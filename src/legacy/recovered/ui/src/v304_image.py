"""V304 build helpers for its original BTF container encoding."""

APP = 0x08003000

def key(b):
 k=bytearray(b[0x400:0x410]);assert len(k)==16
 for _ in range(7):
  prev=k[-16:];k.extend(((((v<<1)|(v>>7))&255) if i<8 else (((v>>1)|(v<<7))&255)) for i,v in enumerate(prev))
 return k
def crypt(b,k):
 x=bytearray(b)
 for i in range(0x800,len(x)):
  z=x[i]^k[i%128]
  if x[i] not in (0,255) and z not in (0,255):x[i]=z
 return bytes(x)
def decoded(encoded,k):
 d=crypt(encoded,k);return d[:0x400]+d[0x800:]
