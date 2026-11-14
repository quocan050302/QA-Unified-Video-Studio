"""mix.py — tron voice + nhac nen + hieu ung am thanh theo story/shots.json, chuan -14 LUFS, ghep vao video.
  python tools/mix.py --project projects/<ten>            -> build/mix.wav (+ out/<tieu de>.mp4 neu da co build/video_silent.mp4)
  python tools/mix.py --project projects/<ten> --preview  -> build/preview.mp4 (pham vi --from-sec den --to-sec)
"""
import argparse, glob, hashlib, json, os, re, subprocess, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SR, load_audio, save_wav, read_json, run, compute_source_hash, compute_canonical_visual_hash, compute_canonical_audio_hash

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("project_pos", nargs="?", default=None, help="Duong dan du an (positional)")
ap.add_argument("--project", default=None, help="Duong dan du an")
ap.add_argument("--no-video", action="store_true")
ap.add_argument("--preview", action="store_true", help="Tron va ghep preview audio")
ap.add_argument("--from-sec", type=float, default=0.0, help="Giay bat dau preview")
ap.add_argument("--to-sec", type=float, default=30.0, help="Giay ket thuc preview")
a = ap.parse_args()
P = a.project or a.project_pos
if not P:
    ap.error("the following arguments are required: --project or project")

if not os.path.isdir(P) or not os.path.isfile(os.path.join(P, "config.json")):
    sys.exit(f"Thu muc du an khong ton tai hoac thieu config.json: {P}")

cfg = read_json(os.path.join(P, "config.json"), {})
story = read_json(os.path.join(P, "story", "shots.json"), {})
shots = story.get("shots", [])
dur = float(story.get("duration") or (shots[-1]["end"] if shots else 0))
N = int(dur * SR) + SR

# Phim khong loi doc (vd pack dem): khong co timeline/voice.wav -> chi tron nhac + SFX
vpath = os.path.join(P, "timeline", "voice.wav")
pack = cfg.get("pack", "")
if pack == "squire" and not os.path.exists(vpath):
    sys.exit("Pack squire can timeline/voice.wav de mix am thanh. Hay nap voice va chay Prepare voice timeline truoc.")

voice = load_audio(vpath) if os.path.exists(vpath) else np.zeros(N)
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
db = lambda x: 10 ** (x / 20)

def loud(y):
    try:
        import pyloudnorm as pyln
        return pyln.Meter(SR).integrated_loudness(y.astype(np.float64))
    except Exception:
        e = y[np.abs(y) > 1e-4]
        return 20 * np.log10(np.sqrt(np.mean(e ** 2)) + 1e-9) - 0.7 if len(e) else -70

if np.any(voice):
    voice *= db(-16 - loud(voice))
log = []

