"""Execute decoded flash, using Unicorn 2.1.x's Cortex-M4 model."""
import ctypes as C
from pathlib import Path
import subprocess
import sys
import os
import numpy as np
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_CPU_ARM_CORTEX_M4
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from btf import APP, decoded, key
RETURN = 0x20000100
S, AUDIO, POL = 0x20016000, 0x20017800, 0x20017e20

class Machine:
    def __init__(self, firmware):
        f=firmware.read_bytes()
        self.u=u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        for address,size in ((APP,0x6f000),(0x20000000,0x20000),(0x40000000,0x24000),(0xe0000000,0x10000)):
            u.mem_map(address,size)
        u.mem_write(APP,decoded(f,key(f)))
        u.reg_write(UC_ARM_REG_SP,0x20015800)
        u.mem_write(0x20000000,bytes.fromhex('7047'))  # modeled external BK register writer returns
        self.put(AUDIO+254,1,1)
        self.put(AUDIO+268,2048<<18)
        self.put(AUDIO+272,2048,2)
        self.put(0x20017f60,0x46534b32)
        self.put(0x20017fa8,0x100)
        self.put(0x20017fa4,0x20000001)
        self.put(0x20017f78,0xc1f60000)
        self.put(0x4001180c,0x8100)
        self.put(0x4000100c,1)
        self.put(0x40013c00,2)
        self.put(0x40013c4c,2048)

    def get(self,a,n=4):
        return int.from_bytes(self.u.mem_read(a,n),'little')

    def put(self,a,value,n=4):
        self.u.mem_write(a,int(value).to_bytes(n,'little'))

    def call(self,address,a=0,b=0,until=RETURN):
        u=self.u
        u.reg_write(UC_ARM_REG_R0,int(a)&0xffffffff)
        u.reg_write(UC_ARM_REG_R1,int(b)&0xffffffff)
        u.reg_write(UC_ARM_REG_LR,RETURN|1)
        u.emu_start(address|1,until,count=250000)
        assert u.reg_read(UC_ARM_REG_PC)==until
        return u.reg_read(UC_ARM_REG_R0)

class Config(C.Structure):
    _fields_=[(k,C.c_uint32) for k in 'target phase flash_cost dma_floor launch_tick ram_exec flash_data ram_data'.split()]

class Result(C.Structure):
    _fields_=[(k,C.c_uint32) for k in
        'frames ticks coalesced preemptions holds running fault last_writer peak_ops peak_work peak_elapsed peak_dma max_entry_lag tim7_ticks release release_command stack_ok'.split()] + [(k,C.c_uint64) for k in ['ops','own_work','isrs']]

def load_scheduler(tmp):
    package=Path(unicorn.__file__).resolve().parent
    libdir=package/'lib'
    libs=[p for p in libdir.glob('*unicorn*') if '.so' in p.name or '.dylib' in p.name]
    if not libs:
        raise RuntimeError('Install the Unicorn 2.1 wheel with its C headers and shared library')
    output=Path(tmp)/'scheduler.so'
    subprocess.run([os.environ.get('CC','cc'),'-O2','-std=c11','-Wall','-Wextra','-Werror','-fPIC','-shared',
        '-I'+str(package/'include'),str(Path(__file__).with_name('scheduler.c')),str(sorted(libs)[0]),
        '-Wl,-rpath,'+str(libdir),'-o',str(output)],check=True)
    library=C.CDLL(str(output))
    f=library.run_clock
    f.argtypes=[C.c_void_p,C.POINTER(Config),C.c_void_p,C.c_uint,C.c_void_p,C.POINTER(Result)]
    f.restype=C.c_int
    return f

def run(f, machine, samples, frames, launch_tick):
    # Measured DMA cost scenario used for the R4 preemption checks.
    samples=np.ascontiguousarray(samples,dtype=np.uint16)
    trace=np.full(frames,255,dtype=np.uint8)
    out=Result()
    err=f(machine.u._uch, C.byref(Config(frames,4500,8,5037,launch_tick,20,6,3)),
          samples.ctypes.data, len(samples),trace.ctypes.data,C.byref(out))
    if err:
        raise RuntimeError(f'Unicorn {err}, PC={machine.u.reg_read(UC_ARM_REG_PC):#x}')
    data={k:int(getattr(out,k)) for k,_ in out._fields_}
    data['dma_stopped']=not bool(machine.get(0x4002041c) & 1)
    data['tx_inactive_after_stop']=not bool(machine.get(S+0x81,1))
    data['peak_t6_cycles_model']=data.pop('peak_work')
    data['mean_t6_instructions']=round(data['ops']/max(1,data['isrs']),1)
    return data,trace,machine

