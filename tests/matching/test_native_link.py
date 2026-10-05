"""Public synthetic checks for the bounded dsd 0.12 native linker experiment."""
import importlib.util
import json
import struct
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'tools/scripts/native_link.py'


def module():
    spec = importlib.util.spec_from_file_location('native_link', SCRIPT)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def fixture():
    # dsd-like interleaved global/local table with a Thumb function, RELA ABS32,
    # and legacy PC24 BL relocation; all bytes here are invented.
    names = b'\0.text\0.data\0.symtab\0.strtab\0.rela.data\0.shstrtab\0.rela.text\0'
    strings = b'\0thumb_func\0$t\0'
    sym = b''.join(struct.pack('<IIIBBH', *s) for s in (
        (0, 0, 0, 0, 0, 0), (0, 0, 0, 3, 0, 1),
        (1, 0, 4, 0x10, 0, 1), (12, 0, 0, 0, 0, 1)))
    contents = [b'', struct.pack('<I', 0xEB000000), bytes(4), sym, strings,
                struct.pack('<IIi', 0, (2 << 8) | 2, 0), names,
                struct.pack('<IIi', 0, (2 << 8) | 1, -8)]
    fields = [(0,0,0,0,0,0), (1,1,6,0,0,4), (7,1,3,0,0,4),
              (13,2,0,4,4,16), (21,3,0,0,0,1), (29,4,0,3,2,12),
              (40,3,0,0,0,1), (50,4,0,3,1,12)]
    data = bytearray(52)
    headers = []
    for content, (name, kind, flags, link, info, entry) in zip(contents, fields):
        data += bytes((-len(data)) % 4)
        headers.append((name, kind, flags, 0, len(data), len(content), link, info, 4, entry))
        data += content
    offset = len(data)
    for header in headers:
        data += struct.pack('<10I', *header)
    struct.pack_into('<16sHHIIIIIHHHHHH', data, 0,
                     b'\x7fELF\x01\x01\x01' + bytes(9), 1, 40, 1, 0, 0, offset,
                     0, 52, 0, 0, 40, len(headers), 6)
    return bytes(data)


class NativeLinkTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'native linker adapter missing')

    def test_normalizes_symbol_partition_thumb_and_rela_references(self):
        tool = module()
        normalized = tool.normalize_object(fixture())
        elf = tool.Elf32(normalized)
        symbols = elf.symbols()
        self.assertEqual(elf.sections[3][7], 3)
        self.assertTrue(all(symbol[3] >> 4 == 0 for symbol in symbols[:3]))
        self.assertEqual(symbols[3][1], 1)
        self.assertEqual(symbols[3][3] & 15, 2)
        self.assertEqual(struct.unpack_from('<IIi', normalized, elf.sections[5][4]),
                         (0, (3 << 8) | 2, 0))
        self.assertEqual(struct.unpack_from('<IIi', normalized, elf.sections[7][4]),
                         (0, (3 << 8) | 28, -8))

    def test_translates_after_as_max_end_with_bss_and_distinct_overlays(self):
        lcf = '''MEMORY {
 ARM9 : ORIGIN = 0x02000000 > build/arm9.bin
 OV000 : ORIGIN = AFTER(ARM9) > build/ov0.bin
 OV001 : ORIGIN = AFTER(ARM9) > build/ov1.bin
 SPACE : ORIGIN = AFTER(ARM9, OV000, OV001)
}
KEEP_SECTION { .init, .ctor, .exceptix }
SECTIONS {
 __CODE_HI = ADDR(SPACE);
 .arm9 : { ALIGNALL(4); a.o(.text) WRITEW(0); ARM9_BSS_START = .; a.o(.bss) } > ARM9
 .ov000 : { ALIGNALL(4); OV000_BSS_START = .; WRITEW(0); } > OV000
 .ov001 : { ALIGNALL(4); OV001_BSS_START = .; WRITEW(0); } > OV001
}'''
        translated, outputs = module().translate_lcf(lcf, Path('/public/objects'))
        self.assertIn('LONG(0)', translated)
        self.assertIn('SUBALIGN(4)', translated)
        self.assertIn('ADDR(.arm9) + SIZEOF(.arm9)', translated)
        self.assertIn('MAX(', translated)
        self.assertIn('.ov000', translated)
        self.assertIn('.ov001', translated)
        self.assertEqual(len(outputs), 3)

    def test_cli_links_rela_fixture_and_emits_elf_section_bytes(self):
        lld = shutil.which('ld.lld')
        clang = '/opt/homebrew/opt/llvm/bin/clang'
        if not Path(clang).exists():
            clang = shutil.which('clang')
        if not lld or not clang:
            self.skipTest('native LLVM ARM tools unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            objects = root / 'objects'
            objects.mkdir()
            (objects / 'a.o').write_bytes(fixture())
            lcf = root / 'test.lcf'
            lcf.write_text("""MEMORY {
 ARM9 : ORIGIN = 0x02000000 > build/arm9.bin
 OV000 : ORIGIN = AFTER(ARM9) > build/ov0.bin
 OV001 : ORIGIN = AFTER(ARM9) > build/ov1.bin
}
SECTIONS {
 .arm9 : { ALIGNALL(4); a.o(.text) a.o(.data) . = ALIGN(16); ARM9_BSS_START = .; . += 32; ARM9_BSS_END = .; } > ARM9
 .ov000 : { ALIGNALL(4); WRITEW(0x11111111); OV000_BSS_START = .; } > OV000
 .ov001 : { ALIGNALL(4); WRITEW(0x22222222); OV001_BSS_START = .; } > OV001
}
""")
            # A relative output path reproduces the real pipeline invocation.
            result = subprocess.run([sys.executable, str(SCRIPT), '--lcf', str(lcf),
                                     '--objects', str(objects), '--output', 'out',
                                     '--lld', lld, '--clang', clang],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            binary = (root / 'out/arm9.bin').read_bytes()
            self.assertEqual(len(binary), 16)
            self.assertEqual(binary[8:], bytes(8))
            self.assertEqual(struct.unpack_from('<I', binary, 4)[0], 0x02000001)
            self.assertEqual((root / 'out/ov0.bin').read_bytes(), bytes.fromhex('11111111'))
            self.assertEqual((root / 'out/ov1.bin').read_bytes(), bytes.fromhex('22222222'))
            modules = json.loads((root / 'out/modules.json').read_text())
            self.assertEqual(modules[1]['address'], 0x02000030)

    def test_rejects_unknown_mw_directive(self):
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            module().translate_lcf('MEMORY {\n ARM9 : ORIGIN = 0x02000000 > build/arm9.bin\n} SECTIONS { .arm9 : { UNKNOWN(); ARM9_BSS_START = .; } > ARM9 }', Path('/public'))


if __name__ == '__main__':
    unittest.main()
