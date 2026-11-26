"""RT950 Pro V0.29 BTF codec, container inspection, and Thumb branch helpers.

The BTF container is a fixed-key obfuscation wrapper around a Cortex-M image:
  0x000..0x3FF  cleartext (vector table and early boot code)
  0x400..0x7FF  fixed 1 KiB key/material block (16-byte seed at 0x400)
  0x800..EOF    obfuscated image body (maps to decoded offset 0x400)
See docs/btf-format.md. Run `python3 tools/btf.py --help` for the CLI.
"""
import hashlib, struct
APP=0x08003000
CLEAR_LEN=0x400
SEED_OFF=0x400
SEED_LEN=0x10
BLOCK_END=0x800
KEY_LEN=0x80
FILL=0xff

def sha(data):return hashlib.sha256(data).hexdigest()
def key(raw):
    k=bytearray(raw[SEED_OFF:SEED_OFF+SEED_LEN]);assert len(k)==SEED_LEN
    for _ in range(7):
        p=k[-16:]
        k.extend((((v<<1)|(v>>7))&255) if j<8 else (((v>>1)|(v<<7))&255) for j,v in enumerate(p))
    return k

def crypt(raw,k):
    out=bytearray(raw)
    for i in range(BLOCK_END,len(out)):
        mixed=out[i]^k[i%KEY_LEN]
        if out[i] not in (0,255) and mixed not in (0,255):out[i]=mixed
    return bytes(out)
def decode(raw):
    v=crypt(raw,key(raw));return v[:CLEAR_LEN]+v[BLOCK_END:]
def encode(plain,original):
    raw=plain[:CLEAR_LEN]+original[SEED_OFF:BLOCK_END]+plain[CLEAR_LEN:]
    return crypt(raw,key(original))
def decoded(encoded,k):
    """Compatibility helper used by the recovered R5 simulator."""
    d=crypt(encoded,k);return d[:CLEAR_LEN]+d[BLOCK_END:]
def branch(pc,target,link=False):
    off=target-pc-4
    assert off%2==0 and -(1<<24)<=off<(1<<24)
    v=off&0x1ffffff;s=v>>24;j1=1^(v>>23&1)^s;j2=1^(v>>22&1)^s
    return struct.pack('<HH',0xf000 | (s<<10) | (v>>12&1023),(0xd000 if link else 0x9000) | (j1<<13) | (j2<<11) | (v>>1&2047))
def unbranch(pc,b):
    a,b=struct.unpack('<HH',b)
    assert a&0xf800==0xf000 and (b&0xd000) in (0x9000,0xd000)
    s=(a>>10)&1;j1=(b>>13)&1;j2=(b>>11)&1
    off=(s<<24)|((1^(j1^s))<<23)|((1^(j2^s))<<22)|((a&1023)<<12)|((b&2047)<<1)
    if off&(1<<24):off-=1<<25
    return pc+4+off

def _u32(data,off):return struct.unpack_from('<I',data,off)[0]

def vector_table(data,limit=CLEAR_LEN):
    """Return the leading vector table words, stopping at the first non-vector."""
    out=[]
    for off in range(0,min(limit,len(data)),4):
        v=_u32(data,off)
        if v==0 or (APP<=v<APP+len(data) and v&1) or 0x20000000<=v<0x20020000:
            out.append(v)
        else:
            break
    return out

def extents(data,fill=FILL,block=0x100):
    """Return merged [start,end) byte ranges that contain non-fill data."""
    used=[any(b!=fill for b in data[i:i+block]) for i in range(0,len(data),block)]
    runs=[];start=None
    for n,u in enumerate(used):
        if u and start is None:start=n
        if not u and start is not None:runs.append((start*block,min(n*block,len(data))));start=None
    if start is not None:runs.append((start*block,len(data)))
    out=[]
    for a,b in runs:
        while a<b and data[a]==fill:a+=1
        while b>a and data[b-1]==fill:b-=1
        out.append((a,b))
    return out

def info(raw):
    """Describe a BTF container and its decoded image."""
    d=decode(raw);vt=vector_table(d)
    return {
        'file_size':len(raw),'file_size_hex':hex(len(raw)),
        'sha256':sha(raw),
        'decoded_size':len(d),'decoded_size_hex':hex(len(d)),
        'image_base':hex(APP),'image_end':hex(APP+len(d)),
        'seed':raw[SEED_OFF:SEED_OFF+SEED_LEN].hex(),
        'key_block_sha256':sha(raw[SEED_OFF:BLOCK_END]),
        'vector_entries':len(vt),
        'initial_sp':hex(vt[0]) if vt else None,
        'reset':hex(vt[1]) if len(vt)>1 else None,
        'nonff_extents':[(hex(APP+a),hex(APP+b)) for a,b in extents(d)],
        'roundtrip':encode(d,raw)==raw,
    }

