"""Measure actual PTY redraw traffic; optionally compare an unpatched binary."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import struct
import subprocess
import tempfile
import termios
import time


def drain(fd, duration):
    chunks = []
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        if select.select([fd], [], [], .01)[0]:
            chunks.append(os.read(fd, 65536))
    return b''.join(chunks)


def measure(binary):
    with tempfile.TemporaryDirectory() as directory:
        mines = {4, 12, 24, 30, 38, 51, 59, 68, 78, 80}
        values = ['OCEAN_MINES_1', '9', '9', '10', '0', '0', '1']
        for index in range(81):
            x, y = index % 9, index // 9
            adjacent = sum((y+dy)*9+x+dx in mines
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                           if (dx or dy) and 0 <= x+dx < 9 and 0 <= y+dy < 9)
            values.extend([str(-1 if index in mines else adjacent), '1' if index == 0 else '0'])
        values.extend(['BOARD_ID', 'redraw-fixture'])
        Path(directory, 'minesweeper.save').write_text('\n'.join(values)+'\n')
        master, slave = pty.openpty()
        original = termios.tcgetattr(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
        process = subprocess.Popen([str(binary)], cwd=directory,
                                   stdin=slave, stdout=slave, stderr=slave,
                                   env=dict(os.environ, MINESWEEPER_CONFIG_DIR=str(Path(directory) / "config")))
        try:
            drain(master, .2)
            os.write(master, b'\x1b[<0;7;13M\x1b[<0;7;13m')
            assert b'Saved game resumed' in drain(master, .2)
            os.write(master, b'l')
            movement = drain(master, .15)
            timer = drain(master, 1.05)
            os.write(master, b'\x03')
            deadline = time.monotonic()+5
            while process.poll() is None and time.monotonic() < deadline:
                drain(master, .05)
            process.wait(timeout=1)
            assert process.returncode == 0
            assert termios.tcgetattr(slave) == original
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)
    clear = re.compile(rb'\x1b\[(?:0|2)?J')
    return {
        'cursor_move_bytes': len(movement),
        'timer_bytes': len(timer),
        'viewport_erases': len(clear.findall(movement+timer)),
        'synchronized_updates': (movement+timer).count(b'\x1b[?2026h'),
        'cursor_move_rows': sorted(set(int(n) for n in re.findall(rb'\x1b\[(\d+);1H', movement))),
        'timer_rows': sorted(set(int(n) for n in re.findall(rb'\x1b\[(\d+);1H', timer))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    fixed = measure(Path(__file__).resolve().parents[1] / 'minesweeper')
    assert fixed['viewport_erases'] == 0, fixed
    assert fixed['cursor_move_rows'] == [7], fixed
    assert fixed['timer_rows'] == [5], fixed
    assert fixed['synchronized_updates'] >= 2, fixed
    result = {'fixed': fixed}
    if args.baseline:
        old = measure(args.baseline.resolve())
        assert fixed['cursor_move_bytes'] < old['cursor_move_bytes'] / 4, result
        assert fixed['timer_bytes'] < old['timer_bytes'] / 4, result
        result['baseline'] = old
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
