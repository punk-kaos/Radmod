# RadMod REG70 live voice R5

R5 advances voice launch by 2.048 seconds from the R4 firmware timer origin. It uses live microphone input and physical PTT release, with the same voice modulator and transmission duration settings as R4.

Flash `build/RT950_V029_REG70_LIVE_VOICE_FAST_PRIMER_R5.BTF`. The known R4 image is in `rollback/`. Start the recorder before keying and record IQ with the same receiver settings as R4.

```sh
python3 capture_reg70.py --port /dev/cu.usbserial-110 --output reg70_r5_uart.txt
```

The expected banner is `RADMOD REG70 LIVE 5`. One key-up with recorded speech played at a fixed level can check onset, the single downward branch transition, and USB/LSB separation on the same input as an R4 comparison. To measure from the physical PTT edge, capture a synchronized key-down marker. With IQ alone, measure from the beginning of the high-branch primer carrier to the onset of voice. That interval was about 2.80 s in the R4 recording and is expected to be about 0.75 s in R5.

## Startup timing

Times below are seconds from the TIM7 schedule origin. Hardware packet duration is estimated from the measured 2,048-byte expiry, adjusted by 8 bits at 6,000 bit/s for every omitted payload byte.

| Event | R4 | R5 |
|---|---:|---:|
| Enable FSK packet TX | 1.213 | 1.213 |
| Turn on RF across expiry | 1.528 | 1.528 |
| Estimated natural packet expiry | 3.950 | 1.902 |
| Mute after expiry | 4.107 | 2.059 |
| Launch live voice DMA | 4.321 | 2.273 |

The BK packet length at initial arm changes from 2,048 to 512 bytes. The post-expiry mute and voice launch both move forward by 4,289 TIM7 ticks. RF is on for approximately 0.37 s before the estimated short-packet expiry. The subsequent timing matches R4 to within one timer tick, including approximately 156 ms on the expired branch and 215 ms muted. The earlier V312 recording independently shows about 0.38 s between high-branch RF onset and the transition with a 512-byte primer. Its shorter post-expiry wait and older voice controller differ from R5.

## Build and simulation

The builder accepts the exact R4 image in this package. It changes eight decoded bytes across three Thumb instructions and the revision banner. The R4 modulator, coefficients, DMA writer, clock rates, warm-up entry and PTT release code are byte-identical.

```sh
python3 build_r5.py
python3 simulate.py
```

The builder uses the Python standard library. The simulation needs NumPy, Unicorn 2.1.x with its C headers and shared library, and a C compiler. The serial recorder requires pyserial.

The simulation executes the decoded firmware, models BK registers, feeds identical archived ADC samples starting at each firmware's voice launch and compares the REG70 commands rendered by DMA. It exercises startup from retained SRAM, TIM7 FIFO/UART service, nested DMA refills, release during seven stages of startup and re-key. The BK packet expiry calculation is a model. A physical R5 IQ capture is needed to measure RF startup timing and sideband rejection.

See `results/replay.json` for the measured command-stream hash, simulated timing, fault and hold counts, and changed flash addresses.