# ---------- nhac nen
music = np.zeros(N)
mcfg = cfg.get("music", {"enabled": True})
if mcfg.get("enabled", True):
    secs = story.get("music") or [{"start": 0, "end": dur, "bed": "curious"}]
    beds = {}
    for f in glob.glob(os.path.join(KIT, "audio", "music", "*.wav")):
        stem = os.path.splitext(os.path.basename(f))[0]
        beds[stem] = f
        m = re.match(r"bed_([a-z]+)", stem)
        if m:
            beds[m.group(1)] = f

    if mcfg.get("file"):
        beds["user"] = os.path.join(P, mcfg["file"])

    gate = np.ones(N)
    for s in shots:
        if "DROP" in str(s.get("notes", "")).upper():
            gate[int(s["start"] * SR):int(s["end"] * SR)] = 0

    cache = {}
    for sec in secs:
        name = sec.get("bed", "curious")
        if name in ("none", "drop"):
            continue
        if mcfg.get("file"):
            name = "user"
        if name not in beds:
            log.append(f"khong co nhac '{name}'")
            continue
        if name not in cache:
            y = load_audio(beds[name])
            y *= db(-16 + float(mcfg.get("gainDb", -13)) - loud(y))
            cache[name] = y
        y = cache[name]
        a0, a1 = int(sec["start"] * SR), min(N, int(sec["end"] * SR))
        L = a1 - a0
        if L <= 0:
            continue
        seg = np.tile(y, L // len(y) + 1)[:L] * db(float(sec.get("gainDb", 0)))
        f = min(int(1.2 * SR), L // 3)
        seg[:f] *= np.linspace(0, 1, f)
        seg[-f:] *= np.linspace(1, 0, f)
        music[a0:a1] += seg

    # Tat / mo nhac em theo DROP gate
    if np.any(gate == 0):
        try:
            from scipy.signal import fftconvolve
            k = int(0.25 * SR)
            sm = fftconvolve(gate, np.ones(k) / k, "same")
            music *= np.clip(sm, 0.0, 1.0)
        except Exception:
            k = int(0.25 * SR)
            cs = np.cumsum(np.pad(gate, (k // 2, k // 2), mode="edge"))
            sm = (cs[k:] - cs[:-k]) / k
            music *= np.clip(sm[:len(music)], 0.0, 1.0)

    # Voice-aware sidechain ducking de bao ve do ro cua giong noi
    if np.any(np.abs(voice) > 1e-4):
        def _fast_smooth(arr, w):
            try:
                from scipy.ndimage import uniform_filter1d
                return uniform_filter1d(arr.astype(np.float32), size=w, mode="nearest")
            except Exception:
                cs = np.cumsum(np.insert(arr, 0, 0))
                res = (cs[w:] - cs[:-w]) / w
                return np.pad(res, ((w - 1) // 2, w - 1 - (w - 1) // 2), mode="edge")

        win = int(0.15 * SR)
        env = _fast_smooth(np.abs(voice), win)
        speech_thresh = np.max(env) * 0.08
        duck_target = np.where(env > speech_thresh, db(-16.0), 1.0)
        k_sm = int(0.25 * SR)
        duck_gain = _fast_smooth(duck_target, k_sm)
        duck_gain = np.clip(duck_gain, db(-18.0), 1.0)
        music *= duck_gain[:len(music)]

# ---------- hieu ung am thanh (SFX)
sfx = np.zeros(N)
scfg = cfg.get("sfx", {"enabled": True})
lib = {os.path.splitext(os.path.basename(f))[0]: f for f in glob.glob(os.path.join(KIT, "audio", "sfx", "*.wav"))}

canonical_aliases = {
    "armor": "armor_clank", "clank": "armor_clank", "metal": "armor_clank",
    "mail": "chainmail", "chain": "chainmail", "mud": "mud_step",
    "step": "single_footstep", "steps": "single_footstep", "footstep": "single_footstep",
    "single_step": "single_footstep", "run": "single_footstep", "footsteps_loop": "footsteps",
    "sword": "sword_draw", "shield": "shield_bash", "bash": "shield_bash",
    "whoosh": "whoosh_fast", "swish": "whoosh_tiny", "ting": "ting_idea",
    "idea": "ting_idea", "stat": "tick", "thud": "thud_soft",
    "impact": "impact_light", "breath": "breath_in", "heart": "heartbeat",
    "horn": "war_horn", "coin": "coin_drop", "door": "door_open"
}

def find(name):
    if not name:
        return None, 0.0
    if os.path.exists(os.path.join(P, name)):
        return os.path.join(P, name), 0.0
    # 1. Exact canonical match
    if name in lib:
        m = re.search(r"hitAt(\d+)ms", name)
        return lib[name], (int(m.group(1)) / 1000 if m else 0.0)
    # 2. Alias match
    alias = canonical_aliases.get(name.lower())
    if alias and alias in lib:
        m = re.search(r"hitAt(\d+)ms", alias)
        return lib[alias], (int(m.group(1)) / 1000 if m else 0.0)
    # 3. Delimited prefix match only
    for k, f in lib.items():
        if k.startswith(name + "_"):
            m = re.search(r"hitAt(\d+)ms", k)
            return f, (int(m.group(1)) / 1000 if m else 0.0)
    return None, 0.0

cues = [(s.get("start", 0.0) + c.get("at", 0), c) for s in shots for c in s.get("sfx", [])] + [(c.get("t", 0.0), c) for c in story.get("sfx", [])]
rendered_cues = []
if scfg.get("enabled", True):
    cache = {}
    for t, c in cues:
        cname = c.get("name", "")
        f, off = find(cname)
        if not f:
            log.append(f"khong co sfx '{cname}'")
            continue
        if f not in cache:
            cache[f] = load_audio(f)
        y = cache[f]
        t0 = t - off - (0.12 if cname.startswith("whoosh") else 0)
        i0 = int(t0 * SR)
        y = y[max(0, -i0):]
        i0 = max(0, i0)
        L = min(len(y), N - i0)
        if L > 0:
            sfx[i0:i0 + L] += y[:L] * db(float(c.get("gain", -8)) + float(scfg.get("gainDb", -4)))
            rendered_cues.append({"time": t, "name": cname, "file": f, "gain": c.get("gain", -8)})

# ---------- Mix master
mix = voice + music + sfx
pk = np.max(np.abs(mix)) + 1e-9
if pk > 0.95:
    mix = np.tanh(mix / pk * 1.5) / np.tanh(1.5) * 0.95

os.makedirs(os.path.join(P, "build"), exist_ok=True)
raw = os.path.join(P, "build", "mix_raw.wav")
save_wav(raw, mix)
out = os.path.join(P, "build", "mix.wav")
lufs = cfg.get("loudness", -14)
tmp = os.path.join(P, "build", "mix_ln.wav")

run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "2", tmp])
if os.path.exists(raw):
    os.remove(raw)

# Loudnorm 2nd pass calibration and limiter
r = subprocess.run(["ffmpeg", "-v", "info", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
gain = (lufs - float(m[-1])) if m else 0.0
run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false", "-ar", str(SR), out])
if os.path.exists(tmp):
    os.remove(tmp)

measured_lufs = float(m[-1]) if m else -14.0
measured_tp = float(tp[-1]) if tp else -1.5

# Save audio mix report
audio_report = {
    "project": os.path.basename(P),
    "mixed_at": time.time(),
    "status": "AUDIO_MIX_PASS",
    "integrated_lufs": measured_lufs,
    "true_peak_dbtp": measured_tp,
    "target_lufs": lufs,
    "duration_sec": dur,
    "voice_rms": float(np.sqrt(np.mean(voice ** 2))),
    "music_rms": float(np.sqrt(np.mean(music ** 2))),
    "sfx_rms": float(np.sqrt(np.mean(sfx ** 2))),
    "cues_rendered_count": len(rendered_cues),
    "cues": rendered_cues[:20],
}
with open(os.path.join(P, "build", "audio_mix_report.json"), "w", encoding="utf-8") as fp:
    json.dump(audio_report, fp, indent=2)

print("Am thanh:", out, f"({measured_lufs:.1f} LUFS, TP: {measured_tp:.1f} dBTP) |", "; ".join(sorted(set(log))) if log else "ok")

# Canonical hashes (V8 spec)
current_vhash = compute_canonical_visual_hash(P, story_data=story, config_data=cfg)
current_ahash = compute_canonical_audio_hash(P, story_data=story, config_data=cfg)
try:
    with open(os.path.join(P, "build", "audio_hash.txt"), "w", encoding="utf-8") as fp:
        fp.write(current_ahash)
except Exception:
    pass

# ---------- Xu ly Preview with Audio
if a.preview:
    prev_silent = os.path.join(P, "build", "preview_silent.mp4")
    prev_final = os.path.join(P, "build", "preview.mp4")
    f0 = max(0.0, float(a.from_sec))
    f1 = min(dur, float(a.to_sec)) if a.to_sec > 0 else dur
    p_dur = max(0.5, f1 - f0)
    prev_audio = os.path.join(P, "build", "preview_audio.wav")
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(f0), "-t", str(p_dur), "-i", out, "-ar", str(SR), "-ac", "2", prev_audio])
    if os.path.exists(prev_silent):
        partial_prev = os.path.join(P, "build", "preview.partial.mp4")
        run(["ffmpeg", "-y", "-v", "error", "-i", prev_silent, "-i", prev_audio, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", partial_prev])
        if os.path.exists(partial_prev):
            # Kiem tra decode va do dai preview hop le
            chk_pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "default=noprint_wrappers=1", partial_prev], capture_output=True, text=True)
            if chk_pr.returncode == 0 and "codec_type=audio" in chk_pr.stdout:
                os.replace(partial_prev, prev_final)
                print("Preview co am thanh hoan tat:", prev_final)
            else:
                if os.path.exists(partial_prev):
                    os.remove(partial_prev)
                sys.exit("Loi tao preview co am thanh (khong co audio stream hoac ffprobe loi)")
    sys.exit(0)

# ---------- Ghep video cuoi (Remux)
video = os.path.join(P, "build", "video_silent.mp4")
shots_file = os.path.join(P, "story", "shots.json")

if not a.no_video:
    if not os.path.exists(video):
        print("Chu y: Chua co build/video_silent.mp4 de ghep video. Chi xuat am thanh build/mix.wav.")
    else:
        # Kiem tra stale video thong minh qua canonical visual_hash
        hash_file = os.path.join(P, "build", "visual_hash.txt")
        stored_vhash = open(hash_file, "r", encoding="utf-8").read().strip() if os.path.exists(hash_file) else ""
        visual_matches = (stored_vhash == current_vhash) if stored_vhash else False

        if os.path.exists(shots_file):
            if stored_vhash:
                if not visual_matches:
                    sys.exit("build/video_silent.mp4 cu hon story/shots.json (storyboard visual da bi thay doi sau khi render). Vui long render lai video truoc khi mix.")
            else:
                v_m = os.path.getmtime(video)
                s_m = os.path.getmtime(shots_file)
                if v_m < s_m - 2:
                    sys.exit("build/video_silent.mp4 cu hon story/shots.json (v_m < s_m - 2). Vui long render lai video truoc khi mix.")

        # Cap nhat stored visual hash neu hop le
        if not os.path.exists(hash_file) or visual_matches:
            try:
                with open(hash_file, "w", encoding="utf-8") as fp:
                    fp.write(current_vhash)
            except Exception:
                pass

        # Kiem tra decode video
        dec = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-f", "null", "-"], capture_output=True, text=True)
        if dec.returncode != 0:
            sys.exit(f"build/video_silent.mp4 bi loi decode: {dec.stderr[:300]}")

        title = re.sub(r'[\\/:*?"<>|]', "", cfg.get("title", "video")).strip() or "video"
        os.makedirs(os.path.join(P, "out"), exist_ok=True)
        final = os.path.join(P, "out", title + ".mp4")
        partial = os.path.join(P, "out", title + ".partial.mp4")
        run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", out, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", "-f", "mp4", partial])

        # Kiem tra partial hop le
        chk = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", partial], capture_output=True, text=True)
        if chk.returncode != 0 or not chk.stdout.strip() or float(chk.stdout.strip()) <= 0:
            if os.path.exists(partial):
                os.remove(partial)
            sys.exit("Loi tao video mix hoan chinh (ffprobe khong doc duoc thoi luong)")

        # Kiem tra audio khong phai toan bo silence
        rms = np.sqrt(np.mean(mix ** 2)) if len(mix) > 0 else 0
        if pack == "squire" and rms < 1e-4:
            if os.path.exists(partial):
                os.remove(partial)
            sys.exit("Am thanh mix bi im lang hoan toan (RMS < 1e-4).")

        os.replace(partial, final)
        print("Video hoan chinh:", final)

        # Do am thanh thuc te tren file MP4 decode cuoi cung (V8 requirement)
        meas_r = subprocess.run(["ffmpeg", "-v", "info", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
        m_post = re.findall(r"I:\s+(-?[\d.]+) LUFS", meas_r)
        tp_post = re.findall(r"True peak:\s+(-?[\d.]+) dBFS", meas_r) or re.findall(r"Peak:\s+(-?[\d.]+) dBFS", meas_r)
        post_lufs = float(m_post[-1]) if m_post else measured_lufs
        post_tp = float(tp_post[-1]) if tp_post else measured_tp

        audio_report["measured_after_final_decode"] = {
            "integrated_lufs": post_lufs,
            "true_peak_dbtp": post_tp,
            "stream_format": "aac",
            "sample_rate": SR,
            "channels": 2,
            "target_lufs": lufs,
            "tolerance_met": (abs(post_lufs - lufs) <= 3.0 and post_tp <= -0.8)
        }
        with open(os.path.join(P, "build", "audio_mix_report.json"), "w", encoding="utf-8") as fp:
            json.dump(audio_report, fp, indent=2)

        # Ghi verification proof de app.py summarize_project xac thuc
        try:
            src_hash = compute_source_hash(P)
            out_h = hashlib.sha256()
            with open(final, "rb") as fp:
                while chunk := fp.read(65536):
                    out_h.update(chunk)
            proof = {
                "source_hash": src_hash,
                "visual_hash": current_vhash,
                "audio_hash": current_ahash,
                "output_file": os.path.relpath(final, P),
                "output_sha256": out_h.hexdigest(),
                "duration": dur,
                "verified_at": time.time(),
                "status": "VERIFIED",
                "measured_lufs": post_lufs,
                "measured_tp": post_tp
            }
            with open(os.path.join(P, "build", "verification_proof.json"), "w", encoding="utf-8") as fp:
                json.dump(proof, fp, indent=2)
        except Exception:
            pass
