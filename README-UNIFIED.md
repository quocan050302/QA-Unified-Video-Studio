# H2 Unified Video Studio — Local-first v0.1

**Purpose:** A personal-use consolidation of the two separately purchased H2 Studio ZIP packages:
- Self-Improvement Short Films (original pack `dem`)
- Squire Animated Military History (original pack `squire`)

The two kits have **22 common files which are byte-for-byte identical**. The merge keeps one copy of the original render engine, Python tools, dependencies and audio generators; adds non-overlapping `packs/dem`, `packs/squire`, and the bundled `packs/doodle`; and preserves both sample projects. The original READMEs, license files, SKILL instructions, and reference guides are preserved under `docs/`.

## Start the dashboard

1. Install **Python 3.9+**, **Node.js 18+**, and **FFmpeg** on your own Mac, Windows or Linux computer.
2. Open a terminal in this extracted directory.
3. Run:

   ```bash
   python app.py --open
   ```

   If `python` is not Python 3, use `python3 app.py --open` (macOS/Linux) or `py -3 app.py --open` (Windows).
4. Open `http://127.0.0.1:7860`. The app binds **locally only**; never expose it to the internet.

## Install rendering dependencies (one-time)

In a second terminal from this directory:

```bash
npm install
npx playwright install chromium
python -m pip install numpy scipy soundfile
python audio/build_audio.py
python tools/doctor.py
```

Use an isolated virtual environment (`python -m venv .venv`) if preferred. Installation downloads third-party packages and a browser; an internet connection is required at least once. `python tools/doctor.py` reports actual missing prerequisites. Optional: `pyloudnorm` for precise loudness matching; `faster-whisper` for advanced alignment with a single voice file.

## Studio workflow

**Self-Improvement:** Select self-improvement, create a project **from the example** (or blank), edit the storyboard JSON; optionally paste your own `01-PHIM` screenplay in the Script tab and run **Compile → storyboard**. Select **Contact sheet**, **Preview 30s**, **Render video**, then **Mix & export MP4**. If no voice exists, the audio mixer uses music and effects only.

**Squire:** Select Military History, create a project **from the example** (or blank), edit shots JSON. Upload an MP3/WAV voice and matching transcript (one line per sentence) in the Script & voice tab, then run **Prepare voice timeline**. Use the same preview/render/mix workflow. The voice file and transcript come from external TTS or your own recording; *built-in generation of TTS using a local model is not yet implemented*.

The sample JSON shots are included as **templates**, not finished episodes. When creating a project from a sample, the source example stays unchanged.

## Important scope (v0.1)

- Included: a working local management dashboard, create/list projects, preserve selectable packs, config editing, JSON story editing, self-improvement screenplay compilation using the original tool, Squire voice file import and timing preparation using the original tool, direct original-engine render/preview/contact sheet/thumbnail, audio-generation step, audio mix, task exit codes and logs, downloadable local output files.
- **Not yet included:** AI auto-writing scripts, direct offline TTS generation, a WYSIWYG animated scene editor, a packaged Mac `.app` / Windows `.exe` installer, task cancel/queue, or proof of fully rendered video output on each target computer.
- The two source licenses say **personal use**, **no redistribution/resale**. This unified copy is for the licensed purchaser's private use. Do **not** publish the source or sell/distribute the bundled software without permission. The originals remain separately available as the provided ZIP files.
- `app.py` is **local only** and not designed for public deployment. Do not proxy it or open a public port.

## Directory map

```
app.py                 # local dashboard backend (Python stdlib)
web/index.html         # frontend, no external JS/CSS dependencies
engine/                # shared animation engine (unchanged)
render.mjs             # shared Playwright + FFmpeg renderer (unchanged)
tools/                 # shared Python helpers (unchanged)
audio/                 # shared Python music / SFX generators (unchanged)
packs/dem/             # self-improvement graphics
packs/squire/          # military history graphics
packs/doodle/          # additional original graphics pack
projects/              # both original demos + user projects
docs/                  # original SKILL docs, guides, license notices
```

## CLI equivalents

```bash
python tools/doctor.py
node render.mjs --project projects/selfimprove-mau --sheet --scale 0.4
node render.mjs --project projects/squire-mau --sheet --scale 0.4
node render.mjs --project projects/squire-mau --from 0 --to 30 --scale 0.5
node render.mjs --project projects/squire-mau
python tools/mix.py --project projects/squire-mau
```

## Validation and honest limits

Core merge: SHA-256 comparison of 22 shared files; *all identical*. Dashboard API smoke tests run using the built-in Python HTTP server, with project creation, script saving, config and story editing, access path validation, and job logs. Producing real MP4s depends on correctly installed local browser/FFmpeg/Node and has not been claimed unless separately tested.
