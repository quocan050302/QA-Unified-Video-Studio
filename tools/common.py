"""common.py — doc/ghi am thanh qua ffmpeg, doc file du an. Chi can numpy + ffmpeg."""
import json, os, re, subprocess, sys, wave
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
