#!/usr/bin/env python3
import argparse,time,re
import serial
p=argparse.ArgumentParser();p.add_argument('--port',required=True);p.add_argument('--output',default='r3b_uart.txt');p.add_argument('--timeout',type=float,default=30);a=p.parse_args()
count=0
with serial.Serial(a.port,115200,timeout=.25) as s,open(a.output,'w') as f:
 print('R3B SRAM 16-tap staged G20 encoder probe, 115200 baud. Hold PTT and speak for at least 8 seconds, then release.',flush=True)
 end=time.monotonic()+a.timeout
 try:
  while time.monotonic()<end:
   raw=s.readline()
   if not raw:continue
   line=raw.decode('ascii',errors='replace').rstrip();print(line,flush=True);f.write(line+'\n');f.flush()
   if re.fullmatch(r'ENC[0-6](?: [A-Z]=[0-9A-F]{8}){4}',line):count+=1
 except KeyboardInterrupt:pass
print(f'Saved {a.output}; {count} complete encoder frames.')
