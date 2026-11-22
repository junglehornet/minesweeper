# Theme files

Copy a `.toml` file into `~/.config/minesweeper/themes/`, or run `./minesweeper --install` from the repository to install these defaults. Existing files are preserved. Theme IDs come from filenames without the `.toml` extension.

A theme has an optional quoted `name` before one `[colors]` table. Color values must be quoted `#RRGGBB` strings; hex digits are case-insensitive. Single-quoted literal strings and double-quoted strings with JSON-compatible escapes are supported. Comments and blank lines are allowed. General TOML features such as arrays, dotted keys, multiline strings, and nested tables are outside this schema.

All colors are optional and inherit Ocean Dark when omitted. Duplicate or unknown keys are rejected, so a typo cannot silently change the palette.

| Color role | Used for |
| --- | --- |
| `background` | Screen and game toolbar background |
| `foreground` | Normal text and toolbar labels |
| `muted` | Secondary text and status information |
| `accent` | Titles |
| `text` | Text in dialogs and focused menu entries |
| `surface` | Dialog background |
| `selection` | Focused menu entries and theme list selection |
| `covered_text` | Dots on unrevealed tiles |
| `covered_a`, `covered_b` | Alternating unrevealed tile backgrounds |
| `open_background` | Revealed cell background |
| `flag`, `flag_background` | Flag symbol and its background |
| `flag_cursor` | Background of the selected flag |
| `cursor`, `cursor_text` | Other selected cells |
| `danger`, `danger_background` | Loss/error text, mines, and incorrect flags |
| `number_1` through `number_8` | Foregrounds for numbered cells |

Use a bright cursor color against dark tiles, or a dark cursor against a light palette, so keyboard selection is easy to follow. The number colors should remain readable on `open_background`.

`ocean-dark.toml` matches the built-in fallback exactly. Ocean Dark and Ocean Light use the Ocean editor palettes from `ocean-c/editors/helix/themes/`. Midnight preserves the earlier Minesweeper palette. Graphite uses neutral gray surfaces.
