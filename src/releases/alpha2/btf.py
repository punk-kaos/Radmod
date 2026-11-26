#!/usr/bin/env python3
"""Deterministic, checksum locked R2D FIX2 -> R2H late USB setup test."""
from pathlib import Path
import hashlib, json, struct, subprocess

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'baseline/RT950_R5_RadMod_V0.2_R2D_FIX2_SRAM_RELOC_NO_UART_UNTESTED.BTF'
OUTPUT=ROOT/'RT950_R5_RadMod_V0.2_R2H_USB_RX_LATE_SETUP_UNTESTED.BTF'
APP=0x08003000
BASE_SHA='3cefc87687911dee9582de67778862fb8023dea65457d67e554d1773fa9a2c7a'
RX_TAIL=0x0801f2f2
CODE_ADDR=0x08070500
CODE_END=0x08071800

def sha(data):return hashlib.sha256(data).hexdigest()
def key(raw):
    k=bytearray(raw[0x400:0x410]);assert len(k)==16
    for _ in range(7):
        p=k[-16:]
        k.extend((((v<<1)|(v>>7))&255) if j<8 else (((v>>1)|(v<<7))&255) for j,v in enumerate(p))
    return k

def crypt(raw,k):
    out=bytearray(raw)
    for i in range(0x800,len(out)):
        mixed=out[i]^k[i%128]
        if out[i] not in (0,255) and mixed not in (0,255):out[i]=mixed
    return bytes(out)
def decode(raw):
    v=crypt(raw,key(raw));return v[:0x400]+v[0x800:]
def encode(plain,original):
    raw=plain[:0x400]+original[0x400:0x800]+plain[0x400:]
    return crypt(raw,key(original))
def branch(pc,target,link=False):
    off=target-pc-4
    assert off%2==0 and -(1<<24)<=off<(1<<24)
    v=off&0x1ffffff;s=v>>24;j1=1^(v>>23&1)^s;j2=1^(v>>22&1)^s
    return struct.pack('<HH',0xf000 | (s<<10) | (v>>12&1023),(0xd000 if link else 0x9000) | (j1<<13) | (j2<<11) | (v>>1&2047))
def unbranch(pc,b):
    a,b=struct.unpack('<HH',b)
    assert a&0xf800==0xf000 and b&0xd000==0x9000
    s=(a>>10)&1;j1=(b>>13)&1;j2=(b>>11)&1
    off=(s<<24)|((1^(j1^s))<<23)|((1^(j2^s))<<22)|((a&1023)<<12)|((b&2047)<<1)
    if off&(1<<24):off-=1<<25
    return pc+4+off

