# FUBAR Labs at RoboCon New Jersey 2026

Booth slideshow for the **3D Printer Playground**, presented by [FUBAR Labs](https://fubarlabs.org) at RoboCon New Jersey 2026 (Bridgewater Commons).

The deck is a single self-contained HTML file: open `FUBAR_Labs_Robocon_presentation.html` in any browser. No server needed.

**View it online:** https://ricklon.github.io/FUBAR_Labs_Robocon/ (add `?kiosk&interval=15` for kiosk mode)

## Files

| Path | What it is |
| --- | --- |
| `FUBAR_Labs_Robocon_presentation.html` | The generated deck (images inlined) |
| `FUBAR_Labs_Robocon_presentation.pptx` | PowerPoint source for most slides |
| `slides/` | Hand-built HTML slides and their images (the prize giveaway slide) |
| `convert.py` | Builds the HTML deck from the pptx plus `slides/` |
| `kiosk.sh` | Runs the deck full-screen in Chrome, auto-advancing and looping |

## Presenting

In the browser:

| Key | Action |
| --- | --- |
| `P` / `F` / `F5` | Toggle present (full-screen) mode |
| `←` / `→`, `Space`, `PgUp` / `PgDn` | Previous / next slide |
| `A` | Toggle autoplay |
| `N` | Show speaker notes |
| `Esc` | Leave present mode |

### Kiosk mode

For an unattended booth screen:

```sh
./kiosk.sh        # 10 seconds per slide
./kiosk.sh 15     # 15 seconds per slide
```

This launches `google-chrome` in kiosk mode with the cursor hidden. Exit with `Alt+F4`. You can also open the HTML file with `?kiosk&interval=15` appended to the URL; it starts looping right away and goes full screen on the first click, tap, or key press.

## Rebuilding the deck

After editing the pptx or anything in `slides/`:

```sh
mkdir -p build && unzip -o FUBAR_Labs_Robocon_presentation.pptx -d build/pptx
uv run --with lxml convert.py build/pptx FUBAR_Labs_Robocon_presentation.html
```

(or `pip install lxml` and run with `python`). Extra hand-built slides and their positions are listed in `EXTRA_SLIDES` in `convert.py`.

## License

Code is MIT licensed (see `LICENSE`). The FUBAR Labs name, logo, and slide content belong to FUBAR Labs.
