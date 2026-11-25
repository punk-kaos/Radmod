"""Build the short-primer image directly from the recorded R4 release."""
from hashlib import sha256
from pathlib import Path
from struct import pack
from btf import APP, crypt, decoded, key

ROOT = Path(__file__).resolve().parent
R4 = ROOT / "rollback/RT950_V029_REG70_LIVE_VOICE_UNLIMITED_R4.BTF"
R5 = ROOT / "build/RT950_V029_REG70_LIVE_VOICE_FAST_PRIMER_R5.BTF"
R4_SHA = "80b3e48bde4a813ca82a892e0c585c72818ccffa450e2c0257e3fecb6542dc3c"
TICK = 955 / 2_000_000
SAVED_TICKS = round((2048 - 512) * 8 / 6000 / TICK)

def movw(register, value):
    first = 0xf240 | ((value >> 1) & 0x400) | (value >> 12)
    second = ((value & 0x700) << 4) | (register << 8) | (value & 0xff)
    return pack("<HH", first, second)

def build():
    raw = R4.read_bytes()
    if sha256(raw).hexdigest() != R4_SHA:
        raise ValueError("Incorrect R4 input")
    k = key(raw)
    original = decoded(raw, k)
    image = bytearray(original)
    patches = [
        # BK REG5D swaps the low length byte with the three upper length bits.
        (0x08043112, bytes.fromhex("4ff6e071"), movw(1, 0xff20)),
        (0x08062b00, bytes.fromhex("42f29812"), movw(2, 8600 - SAVED_TICKS)),
        (0x08062b14, bytes.fromhex("42f25a32"), movw(2, 9050 - SAVED_TICKS)),
        (0x08052f7c, b"RADMOD REG70 LIVE 4", b"RADMOD REG70 LIVE 5"),
    ]
    for addr, before, after in patches:
        i = addr - APP
        if len(before) != len(after) or image[i:i+len(before)] != before:
            raise ValueError(f"Unexpected bytes at {addr:#010x}")
        image[i:i+len(before)] = after
    result = crypt(image[:1024] + raw[1024:2048] + image[1024:], k)
    assert len(raw) == len(result) and raw[1024:2048] == result[1024:2048]
    assert decoded(result, k) == image
    R5.parent.mkdir(exist_ok=True)
    R5.write_bytes(result)
    return sha256(result).hexdigest()

if __name__ == "__main__":
    print(R5.name, build())
