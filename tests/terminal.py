"""PTY integration: mouse, save/resume, resizing, and terminal cleanup."""
import fcntl
import os
import pathlib
import pty
import re
import select
import struct
import subprocess
import tempfile
import termios
import time

BINARY = pathlib.Path(__file__).resolve().parents[1] / 'minesweeper'

def start(directory, width=100, height=35, config=None):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
    original = termios.tcgetattr(slave)
    proc = subprocess.Popen([str(BINARY)], stdin=slave, stdout=slave, stderr=slave, cwd=directory, env=dict(os.environ, MINESWEEPER_CONFIG_DIR=str(config if config is not None else pathlib.Path(directory) / "config")))
    return proc, master, slave, original

def read(master, duration=.3):
    data = b''
    until = time.monotonic() + duration
    while time.monotonic() < until:
        if select.select([master], [], [], .02)[0]:
            try:
                data += os.read(master, 65536)
            except OSError:
                break
    return data

def click(master, x, y, button=0):
    # Zero-based coordinates encoded as SGR mouse press/release reports.
    os.write(master, f'\x1b[<{button};{x+1};{y+1}M\x1b[<{button};{x+1};{y+1}m'.encode())
    return read(master)

def finish(proc, master, slave, original):
    # A full colored viewport can fill the PTY buffer during the final redraw.
    # Keep consuming output while waiting so the application can finish writing.
    output = b''
    deadline = time.monotonic() + 5
    while proc.poll() is None and time.monotonic() < deadline:
        output += read(master, .05)
    proc.wait(timeout=1)
    output += read(master)
    assert proc.returncode == 0
    assert termios.tcgetattr(slave) == original, 'terminal mode was not restored'
    assert b'\x1b[?1002l' in output and b'\x1b[?1006l' in output, 'mouse reporting was not disabled'
    os.close(master)
    os.close(slave)