def diff(a,b,base=APP,merge=16):
    """Compare decoded images a and b and classify changed bytes.

    Kinds: 'code' (byte was active in a), 'cave' (byte was 0xFF in a) or
    'beyond' (offset is past the end of a). Unchanged gaps up to merge bytes
    are folded into one run.
    """
    aa=a.ljust(len(b),bytes([FILL]))
    runs=[];start=None;last=None
    for i in range(len(b)):
        if aa[i]==b[i]:continue
        if start is None:start=i
        elif i-last>merge:runs.append((start,last));start=i
        last=i
    if start is not None:runs.append((start,last))
    exact={'code':0,'cave':0,'beyond':0}
    for i in range(len(b)):
        if aa[i]==b[i]:continue
        exact['beyond' if i>=len(a) else ('cave' if a[i]==FILL else 'code')]+=1
    out=[]
    for s,e in runs:
        kinds=set()
        for i in range(s,e+1):
            if aa[i]==b[i]:continue
            kinds.add('beyond' if i>=len(a) else ('cave' if a[i]==FILL else 'code'))
        out.append({'start':base+s,'end':base+e,'bytes':e-s+1,'kinds':sorted(kinds)})
    return {'a_size':len(a),'b_size':len(b),'changed':sum(exact.values()),'classes':exact,'runs':out}

def _write(path,data):
    from pathlib import Path
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)

def main(argv=None):
    import argparse,json,sys
    from pathlib import Path
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('info',help='show container and image metadata');p.add_argument('file');p.add_argument('--json',action='store_true')
    p=sub.add_parser('decode',help='write the decoded flash image');p.add_argument('file');p.add_argument('output')
    p=sub.add_parser('encode',help='wrap a decoded image into a BTF');p.add_argument('plain');p.add_argument('output');p.add_argument('--template',required=True,help='any BTF supplying the fixed 1 KiB block')
    p=sub.add_parser('verify',help='check decode/encode round-trip');p.add_argument('files',nargs='+')
    p=sub.add_parser('diff',help='compare two BTFs (or decoded images with --decoded)');p.add_argument('a');p.add_argument('b');p.add_argument('--decoded',action='store_true');p.add_argument('--json',action='store_true')
    p=sub.add_parser('scan',help='verify every .BTF under a directory');p.add_argument('root');p.add_argument('--json',action='store_true')
    a=ap.parse_args(argv)
    if a.cmd=='info':
        i=info(Path(a.file).read_bytes())
        if a.json:print(json.dumps(i,indent=2))
        else:
            for k,v in i.items():
                if k=='nonff_extents':
                    print(f'{k}:')
                    for s,e in v:print(f'  {s}..{e}')
                else:print(f'{k}: {v}')
        return 0
    if a.cmd=='decode':
        raw=Path(a.file).read_bytes();_write(a.output,decode(raw));print(f'{a.output}: {len(decode(raw))} bytes, sha256 {sha(decode(raw))}');return 0
    if a.cmd=='encode':
        plain=Path(a.plain).read_bytes();tpl=Path(a.template).read_bytes()
        if len(plain)<CLEAR_LEN:ap.error('decoded image shorter than the 0x400-byte clear header')
        out=encode(plain,tpl)
        if decode(out)!=plain:ap.error('encoding round-trip failed')
        _write(a.output,out);print(f'{a.output}: {len(out)} bytes, sha256 {sha(out)}');return 0
    if a.cmd=='verify':
        bad=0
        for f in a.files:
            try:
                i=info(Path(f).read_bytes());ok=i['roundtrip']
            except Exception as e:ok=False;i={'sha256':'-','file_size':0};print(f'FAIL {f}: {e}')
            else:print(f'{"PASS" if ok else "FAIL"} {f}: {i["file_size"]} bytes, {i["decoded_size"]} decoded, {i["sha256"]}')
            bad+=not ok
        return 1 if bad else 0
    if a.cmd=='diff':
        ra=Path(a.a).read_bytes();rb=Path(a.b).read_bytes()
        da,db=(ra,rb) if a.decoded else (decode(ra),decode(rb))
        d=diff(da,db)
        if a.json:print(json.dumps(d,indent=2))
        else:
            print(f'{a.a} -> {a.b}: {d["changed"]} changed bytes')
            print(f'  classes: {d["classes"]}')
            for r in d['runs']:
                print(f'  0x{r["start"]:08x}..0x{r["end"]:08x} {r["bytes"]:6d}  {",".join(r["kinds"])}')
        return 0
    if a.cmd=='scan':
        files=sorted(p for p in Path(a.root).rglob('*') if p.suffix.lower()=='.btf')
        rows=[];bad=0
        for f in files:
            try:i=info(f.read_bytes());ok=i['roundtrip']
            except Exception as e:ok=False;i={'sha256':'-','file_size':0,'decoded_size':0}
            bad+=not ok;rows.append({'file':str(f),'ok':ok,**i})
        if a.json:print(json.dumps(rows,indent=2))
        else:
            for r in rows:print(f'{"PASS" if r["ok"] else "FAIL"} {r["file"]}: {r["file_size"]} bytes, {r["decoded_size"]} decoded')
            print(f'{len(rows)-bad}/{len(rows)} containers round-trip')
        return 1 if bad else 0
    return 2

if __name__=='__main__':
    raise SystemExit(main())
