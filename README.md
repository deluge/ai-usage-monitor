# AI Usage Monitor

I built a small desk display for my Claude usage limits using a **1.54" OLED display (oled_m154_7p, 7-pin SPI, 128×64)**, driven either by a **Raspberry Pi Zero W** or an **ESP32-C3 Super Mini**. Once the board starts and joins my Wi-Fi, it automatically shows my **current** (5-hour) and **weekly** usage, each with a progress bar and the time when it resets. No keyboard, monitor or browser needed.

![Display preview: loading screen and usage screen](docs/preview.png)

*Left to right: loading screen at boot and the usage display (Raspberry Pi version).*

## Choose your board

This README covers everything both boards have in common. The board-specific steps (hardware, wiring, installation, configuration) are in separate guides:

| Board | Runs | Guide |
|---|---|---|
| Raspberry Pi Zero W / Zero 2 W | Python 3 on Raspberry Pi OS, started by systemd | [README_RASPBERRY_PI.md](README_RASPBERRY_PI.md) |
| ESP32-C3 Super Mini | MicroPython, starts on power-up | [README_ESP32_C3.md](README_ESP32_C3.md) |

The Pi version is easier to debug over SSH and has a 3D-printable case. The ESP32 is cheaper, smaller, uses less power and is ready a few seconds after you plug it in.

## What it shows

| Line | Meaning |
|---|---|
| `Current 42%` | Usage of the rolling 5-hour session window |
| `Reset 00:30 (0h54)` | When that window resets, plus a live countdown |
| `Weekly 18%` | Usage of the rolling 7-day window |
| `Reset Thu 29.10. 09:00` | When the weekly limit resets |

The values are fetched every 2 minutes. Until the first data arrives, the display shows `Loading...`. Both boards use the same font (DejaVu Sans) and layout, so the display looks the same on either.

## How it works

Claude Code shows your limits with `/usage`. Behind that is an **undocumented** endpoint (`https://api.anthropic.com/api/oauth/usage`) that returns the same numbers. The board calls this endpoint with your Claude login credentials and keeps the login fresh by refreshing the token itself.

> [!CAUTION]
> This is not an official Anthropic API and this project is not affiliated with Anthropic. The endpoint may change or disappear at any time, which would break the display until the code is updated. It only works with Claude subscription plans (Pro/Max), not with API keys.

## Repository contents

