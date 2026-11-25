#!/usr/bin/env python3
"""Apply address-checked decoded overlay records to a user-supplied OEM BTF."""
import argparse, json, hashlib
from pathlib import Path
from btf import APP, decode, encode, sha

def apply(raw, manifest, strict=True):
    if strict and sha(raw)!=manifest['input_sha256']:
        raise ValueError('Input firmware SHA-256 mismatch')
    orig=decode(raw)
    if encode(orig,raw)!=raw: raise ValueError('BTF codec round-trip failed')
    n=manifest['decoded_size']
    if not len(orig)<=n<=0x6f000: raise ValueError('Invalid overlay image length')
    p=bytearray(orig.ljust(n,b'\xff')); end=0
    for e in manifest['edits']:
        at=int(e['address'],16)-APP; old=bytes.fromhex(e['before']); new=bytes.fromhex(e['after'])
        if not old or len(old)!=len(new) or at<end or at+len(old)>n: raise ValueError(f'Invalid/overlapping patch at {e["address"]}')
        if p[at:at+len(old)]!=old: raise ValueError(f'Preimage mismatch at {e["address"]}')
        p[at:at+len(new)]=new;end=at+len(old)
    out=encode(bytes(p),raw)
    if decode(out)!=bytes(p) or out[0x400:0x800]!=raw[0x400:0x800]: raise ValueError('Output encoding check failed')
    if strict and sha(out)!=manifest['output_sha256']: raise ValueError('Output SHA-256 mismatch')
    return out

def make_manifest(raw, out):
    a=decode(raw); b=decode(out); a=a.ljust(len(b),b'\xff'); edits=[]; start=None; last=None
    def record():
        edits.append({'address':hex(APP+start),'before':a[start:last+1].hex(),'after':b[start:last+1].hex()})
    for i,(x,y) in enumerate(zip(a,b)):
        if x==y: continue
        if start is None: start=i
        elif i-last>8: record();start=i
        last=i
    if start is not None: record()
    return {'input_sha256':sha(raw),'output_sha256':sha(out),'decoded_size':len(b),'edits':edits}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('oem',type=Path);ap.add_argument('patch',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
    if a.oem.resolve()==a.output.resolve():ap.error('Refusing to overwrite OEM input')
    result=apply(a.oem.read_bytes(),json.loads(a.patch.read_text()));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(result);print(f'{a.output}: {sha(result)}')
if __name__=='__main__':main()
