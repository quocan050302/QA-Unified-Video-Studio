"""common.py — doc/ghi am thanh qua ffmpeg, doc file du an. Chi can numpy + ffmpeg."""
import json, os, re, subprocess, sys, wave
from typing import Any, Dict, List, Optional
import numpy as np

SR = 48000

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"Loi khi chay: {' '.join(cmd[:4])}...\n{r.stderr[-800:]}")
    return r.stdout

def load_audio(path, sr=SR, ch=1):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-acodec", "pcm_f32le", "-ac", str(ch), "-ar", str(sr), "-"], capture_output=True)
    if p.returncode:
        sys.exit(f"Khong doc duoc am thanh: {path}\n{p.stderr.decode()[-500:]}")
    y = np.frombuffer(p.stdout, dtype=np.float32).copy()
    return y.reshape(-1, ch) if ch > 1 else y

def save_wav(path, y, sr=SR):
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 1: y = y[:, None]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(y.shape[1]); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())

def duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip()
    return float(out or 0)

def read_json(path, default=None):
    if not os.path.exists(path): return default
    with open(path, encoding="utf-8") as f: return json.load(f)

def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1)

def rms_env(y, hop=0.01, sr=SR):
    h = int(hop * sr); n = len(y) // h
    if n < 1: return np.zeros(1)
    return np.sqrt(np.mean(y[: n * h].reshape(n, h) ** 2, 1) + 1e-12)

def trim(y, thr=0.004, sr=SR, pre=0.03, post=0.08):
    idx = np.where(np.abs(y) > thr)[0]
    if len(idx) == 0: return y
    a = max(0, idx[0] - int(pre * sr)); b = min(len(y), idx[-1] + int(post * sr))
    return y[a:b]

def pauses(y, min_len=0.12, sr=SR):
    """khoang lang ben trong (giay): [(start, end)]"""
    e = rms_env(y, 0.01, sr)
    if len(e) < 3: return []
    thr = max(np.percentile(e, 20) * 1.8, e.max() * 0.04)
    low = e < thr; res = []; s = None
    for i, l in enumerate(low):
        if l and s is None: s = i
        if not l and s is not None:
            if (i - s) * 0.01 >= min_len and s > 0: res.append((s * 0.01, i * 0.01))
            s = None
    return res

def sentences(text):
    """tach cau: giu dau cau, khong tach so thap phan; chu hoa moi ngon ngu (Viet, Anh...)"""
    parts, cur = [], ""
    for tok in re.split(r'(?<=[.!?…])\s+', text.strip()):
        nxt = tok.lstrip('"\'“(')
        if cur and nxt and (nxt[0].isupper() or nxt[0].isdigit()):
            parts.append(cur.strip()); cur = tok
        else:
            cur = (cur + " " + tok) if cur else tok
    if cur.strip(): parts.append(cur.strip())
    return parts

def compute_source_hash(project_dir):
    """Tinh SHA-256 fingerprint mang tinh deterministic cua toan bo source files anh huong toi video.
    Bao gom: config, storyboard, timeline/voice, input scripts, custom scenes (*.js), va image assets (anh/*).
    """
    import hashlib
    from pathlib import Path
    p = Path(project_dir).resolve()
    h = hashlib.sha256()

    fixed_files = (
        'config.json',
        'story/shots.json',
        'timeline/voice.wav',
        'timeline/lines.json',
        'timeline/words.json',
        'input/01-PHIM.txt',
        'input/voice_script.txt',
        'input/voice_source.wav',
    )
    for rel in fixed_files:
        f = p / rel
        if f.is_file():
            try:
                sz = f.stat().st_size
                h.update(f"{rel}:{sz}:".encode('utf-8'))
                with f.open('rb') as fp:
                    while chunk := fp.read(65536):
                        h.update(chunk)
            except OSError:
                pass

    scenes_dir = p / 'scenes'
    if scenes_dir.is_dir():
        for f in sorted(scenes_dir.rglob('*.js')):
            if f.is_file():
                rel = f.relative_to(p).as_posix()
                try:
                    sz = f.stat().st_size
                    h.update(f"{rel}:{sz}:".encode('utf-8'))
                    h.update(f.read_bytes())
                except OSError:
                    pass

    anh_dir = p / 'anh'
    if anh_dir.is_dir():
        for f in sorted(anh_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                rel = f.relative_to(p).as_posix()
                try:
                    sz = f.stat().st_size
                    h.update(f"{rel}:{sz}:".encode('utf-8'))
                    with f.open('rb') as fp:
                        while chunk := fp.read(65536):
                            h.update(chunk)
                except OSError:
                    pass

    return h.hexdigest()


# =========================================================================
# CANONICAL HASHING & MANIFEST SPECIFICATION (V8)
# Python and Node.js cross-language byte-for-byte identical SHA256 hashes
# =========================================================================

NON_VISUAL_ARG_KEYS = {
    "sfx", "music", "audio_gain", "voice_gain", "notes", "cue", "cues",
    "audio_plan", "audio_report", "comment", "audio"
}

def canonical_json_serialize(obj) -> str:
    """Deterministic, cross-language serialization for canonical hashing.
    Produces identical byte sequences in Python and Node.js.
    """
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, (int, np.integer)):
        return str(int(obj))
    if isinstance(obj, (float, np.floating)):
        r = round(float(obj), 4)
        if r == 0.0:
            return "0"
        if r.is_integer():
            return str(int(r))
        return f"{r:.4f}".rstrip("0").rstrip(".")
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(canonical_json_serialize(x) for x in obj) + "]"
    if isinstance(obj, dict):
        # Sort keys lexicographically and skip None/undefined
        items = []
        for k in sorted(obj.keys()):
            v = obj[k]
            if v is not None:
                items.append(f"{json.dumps(str(k), ensure_ascii=False, separators=(',', ':'))}:{canonical_json_serialize(v)}")
        return "{" + ",".join(items) + "}"
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def filter_visual_args(args: Any) -> Any:
    """Filter out audio and non-visual fields from template args."""
    if not isinstance(args, dict):
        return args
    res = {}
    for k, v in args.items():
        if k in NON_VISUAL_ARG_KEYS:
            continue
        if isinstance(v, dict):
            res[k] = filter_visual_args(v)
        elif isinstance(v, list):
            res[k] = [filter_visual_args(x) if isinstance(x, dict) else x for x in v]
        else:
            res[k] = v
    return res


