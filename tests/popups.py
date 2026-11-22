"""Check real animated popup lifetimes without animating internal navigation."""
import os
from pathlib import Path
import re
import tempfile
from terminal import start, read, click, finish


def frames(output):
    assert not re.search(rb'\x1b\[(?:0|2)?J', output), 'animation must not clear the viewport'
    return output.count(b'\x1b[?2026h')


def main():
    with tempfile.TemporaryDirectory() as temporary:
        p, m, s, old = start(Path(temporary))
        try:
            read(m)
            # Opening the picker grows it over several synchronized paints.
            opening = click(m, 6, 18)
            assert frames(opening) >= 3, 'opening must have intermediate frames'
            assert '╭'.encode() in opening and '╰'.encode() in opening
            os.write(m, b'\r')
            entry = read(m)
            assert b'Resume from filename' in entry
            assert frames(entry) == 1, 'picker to entry must not restart the zoom'
            os.write(m, b'\x1b')
            back = read(m)
            assert b'Resume from other game' in back
            assert frames(back) == 1, 'returning within a popup must not zoom'
            os.write(m, b'\x1b')
            closing = read(m)
            assert frames(closing) >= 3, 'closing must shrink over intermediate frames'
            os.write(m, b't')
            assert frames(read(m)) >= 3
            # Input arriving immediately after opening is retained while it grows.
            os.write(m, b'\x1b')
            read(m)
            os.write(m, b'tocean')
            assert b'Ocean Dark' in read(m)
            os.write(m, b'\x03')
            finish(p, m, s, old)
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
    print('Popup integration passed: opening/closing zoom, instant internal navigation, responsive input, no viewport erase')


if __name__ == '__main__':
    main()
