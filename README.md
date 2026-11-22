# Ocean Minesweeper

A terminal Minesweeper game written in [Ocean](https://ocean-lang.dev), using its built-in `term/tui` library. Play with the keyboard, the mouse, or both.

Features include three difficulties, safe first reveals, automatic empty-area reveals, chording, save/resume with custom filenames, and searchable TOML themes.

## Build and run

Use a recent Ocean compiler with a standard library that includes `os.OS()`, `os.Arch()`, `os.WindowsKnownFolder()`, and the Windows filesystem APIs, along with `term/tui` mouse support and the incremental renderer. Set `OCEAN_SRC` to the absolute path of a matching source checkout when using a local standard library.

```sh
ocean check .
ocean build . -o minesweeper
./minesweeper
```

Alternatively, run `ocean run .`. Use an interactive terminal with true-color ANSI support and xterm-compatible mouse reporting. On Windows, use a terminal with virtual terminal input support. A window of at least 64 columns and 24 rows is recommended; smaller windows show a scrollable portion of the board. Expert fits in full at 96 columns and 28 rows.

## Install themes and settings

From the repository directory:

```sh
./minesweeper --install
```

This creates:

```text
~/.config/minesweeper/
├── settings.json
└── themes/
    ├── ocean-dark.toml
    ├── ocean-light.toml
    ├── midnight.toml
    └── graphite.toml
```

The installer copies missing `*.toml` files from `./themes`. Existing settings and theme files are preserved, including user edits. If `./themes` does not exist, installation still creates the configuration directories and default settings. The command exits after installation and does not need a terminal.

A new configuration starts with:

```json
{"theme":"ocean-dark"}
```

Normal startup does not create configuration files. Without configuration, the game uses its hardcoded Ocean Dark palette. Ocean Dark remains available if theme files are absent; invalid settings or an unavailable saved theme also fall back to it.

`MINESWEEPER_CONFIG_DIR` can override the configuration directory for portable setups and isolated tests. Otherwise the path is exactly `~/.config/minesweeper`.

## Choose a theme

Open **Settings → Themes** on the main menu, press **t** from the menu or game, or click **[t]** on the game toolbar.

Type into the filter to narrow the list by theme name or filename. Matching is case-insensitive for ASCII letters. **Tab** and **Shift+Tab** cycle through all themes when the filter is empty, or just the matching themes otherwise. Up/Down also work. **Enter** applies the selected theme and atomically saves its filename stem in `settings.json`. **Escape** cancels without changing the current theme or saved preference.

Click a listed theme to apply it, or use the mouse wheel to navigate. Left/Right and Home/End move the text cursor; click inside the field to position it. Typing inserts at the cursor, Backspace erases before it, Delete erases after it, and Ctrl+U clears the field. Long queries scroll within the box to keep the cursor visible. The game timer pauses while a popup is open.

Bundled themes:

| Theme | Palette |
| --- | --- |
| Ocean Dark | Ocean editor theme colors: navy surfaces, blue cursor, syntax accents |
| Ocean Light | The corresponding light Ocean editor palette |
| Midnight | The original charcoal and slate-blue Minesweeper palette |
| Graphite | Neutral dark gray surfaces with restrained number accents |

Ocean Dark and Ocean Light derive their palettes from `ocean-c/editors/helix/themes/`, shared with Ocean's VS Code and Rex themes.

## Custom themes

Add a lowercase `.toml` file to `~/.config/minesweeper/themes/`. Its filename, without `.toml`, is its stable ID. The picker reloads installed files whenever it opens. Invalid theme files are skipped with a message.

Theme files use a small TOML schema: an optional quoted `name`, then a `[colors]` table containing quoted `#RRGGBB` values. Missing colors inherit the hardcoded Ocean Dark defaults. Unknown keys, duplicates, invalid colors, and invalid strings are rejected. See [themes/README.md](themes/README.md) for all color roles and the complete bundled examples.

```toml
name = "My Blue Theme"

[colors]
background = "#101820"
accent = "#88bbff"
cursor = "#aaccff"
```

## Play

Choose Beginner (9×9, 10 mines), Intermediate (16×16, 40 mines), or Expert (30×16, 99 mines). The first reveal and its neighbors are safe. Empty regions open automatically. Reveal every non-mine cell to win.

| Action | Keyboard | Mouse |
| --- | --- | --- |
| Choose menu entry | Up/Down, j/k, Tab; Enter/Space | Click entry |
| Start difficulty | 1 / 2 / 3 in menu | Click difficulty |
| Move selection | Arrows, WASD, hjkl | Click a cell |
| Reveal | Enter / Space | Left click |
| Toggle flag | f | Right click |
| Chord | c, or reveal an open number | Middle click, or left click an open number |
| Toggle left-click flagging | — | Click Flag button |
| Pan viewport | Move selection past the visible edge | Click < / > / ^ / v |
| Reset at current difficulty | r | Click Reset |
| Save | v | Click Save |
| Save to a custom filename | Shift+S | Click Save as |
| Theme picker | t | Click [t], or Settings → Themes |
| Save and return to menu | m / Escape | Click Menu |
| Save and quit | q during game | Click Save+Quit |
| Quit main menu | q | Click Quit |
| Exit immediately without saving | Ctrl+C | — |

A chord reveals the unflagged neighbors of an open number when its adjacent flag count matches the number. Incorrect flags can make a chord reveal a mine.

Reset clears reveals and flags, resets the timer and selection, and creates a fresh board at the same difficulty. It does not replace the saved file until you save again. Resume continues the current unfinished game, or loads the default saved file if no unfinished game is active.

## Save and resume

Save initially writes `minesweeper.save` in your user save folder, preserving the board, flags, reveals, selection, and elapsed time. The folder is created on the first save. The save confirmation disappears after 900 ms. Completed games cannot be saved.

| Platform | User save folder |
| --- | --- |
| Linux and other XDG systems | `$XDG_DATA_HOME/minesweeper/saves/`, defaulting to `~/.local/share/minesweeper/saves/` |
| macOS | `~/Library/Application Support/Minesweeper/saves/` |
| Windows | `JungleHornet\Minesweeper` under the Saved Games known folder, usually `%USERPROFILE%\Saved Games` |

Set `MINESWEEPER_SAVE_DIR` to an absolute path to override the folder. If the user-wide `minesweeper.save` is missing, **Resume** tries the old default file in the working directory. The next save writes to the user folder and the original file stays in place.

**Save as** opens a filename entry. A bare name such as `weekend.save` goes in the user save folder. Explicit relative paths such as `./weekend.save` or `old/weekend.save` resolve from the working directory, and absolute paths work as entered. Enter submits, Left/Right and Home/End move the cursor, and clicking inside the field positions it. Typing inserts at the cursor; Backspace erases before it and Delete erases after it. Ctrl+U clears, Tab changes focus between the field and buttons, and Escape cancels. Long filenames scroll within the field, preserving the popup border and keeping the cursor visible. A successful save under a new name makes that path the current game's save target.

Updating the same board's save proceeds immediately. Saving over a different board opens a centered dialog with **Overwrite**, **Save as**, and **Cancel**. Menu and quit requests also offer **Exit without saving**. Cancel returns to the game without saving or leaving it. The game timer pauses while the dialog is open. Popups zoom from the center when opening and shrink back when closing, with the fill extending through their rounded border cells. Switching between screens within one popup is immediate.

The last main-menu option, **Resume from other game**, opens a scrollable picker of files in the user save folder. It includes hidden files and does not filter by save extension. Use arrows, Page Up/Down, Home/End, the mouse wheel, or click a file. The first option lets you type a filename or an explicit path. Invalid saves show an error and leave the picker open. Loading a file makes it the game's save target.

To delete a save, choose **Delete** beside it in the picker or highlight it and press **Delete**. In **Save as** or the custom filename dialog, enter the filename or path, then choose the **Delete** button. The confirmation shows the file path and starts with **Cancel** selected. Choose **Delete** in the confirmation to remove the file.

## Verify

```sh
ocean check .
ocean test . --notty
ocean build . -o minesweeper
python3 tests/terminal.py
python3 tests/preferences.py
python3 tests/entries.py
python3 tests/popups.py
python3 tests/redraw.py
```

Tests cover game rules, Unicode-safe popup layout, settings and theme parsing, installation, filtering, keyboard/mouse selection, persistence, malformed files, save/resume, overwrites, resizing, and terminal cleanup. Integration tests use temporary configuration and save directories.

The built-in TUI's incremental renderer repaints only changed styled rows, clears stale content after painting, and uses synchronized output mode 2026 where supported. `tests/redraw.py` checks actual PTY traffic: cursor movement updates its board row, timer ticks update the status row, and neither clears the viewport. Pass `--baseline /path/to/unpatched-binary` to compare traffic.

The historical renderer patch in `patches/` and its temporary-library helper in
`scripts/ocean.py` are retained for reference. Normal builds use the compiler's
matching standard library directly; no patch wrapper is needed.
