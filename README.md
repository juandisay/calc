# calc

A safe, lightweight, full-precision CLI calculator — a single Python file with no dependencies.

## Features

- **Full-precision numbers** — billions, trillions, up to thousands of digits (exact integers, no digit limit)
- **Very long expressions** — chains of hundreds of thousands of terms (`1+1+1+…`) evaluated with no depth limit
- **Safe** — AST parser with a whitelist; no free `eval`, no system access
- **4 modes** — argument, unquoted, stdin pipe, interactive REPL
- **Friendly error messages** — clear messages, exit code `1`

## Requirements

- Python **3.9+** (3.11+ recommended so numbers >4300 digits can be printed)

## Installation

```bash
ln -s "$(pwd)/calc" ~/.local/bin/calc   # make sure ~/.local/bin is on your PATH
calc "2+2"
```

Or run directly: `./calc "2+2"`.

## GUI

A PyQt6 desktop GUI (`calc_gui.py`) wraps the same engine — no duplicated logic:

```bash
python3 -m venv .venv
.venv/bin/pip install PyQt6
.venv/bin/python calc_gui.py
```

Features: expression line with Enter to evaluate, ↑/↓ input history, a
clickable history panel (click to reuse, double-click to re-run), a button
pad for operators and functions, `ans`, and a Help dialog listing all
functions. Errors render in red with the same friendly messages as the CLI.

### Building the .dmg

`build_dmg.sh` bundles the GUI with PyInstaller (venv must have
`pyinstaller`), regenerates `calc.icns` if missing, ad-hoc signs the app,
and wraps it as `dist/calc-1.0.0-<arch>.dmg` with an Applications alias for
drag-to-install:

```bash
./build_dmg.sh
open dist/calc-1.0.0-arm64.dmg
```

Notes:

- The engine ships inside the bundle as `calc_engine/calc` — a data file
  named `calc` would collide with the `calc` executable.
- The bundle is signed ad-hoc (no Developer ID). On other Macs, Gatekeeper
  may require right-click → Open on first launch.

## Usage

```bash
calc "2 + 3 * 4"        # 14 — evaluate an expression
calc 2 + 3 * 4          # same, arguments are joined automatically (quote if there is a * so the shell doesn't glob it)
echo "1+2" | calc       # 3 — read from stdin
calc                    # interactive REPL (quit / Ctrl-D to exit)
```

REPL mode:

- `ans` — result of the last calculation
- `help` — help
- `quit`, `exit`, `q`, Ctrl-D — exit

## Operators

| Operator | Meaning |
|---|---|
| `+ - * /` | add, subtract, multiply, divide (float) |
| `//` | floor division |
| `%` | remainder |
| `**` `^` | power (`^` is mapped to `**`) |
| `( )` | grouping |
| `< <= > >= == !=` | comparison (results `True`/`False`) |

Standard mathematical precedence: `2+3^4` = 83, `-2^2` = -4, `10//4` = 2.

## Functions

| Function | Description |
|---|---|
| `sqrt(x)` | square root |
| `sin cos tan asin acos atan` | trigonometry (radians) |
| `atan2(y, x)` | two-argument atan |
| `log(x)` / `ln(x)` / `log2(x)` | log base 10 / e / 2 |
| `exp(x)` | e to the power of x |
| `abs(x)` `round(x[, n])` | absolute value, rounding |
| `floor ceil trunc` | round down / up / truncate |
| `min(…)` `max(…)` | minimum / maximum |
| `hypot(a, b)` | hypotenuse length |
| `deg(x)` `rad(x)` | radians ↔ degrees conversion |
| `fact(n)` | factorial |
| `sum(…)` `mul(…)` | sum / product of many arguments |

Constants: `pi`, `e`, `tau`.

## Precision and limits

- **Exact integers** — `999999999999 + 1` → `1000000000000`; `2^100` → all 31 digits.
- **Unlimited digits** — `10^5000` prints 5001 digits (Python's 4300-digit limit is disabled).
- **Long expressions** — a pure chain of one operator class (`1+2+3+…` or `2*3*4*…`) is folded automatically into `sum(...)`/`mul(...)` before parsing: tested up to **100,000 terms**. Mixed expressions (e.g. `1+2*3`) are limited to depth 15,000 (±30,000 characters) and rejected with a clear message instead of crashing.
- **Floats** — full digits up to IEEE precision are shown: `1e12 * 1.5` → `1500000000000`; extreme numbers use exponential notation.

## Security

Expressions are parsed with `ast` and every node must be on the whitelist; the evaluation namespace has empty `__builtins__`. The following are rejected:

```bash
calc "__import__('os').system('id')"   # error: only direct function calls are supported
calc "open('/etc/passwd')"             # error: unknown name: 'open'
```

## Examples

```bash
calc "999999999999 + 1"                  # 1000000000000
calc "10^15 * 3"                         # 3000000000000000
calc "fact(20)"                          # 2432902008176640000
calc "hypot(3, 4)"                       # 5
calc "round(pi, 2)"                      # 3.14
calc "sum(1, 2, 3, 4, 5)"                # 15
echo "1+1+1+1+1" | calc                  # 5
```