def main():
    with tempfile.TemporaryDirectory() as directory:
        p, m, s, old = start(directory)
        assert b'Beginner' in read(m)
        assert b'Mines: 10' in click(m, 6, 6)
        click(m, 3, 6)  # safe first reveal
        click(m, 27, 14, 2)  # flag with right button
        assert b'Saved to minesweeper.save' in click(m, 14, 3)
        expired = read(m, .8)
        assert re.search(rb'\x1b\[[0-9]+;1H', expired), 'save expiry must redraw its row'
        assert b'Saved to minesweeper.save' not in expired.rsplit(b'\x1b[?2026h', 1)[-1], 'save notice must expire after 900 ms'
        saved = pathlib.Path(directory, 'minesweeper.save').read_text()
        assert saved.startswith('OCEAN_MINES_1\n9\n9\n10\n')
        os.write(m, b'q')
        finish(p, m, s, old)
        saved = pathlib.Path(directory, 'minesweeper.save').read_text()
        p, m, s, old = start(directory)
        read(m)
        assert b'Saved game resumed' in click(m, 6, 12)
        assert pathlib.Path(directory, 'minesweeper.save').read_text() == saved
        assert b'New board. First reveal is safe.' in click(m, 53, 3)
        assert b'Overwrite saved game?' in click(m, 14, 3)
        assert pathlib.Path(directory, 'minesweeper.save').read_text() == saved
        # Cancel leaves the current board active and the saved board intact.
        os.write(m, b'\x1b')
        read(m)
        assert b'Overwrite saved game?' in click(m, 14, 3)
        assert b'Saved to minesweeper.save' in click(m, 26, 16)
        reset = pathlib.Path(directory, 'minesweeper.save').read_text().splitlines()
        assert reset[1:7] == ['9', '9', '10', '0', '0', '0']
        assert all(value == '0' for value in reset[7:169]), 'reset must clear every cell and flag'
        # Resize while playing.
        fcntl.ioctl(s, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 60, 0, 0))
        read(m)
        os.write(m, b'q')
        finish(p, m, s, old)
        # Malformed save must be rejected without starting a game.
        pathlib.Path(directory, 'minesweeper.save').write_text('bad save\n')
        p, m, s, old = start(directory)
        read(m)
        assert b'Invalid save format' in click(m, 6, 12)
        os.write(m, b'q')
        finish(p, m, s, old)
    # Protect saves across reset, difficulty changes, menu exits, and quit requests.
    with tempfile.TemporaryDirectory() as directory:
        p, m, s, old = start(directory)
        read(m)
        click(m, 6, 6)
        click(m, 14, 3)
        original_save = pathlib.Path(directory, 'minesweeper.save').read_text()
        # Saving progress on the same board does not prompt.
        assert b'Overwrite saved game?' not in click(m, 14, 3)
        os.write(m, b'rm')
        popup = read(m)
        assert b'Overwrite saved game?' in popup and b'Exit without saving' in popup
        # Escape cancels without opening the menu or changing the saved file.
        os.write(m, b'\x1b')
        cancelled = read(m)
        assert b'Choose an expedition' not in cancelled
        assert pathlib.Path(directory, 'minesweeper.save').read_text() == original_save
        os.write(m, b'm')
        read(m)
        # Default is Cancel; Up chooses Exit without saving.
        os.write(m, b'\x1b[A\r')
        assert b'Choose an expedition' in read(m)
        assert pathlib.Path(directory, 'minesweeper.save').read_text() == original_save
        os.write(m, b'2')
        read(m)
        os.write(m, b'm')
        assert b'Overwrite saved game?' in read(m)
        # From Cancel, three Up presses choose Overwrite and return to the menu.
        os.write(m, b'\x1b[A\x1b[A\x1b[A\r')
        assert b'Choose an expedition' in read(m)
        replacement = pathlib.Path(directory, 'minesweeper.save').read_text()
        assert replacement.startswith('OCEAN_MINES_1\n16\n16\n40\n')
        assert replacement != original_save
        click(m, 6, 12)  # resume current board
        os.write(m, b'rq')
        assert b'Exit without saving' in read(m)
        # Quit without saving preserves the saved board, too.
        os.write(m, b'\x1b[A\r')
        finish(p, m, s, old)
        assert pathlib.Path(directory, 'minesweeper.save').read_text() == replacement
        # Existing saves from before board IDs were added still resume normally.
        legacy = replacement.split('BOARD_ID\n', 1)[0]
        pathlib.Path(directory, 'minesweeper.save').write_text(legacy)
        p, m, s, old = start(directory)
        read(m)
        assert b'Saved game resumed' in click(m, 6, 12)
        assert b'Overwrite saved game?' not in click(m, 14, 3)
        os.write(m, b'q')
        finish(p, m, s, old)

    # Custom save filenames, clipped entry text, file browsing, and typed paths.
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        (root / 'nested').mkdir()
        long_name = 'nested/' + 'board_' * 16 + '-tail.save'
        p, m, s, old = start(directory)
        read(m)
        click(m, 6, 6)
        assert b'Save as...' in click(m, 27, 4)
        os.write(m, b'\x15' + long_name.encode())
        entry = read(m)
        assert b'-tail.save_' in entry and long_name.encode() not in entry
        assert b'<' in entry, 'long filename must clip its start'
        # Click Save in the filename popup.
        assert b'Saved to nested/' in click(m, 26, 18)
        source = (root / long_name).read_text()
        assert not (root / 'minesweeper.save').exists()
        os.write(m, b'q')
        finish(p, m, s, old)
        source = (root / long_name).read_text()
        (root / 'b.save').write_text(source)
        (root / '.hidden.save').write_text(source)
        (root / '00-invalid.txt').write_text('not a saved game')
        for i in range(25):
            (root / f'fixture-{i:02}.txt').write_text('unrelated file')
        p, m, s, old = start(directory)
        read(m)
        assert b'Resume from other game' in click(m, 6, 18)
        # The picker includes hidden saves and unrelated files, with no extension filter.
        picker = read(m)
        os.write(m, b'\x1b[F')  # End scrolls to Cancel.
        assert b'fixture-24.txt' in read(m)
        os.write(m, b'\x1b[H\x1b[B\x1b[B\r')  # Custom, .hidden.save, 00-invalid.txt.
        assert b'Invalid save format' in read(m)
        os.write(m, b'\x1b[H\r')
        assert b'Resume from filename' in read(m)
        os.write(m, str(root / long_name).encode())
        read(m)
        os.write(m, b'\r')
        assert b'Saved game resumed' in read(m)
        os.write(m, b'q')
        finish(p, m, s, old)
        # Selecting a file with the mouse resumes it; Save as preserves a menu exit.
        p, m, s, old = start(directory)
        read(m)
        click(m, 6, 18)
        # height=35, picker height=18 -> top=8, files start at row 12.
        assert b'Saved game resumed' in click(m, 26, 15)  # b.save (after custom, hidden, invalid)
        os.write(m, b'rm')
        assert b'Overwrite saved game?' in read(m)
        os.write(m, b'\x1b[A\x1b[A\r')  # Cancel -> Exit without saving -> Save as.
        assert b'Save as...' in read(m)
        os.write(m, b'\x15elsewhere.save\r')
        assert b'Choose an expedition' in read(m)
        assert (root / 'elsewhere.save').is_file()
        assert (root / 'b.save').read_text() == source
        os.write(m, b'q')
        finish(p, m, s, old)

    print('PTY integration passed: mouse, save/resume, overwrite dialogs, custom paths, clipping, picker, resize, cleanup')


if __name__ == "__main__":
    main()
