"""Installer, theme discovery, filtered selection, and persistence integration."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
from terminal import BINARY, start, read, click, finish

ROOT = BINARY.parent


def install(config, cwd=ROOT):
    return subprocess.run([str(BINARY), '--install'], cwd=cwd, capture_output=True,
                          env=dict(os.environ, MINESWEEPER_CONFIG_DIR=str(config)), timeout=10)


def quit_game(p, m, s, old):
    os.write(m, b'\x03')
    finish(p, m, s, old)


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        config = root / 'config'
        p, m, s, old = start(root)
        initial = read(m)
        assert b'48;2;8;17;32m' in initial
        assert not config.exists(), 'ordinary startup must not create configuration'
        os.write(m, b't')
        picker = read(m)
        assert b'Ocean Dark' in picker
        os.write(m, b'\r')
        assert b'Theme set: Ocean Dark' in read(m)
        assert json.loads((config / 'settings.json').read_text()) == {'theme': 'ocean-dark'}
        quit_game(p, m, s, old)

        # Explicit installation copies all bundled files and preserves settings.
        result = install(config)
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(list((config / 'themes').glob('*.toml'))) == 4
        for source in (ROOT / 'themes').glob('*.toml'):
            tomllib.loads(source.read_text())
            assert (config / 'themes' / source.name).read_text() == source.read_text()
        assert json.loads((config / 'settings.json').read_text())['theme'] == 'ocean-dark'

        p, m, s, old = start(root)
        read(m)
        assert b'Settings' in click(m, 6, 14)
        assert b'Themes' in click(m, 6, 6)
        os.write(m, b'mid')
        filtered = read(m)
        assert b'Midnight' in filtered
        os.write(m, b'\t\x1b[Z\r')  # Both directions wrap over the only match.
        assert b'Theme set: Midnight' in read(m)
        assert json.loads((config / 'settings.json').read_text())['theme'] == 'midnight'
        os.write(m, b'\x1b')
        read(m)
        os.write(m, b'1')
        read(m)
        os.write(m, b'tocean')
        read(m)
        os.write(m, b'\t\x1b[Z\t\r')
        assert b'Theme set: Ocean Light' in read(m)
        assert json.loads((config / 'settings.json').read_text())['theme'] == 'ocean-light'
        assert b'Themes' in click(m, 60, 3)
        # Graphite is the second item after built-in Ocean Dark.
        assert b'Theme set: Graphite' in click(m, 26, 15)
        assert json.loads((config / 'settings.json').read_text())['theme'] == 'graphite'
        quit_game(p, m, s, old)

        # Selection persists across fresh processes and Enter is the commit point.
        p, m, s, old = start(root)
        assert b'48;2;21;21;21m' in read(m)
        os.write(m, b'tmidnight')
        read(m)
        os.write(m, b'\x1b')
        read(m)
        assert json.loads((config / 'settings.json').read_text())['theme'] == 'graphite'
        os.write(m, b't')
        read(m)
        os.write(m, b'z' * 150)
        long_query = read(m)
        assert b'<' in long_query and b'No matching themes' in long_query
        os.write(m, b'\r')
        read(m)
        assert json.loads((config / 'settings.json').read_text())['theme'] == 'graphite'
        quit_game(p, m, s, old)

        # Reinstall does not replace a preference or user-edited bundled file.
        custom = (config / 'themes/graphite.toml').read_text() + '\n# User customization\n'
        (config / 'themes/graphite.toml').write_text(custom)
        result = install(config)
        assert result.returncode == 0 and b'Installed 0 theme(s)' in result.stdout
        assert (config / 'themes/graphite.toml').read_text() == custom
        assert json.loads((config / 'settings.json').read_text())['theme'] == 'graphite'

        # Custom TOML themes inherit unspecified roles and can be selected by ID.
        (config / 'themes/custom-blue.toml').write_text('name = "Custom Blue"\n[colors]\nbackground = "#123456"\n')
        (config / 'settings.json').write_text('{"theme":"custom-blue"}\n')
        p, m, s, old = start(root)
        assert b'48;2;18;52;86m' in read(m)
        quit_game(p, m, s, old)
        (config / 'themes/broken.toml').write_text('[colors]\nbackground = "not-a-color"\n')
        (config / 'settings.json').write_text('{}\n')
        p, m, s, old = start(root)
        assert b'using Ocean Dark' in read(m)
        os.write(m, b't')
        assert b'Skipped 1 invalid theme' in read(m)
        quit_game(p, m, s, old)

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        # No ./themes folder: create valid config without needing a terminal.
        result = install(root / 'config', root)
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads((root / 'config/settings.json').read_text()) == {'theme': 'ocean-dark'}
        assert list((root / 'config/themes').iterdir()) == []
        # A blocked settings destination keeps the theme dialog open on error.
        blocked = root / 'blocked'
        blocked.write_text('not a directory')
        p, m, s, old = start(root, config=blocked)
        read(m)
        os.write(m, b't')
        read(m)
        os.write(m, b'\r')
        assert b'Cannot create the configuration directory' in read(m)
        assert blocked.read_text() == 'not a directory'
        quit_game(p, m, s, old)

    print('Theme integration passed: fallback, install, TOML, search, keyboard/mouse, persistence, clipping, errors')


if __name__ == '__main__':
    main()
