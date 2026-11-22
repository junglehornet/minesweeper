#!/usr/bin/env python3
"""Run Ocean with the term/tui redraw patch in a temporary standard-library tree."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    compiler = shutil.which(os.environ.get('OCEAN', 'ocean'))
    if not compiler:
        sys.exit('Ocean compiler not found. Set OCEAN or add ocean to PATH.')
    configured = os.environ.get('OCEAN_SRC')
    if configured:
        source = Path(configured).resolve()
    else:
        sibling = ROOT.parent / 'ocean-src'
        source = sibling if sibling.is_dir() else Path(compiler).resolve().parent.parent / 'src'
    if not (source / 'term/tui/render.oc').is_file():
        sys.exit('Cannot locate term/tui. Set OCEAN_SRC to the Ocean standard-library source.')
    with tempfile.TemporaryDirectory(prefix='minesweeper-stdlib-') as directory:
        overlay = Path(directory)
        # Intrinsic packages must physically live under OCEAN_SRC; symlinks back
        # to the original tree fail the compiler's standard-library checks.
        shutil.copytree(source, overlay, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
        patch = ROOT / 'patches/term-tui-redraw.patch'
        already_applied = subprocess.run(
            ['patch', '--dry-run', '--batch', '--reverse', '-p1', '-i', str(patch)],
            cwd=overlay, capture_output=True, text=True)
        if already_applied.returncode:
            result = subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)],
                                    cwd=overlay, capture_output=True, text=True)
            if result.returncode:
                sys.exit('Could not apply the TUI patch to this standard-library version:\n' +
                         result.stdout + result.stderr)
        env = dict(os.environ, OCEAN_SRC=str(overlay))
        args = sys.argv[1:]
        if args == ['--test-tui']:
            # Test the renderer independently. The existing mouse unit tests
            # hit a compiler backend error even with the unmodified library;
            # the library's PTY harness below still tests actual mouse input.
            renderer_tests = overlay / '.renderer-tests'
            renderer_tests.mkdir()
            for entry in (overlay / 'term/tui').glob('*.oc'):
                if not entry.name.endswith('_test.oc') or entry.name == 'render_test.oc':
                    shutil.copy2(entry, renderer_tests / entry.name)
            checks = [
                [compiler, 'test', str(renderer_tests), '--notty'],
                [sys.executable, str(overlay / 'term/tui/tests/test_tui.py')],
            ]
            env['OCEAN'] = compiler
            for command in checks:
                result = subprocess.run(command, env=env)
                if result.returncode:
                    return result.returncode
            return 0
        return subprocess.run([compiler, *args], env=env).returncode


if __name__ == '__main__':
    sys.exit(main())
