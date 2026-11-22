"""Real terminal editing: cursor navigation, Unicode, scrolling, and mouse clicks."""
import json
import os
from pathlib import Path
import tempfile
from terminal import start, read, click, finish


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        p, m, s, old = start(root)
        try:
            read(m)
            os.write(m, b'1')
            read(m)
            os.write(m, b'S\x15ab.save\x1b[H\x1b[C\x1b[C' + '界'.encode())
            read(m)
            # Delete a wide glyph from its start and insert a flag in its place.
            os.write(m, b'\x1b[D\x1b[3~' + '⚑'.encode())
            read(m)
            os.write(m, b'\x1b[F\x7fe\x1b[H\x1b[C\x1b[3~b')
            read(m)
            # The filename field starts at x=25, y=15 in a 100x35 window.
            click(m, 25, 15)
            os.write(m, b'x\r')
            assert 'Saved to xab⚑.save'.encode() in read(m)
            assert (root / 'xab⚑.save').is_file()

            # Home must show the start of a clipped entry; End must follow its tail.
            os.write(m, b'S\x15' + b'p' * 70 + b'.save')
            read(m)
            os.write(m, b'\x1b[H')
            beginning = read(m)
            assert b'_ppp' in beginning and b'>' in beginning
            os.write(m, b'new-')
            assert b'new-_ppp' in read(m)
            os.write(m, b'\x1b[F\x7fX')
            ending = read(m)
            assert b'.savX_' in ending and b'<' in ending
            os.write(m, b'\r')
            read(m)
            assert (root / ('new-' + 'p' * 70 + '.savX')).is_file()

            # The custom resume path uses the same editor.
            os.write(m, b'm')
            read(m)
            click(m, 6, 18)
            os.write(m, b'\r')
            read(m)
            os.write(m, 'xyab⚑.save'.encode() + b'\x1b[H\x1b[C\x1b[3~\r')
            assert b'Saved game resumed' in read(m)

            # Fix a query in its middle rather than appending to it.
            os.write(m, b'tocen')
            assert b'No matching themes' in read(m)
            os.write(m, b'\x1b[Da')
            assert b'Ocean Dark' in read(m)
            # Click the start of the filter; replace its first character.
            click(m, 32, 11)
            os.write(m, b'\x1b[3~O\r')
            assert b'Theme set: Ocean Dark' in read(m)
            assert json.loads((root / 'config/settings.json').read_text())['theme'] == 'ocean-dark'
            os.write(m, b'\x03')
            finish(p, m, s, old)
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
    print('Entry integration passed: cursor keys, middle edits, Unicode, clipping, mouse, save/load, search')


if __name__ == '__main__':
    main()