def get_canonical_visual_manifest(project_dir: str, story_data: dict = None, config_data: dict = None) -> dict:
    """Build the versioned canonical visual manifest for a project.
    Contains ONLY visual-impacting attributes (layout, shots, templates, args, custom scenes, visual assets).
    Excludes all audio cues, SFX, music beds, and non-visual notes.
    """
    from pathlib import Path
    p = Path(project_dir).resolve()
    
    cfg = config_data if config_data is not None else read_json(p / "config.json", {}) or {}
    story = story_data if story_data is not None else read_json(p / "story" / "shots.json", {}) or {}

    manifest = {
        "manifest_version": "v8_visual_v1",
        "config": {
            "pack": str(cfg.get("pack", "squire")),
            "aspect": str(cfg.get("aspect", "16:9")),
            "resolution": str(cfg.get("resolution", "1080p")),
            "fps": int(cfg.get("fps", 24)),
            "style": str(cfg.get("style", "flat")),
        },
        "shots": [],
        "visual_assets": {}
    }

    for s in story.get("shots", []):
        sh_entry = {
            "id": str(s.get("id", "")),
            "start": round(float(s.get("start", 0.0)), 4),
            "end": round(float(s.get("end", 0.0)), 4),
            "tpl": str(s.get("tpl", "scene")),
            "scene": str(s.get("scene", "")) if s.get("scene") else None,
            "args": filter_visual_args(s.get("args", {}))
        }
        manifest["shots"].append(sh_entry)

    # Collect custom scenes and anh/* assets
    scenes_dir = p / "scenes"
    if scenes_dir.is_dir():
        import hashlib
        for f in sorted(scenes_dir.rglob("*.js")):
            if f.is_file():
                rel = f.relative_to(p).as_posix()
                try:
                    manifest["visual_assets"][rel] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                except OSError:
                    pass

    anh_dir = p / "anh"
    if anh_dir.is_dir():
        import hashlib
        for f in sorted(anh_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                rel = f.relative_to(p).as_posix()
                try:
                    manifest["visual_assets"][rel] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                except OSError:
                    pass

    return manifest


def compute_canonical_visual_hash(project_dir: str, story_data: dict = None, config_data: dict = None) -> str:
    """Compute the 64-char SHA256 of the canonical visual manifest."""
    import hashlib
    manifest = get_canonical_visual_manifest(project_dir, story_data, config_data)
    serialized = canonical_json_serialize(manifest)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_canonical_audio_manifest(project_dir: str, story_data: dict = None, config_data: dict = None) -> dict:
    """Build the versioned canonical audio manifest for a project.
    Contains voice hash, music/sfx config, audio cues, and loudness target.
    """
    from pathlib import Path
    import hashlib
    p = Path(project_dir).resolve()
    
    cfg = config_data if config_data is not None else read_json(p / "config.json", {}) or {}
    story = story_data if story_data is not None else read_json(p / "story" / "shots.json", {}) or {}

    voice_file = p / "timeline" / "voice.wav"
    voice_sha = ""
    if voice_file.is_file():
        try:
            h = hashlib.sha256()
            with voice_file.open("rb") as fp:
                while chunk := fp.read(65536):
                    h.update(chunk)
            voice_sha = h.hexdigest()
        except OSError:
            pass

    manifest = {
        "manifest_version": "v8_audio_v1",
        "voice_sha256": voice_sha,
        "config": {
            "music": cfg.get("music", {"enabled": True, "gainDb": -15}),
            "sfx": cfg.get("sfx", {"enabled": True, "gainDb": -4}),
            "loudness": float(cfg.get("loudness", -14)),
        },
        "shots_audio": [],
        "story_sfx": story.get("sfx", []),
        "story_music": story.get("music", []),
    }

    for s in story.get("shots", []):
        manifest["shots_audio"].append({
            "id": str(s.get("id", "")),
            "sfx": s.get("sfx", []),
            "music": s.get("music")
        })

    return manifest


def compute_canonical_audio_hash(project_dir: str, story_data: dict = None, config_data: dict = None) -> str:
    """Compute the 64-char SHA256 of the canonical audio manifest."""
    import hashlib
    manifest = get_canonical_audio_manifest(project_dir, story_data, config_data)
    serialized = canonical_json_serialize(manifest)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