| File | Purpose |
|---|---|
| `display_usage/monitor.py` | `UsageMonitor`: fetches the usage and keeps the display updated |
| `display_usage/api.py` | `ClaudeApi`: credentials, token refresh and usage requests |
| `display_usage/display.py` | `BaseDisplay`: the screen layout, drawn with a few primitives each board implements |
| `display_usage/utils.py` | Shared helpers: logging, time and `Timezone`, reset time formatting |
| `display_usage/errors.py` | Exceptions shared by the modules above |
| `display_usage/pizerow/display.py` | `Oled_m154_7p` for the Raspberry Pi (luma.oled, TrueType fonts) |
| `display_usage/esp32/display.py` | `Oled_m154_7p` for the ESP32 (MicroPython's `ssd1306` driver) |
| `display_usage/esp32/wifi.py` | `Wifi`: Wi-Fi connection and clock sync on the ESP32 |
| `display_usage/esp32/font.py` | `BitmapFont`: draws the bitmap fonts below |
| `display_usage/esp32/dejavu_sans_*.py` | DejaVu Sans as bitmap fonts for the ESP32 (generated) |
| `tools/make_esp32_fonts.py` | Generates the ESP32 bitmap fonts from `DejaVuSans.ttf` |
| `show_my_usage.py` | Your own Pi start script with your settings (not in git) |
| `main.py` | Your own ESP32 start script with your settings (not in git) |
| `credentials.example.json` | Shape of the credentials file |
| `pyproject.toml` / `uv.lock` | Development tools and settings (managed with [uv](https://docs.astral.sh/uv/)); the boards don't use them |
| `Makefile` | Shortcuts for formatting and checking code (`make help`) |
| `3Dprint/pizero_oled154_case.scad` | OpenSCAD source of the Pi case (adjustable) |
| `3Dprint/pizero_oled154_case.stl` | Ready-to-print Pi case (body and bottom plate) |

## The display

Both boards use the same display:

- 1.54" OLED, 128×64, 7-pin SPI (SSD1309 controller; SSD1306 variants work too)
- 7 female-to-female jumper wires (or soldered header)

![1.54" OLED module oled_m154_7p, front and back](docs/displays/oled_m154_7p/display.png)

*The display module used here (front and back). The back is labeled `OLED_M154_7P`.*

The OLED is monochrome. The text color (white, blue, yellow, green…) is fixed by the display you buy and cannot be changed in software.

The pin order on the display can differ between sellers, so always wire by the labels printed on your board: `GND`, `VCC`, `SCL` (SPI clock), `SDA` (SPI data), `RES` (reset), `DC` (data/command) and `CS` (chip select). Power it with **3.3 V**.

## Get your Claude login credentials

Both boards need a copy of your Claude login. The board guides tell you when to do this.

You need [Claude Code](https://claude.com/claude-code) on your computer, logged in with your Claude account (run `claude`, then `/login`). A token from `claude setup-token` does **not** work: it lacks the permission for usage data and returns HTTP 403.

Read the stored credentials on your computer:

- **macOS** (stored in the Keychain, not as a file):
  ```bash
  security find-generic-password -s "Claude Code-credentials" -w
  ```
- **Windows**: `%USERPROFILE%\.claude\.credentials.json` (hidden file; in PowerShell: `notepad $env:USERPROFILE\.claude\.credentials.json`)
- **Linux**: `cat ~/.claude/.credentials.json`

The output is a JSON object containing `claudeAiOauth`. When you put it on the board, change the value after `"expiresAt":` to `0`. This makes the board refresh the token right away, so it gets its own login (see [Sharing the login](#sharing-the-login-between-board-and-computer)). The result looks like `credentials.example.json`.

> [!IMPORTANT]
> These credentials give full access to your Claude account. Never commit them to Git or share them. The `.gitignore` excludes `credentials.json`.

## Log in again on your computer

Once the board has refreshed its token (the display shows your usage), open Claude Code on your computer and run `/login` once. Use `/login`, not `/logout`, since logging out may revoke the shared session.

## Sharing the login between board and computer

Both devices start out with the same login. When one of them refreshes the token, the other one's copy becomes invalid. Setting `expiresAt` to `0` lets the board refresh first; a fresh `/login` on the computer then gives the computer its own session. After that, both run independently.

You only need to copy the credentials again if the board was off for a long time (weeks), or if you change your password or log out everywhere. The display will show `HTTP 401` in that case.

## Configuration

All settings are passed to the classes in your start script (`show_my_usage.py` on the Pi, `main.py` on the ESP32). These settings are the same on both boards; the display and Wi-Fi settings are listed in the board guides.

**`ClaudeApi`**

| Setting | Default | Meaning |
|---|---|---|
| `credentials_file` | Pi: `~/.usage-monitor/credentials.json`, ESP32: `credentials.json` | Where your login credentials are stored |
| `timeout` | `20` | Seconds to wait for an API response |

**`UsageMonitor`**

| Setting | Default | Meaning |
|---|---|---|
| `wifi` | `None` | The `Wifi` connection on the ESP32; not needed on the Pi |
| `api_request_interval` | `120` | Seconds between API requests (don't go too low) |
| `display_refresh_interval` | `30` | Seconds between screen redraws (updates the countdown) |

**`Timezone`** (passed to `Oled_m154_7p` as `timezone`)

| Setting | Default | Meaning |
|---|---|---|
| `utc_offset` | `None` | Your standard (winter) time offset from UTC in hours, e.g. `1` for Germany, `-5` for New York, `5.5` for India. `None` uses the system's timezone, which is right on the Pi; the ESP32 has none, so set it there |
| `dst` | `None` | Summer time rule: `"eu"` (last Sunday in March to last Sunday in October), `"us"` (second Sunday in March to first Sunday in November) or `None` |

## Troubleshooting

These apply to both boards. See the board guides for wiring, network and startup problems.

| Display / log | Likely cause | Fix |
|---|---|---|
| `No credentials` | File missing | Put the credentials on the board (see the board guide) |
| `HTTP 403` | `setup-token` used, or request blocked | Use the `claudeAiOauth` login credentials ([see above](#get-your-claude-login-credentials)) |
| `HTTP 401` | Token invalid or expired | Copy fresh credentials, set `expiresAt` to `0`, restart |
| `Token refresh at …: HTTP 404` in the log | Anthropic changed the refresh URL | Update `TOKEN_URLS` in `display_usage/api.py` |

## Development

The boards don't need any of this; it's only for working on the code on your computer. Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv venv
make devinstall   # installs ruff and ipdb into .venv
make check        # check formatting and lint rules (same as the GitHub workflow)
make correct      # fix formatting and lint issues
```

### Code structure

Both boards run the same code. Everything in `display_usage/` runs on the Pi (Python 3) and on the ESP32 (MicroPython), so it only uses what MicroPython supports (no `datetime`, `threading` or `os.path`). Only the hardware-specific parts live in `display_usage/pizerow/` and `display_usage/esp32/`:

- `ClaudeApi` uses `requests`, which both Python 3 and MicroPython provide with the same interface.
- `UsageMonitor` runs one loop that fetches and redraws; on the ESP32 it also keeps the `Wifi` connected.
- `BaseDisplay` draws the whole screen with five primitives (`clear`, `show`, `text`, `textlength`, `rectangle`). Each board's `Oled_m154_7p` implements them for its display driver. To support another display or board, write such a subclass.

### ESP32 fonts

MicroPython can't read TTF fonts, so the ESP32 uses DejaVu Sans pre-rendered as bitmaps (`display_usage/esp32/dejavu_sans_*.py`). They are rendered with Pillow the same way the Pi draws text, so both displays show the same pixels. The sizes come from `BaseDisplay.FONT_SIZE` and `SMALL_FONT_SIZE`. To regenerate them after changing those, download `DejaVuSans.ttf` and run from the project folder:

```bash
uv run --no-project --with pillow python -B -m tools.make_esp32_fonts /path/to/DejaVuSans.ttf
```
