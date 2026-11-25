"""Patcher regression tests without an OEM file."""
import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from btf import decode,encode,APP
from patch import apply,make_manifest
class PatchTests(unittest.TestCase):
    def setUp(self):
        self.raw=bytes(0x900);p=bytearray(decode(self.raw));p[0x45]=2;p.extend(b'\xff'*20);p[-1]=7
        self.out=encode(bytes(p),self.raw);self.m=make_manifest(self.raw,self.out)
    def test_roundtrip(self):self.assertEqual(apply(self.raw,self.m),self.out)
    def test_wrong_oem(self):
        with self.assertRaises(ValueError):apply(b'\x01'+self.raw[1:],self.m)
    def test_wrong_preimage(self):
        self.m['edits'][0]['before']='ff'
        with self.assertRaises(ValueError):apply(self.raw,self.m)
    def test_overlap(self):
        self.m['edits'].insert(1,self.m['edits'][0])
        with self.assertRaises(ValueError):apply(self.raw,self.m)
    def test_wrong_output(self):
        self.m['output_sha256']='0'*64
        with self.assertRaises(ValueError):apply(self.raw,self.m)
if __name__=='__main__':unittest.main()
