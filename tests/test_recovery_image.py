# SPDX-License-Identifier: MIT
import pathlib,sys,unittest,struct
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from recovery_image import add,parse_cpio,write_cpio,compress,decompress,read_recovery,write_recovery

class ImageTests(unittest.TestCase):
    def test_preserves_symlink_mode_and_binary_payload(self):
        entries={};add(entries,'vendor/bin/touch',b'\x00\n\r\xffpayload',0o100755);add(entries,'default.prop',b'prop.default',0o120777)
        result=parse_cpio(write_cpio(entries))
        self.assertEqual(result['default.prop'].mode,0o120777)
        self.assertEqual(result['default.prop'].data,b'prop.default')
        self.assertEqual(result['vendor/bin/touch'].data,b'\x00\n\r\xffpayload')
        self.assertEqual(result['vendor/bin/touch'].mode,0o100755)
    def test_lz4_multi_block_preserves_bytes(self):
        content=bytes(range(256))*34000
        self.assertEqual(decompress(compress(content)),content)
    def test_rejects_truncated_lz4(self):
        with self.assertRaises(ValueError):decompress(b'\x02\x21\x4c\x18'+struct.pack('<I',100)+b'bad')
    def test_rejects_unsafe_paths(self):
        for path in ('../outside','/absolute','vendor/../../outside'):
            with self.assertRaises(ValueError):add({},path,b'data')
    def test_does_not_follow_symlink_parent(self):
        entries={};add(entries,'vendor',b'/real_vendor',0o120777)
        with self.assertRaises(ValueError):add(entries,'vendor/bin/x',b'data')
    def test_rejects_truncated_cpio_payload(self):
        entries={};add(entries,'large',b'X'*1000)
        with self.assertRaises(ValueError):parse_cpio(write_cpio(entries)[:200])
    def test_recovery_roundtrip_keeps_header(self):
        header=bytearray(4096);header[:8]=b'ANDROID!';struct.pack_into('<I',header,40,4);struct.pack_into('<I',header,16,0x20000119)
        entries={};add(entries,'init',b'test')
        result=write_recovery(bytes(header),entries)
        self.assertEqual(read_recovery(result)['init'].data,b'test')
        self.assertEqual(result[16:20],header[16:20])
    def test_refuses_embedded_kernel(self):
        header=bytearray(4096);header[:8]=b'ANDROID!';struct.pack_into('<I',header,40,4);struct.pack_into('<I',header,8,4096)
        with self.assertRaises(ValueError):read_recovery(header)

if __name__=='__main__':unittest.main()
