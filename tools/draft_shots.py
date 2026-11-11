"""draft_shots.py — tao khung story/shots.json tu timeline/lines.json.
Chia theo thoi gian: cau dai hon --max giay tach o dau phay / lien tu, cau ngan hon --min giay gop voi cau sau.
Claude sau do viet lai: them scene / tpl + args, chuyen canh, sfx, nhac.
  python tools/draft_shots.py --project projects/<ten> [--force] [--min 1.6] [--max 4.5]
  (What If nhanh: mac dinh --min 1.6 --max 4.5;  ngach ke chuyen cham kieu Ve Voi: --min 2.5 --max 7)
Neu co input/anh-ai.json ({"A001": {"block": "V003", "text": "..."}}) thi gan san args.img cho shot khop cau.
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_json, write_json
ap = argparse.ArgumentParser(); ap.add_argument("--project", required=True); ap.add_argument("--force", action="store_true")
ap.add_argument("--lead", type=float, default=0.15); ap.add_argument("--min", type=float, default=1.6); ap.add_argument("--max", type=float, default=4.5)
a = ap.parse_args(); P = a.project
out = os.path.join(P, "story", "shots.json")
if os.path.exists(out) and not a.force: sys.exit("Da co story/shots.json (them --force de ghi de).")
lines = read_json(os.path.join(P, "timeline", "lines.json"), [])
words = read_json(os.path.join(P, "timeline", "words.json"), [])
if not lines: sys.exit("Chua co timeline/lines.json. Chay tools/prep_voice.py truoc.")
CONJ = r",\s|;\s|:\s|[、。！？]\s|\s—\s|\s-\s|\s(and|but|or|then|so|because|và|nhưng|rồi|thì|mà|nên|vì|còn)\s"

def split_line(l):
    """cat 1 cau thanh cac doan <= a.max giay, tai dau phay/lien tu gan giua nhat"""
    lw = [w for w in words if l["start"] - 0.01 <= w["t"] <= l["end"]]
    segs = [(l["start"], l["end"], l["text"], 0, len(l["text"].split()))]
    out = []
    while segs:
        s0, s1, txt, w0, w1 = segs.pop(0)
        if s1 - s0 <= a.max or w1 - w0 < 6: out.append((s0, s1, txt)); continue
        best = None
        for m in re.finditer(CONJ, txt):
            k = m.start() + 1; n = len(txt[:k].split())
            if n < 3 or w1 - w0 - n < 3: continue
            tm = lw[w0 + n]["t"] if w0 + n < len(lw) else (s0 + s1) / 2
            score = abs((tm - s0) - (s1 - s0) / 2)
            if best is None or score < best[0]: best = (score, k, n, tm)
        if not best:
            n = (w1 - w0) // 2; ws = txt.split(); k = len(" ".join(ws[:n])) + 1
            tm = lw[w0 + n]["t"] if w0 + n < len(lw) else (s0 + s1) / 2; best = (0, k, n, tm)
        _, k, n, tm = best
        segs[:0] = [(s0, tm, txt[:k].strip(), w0, w0 + n), (tm, s1, txt[k:].strip(), w0 + n, w1)]
    return out

cuts = []
for l in lines:
    for st, en, txt in split_line(l): cuts.append([st, txt, l, en])

imgs = read_json(os.path.join(P, "input", "anh-ai.json"), {}) or {}
norm = lambda x: re.sub(r"[\W_]+", " ", x.lower()).strip()
def phrase_time(text, t0, t1):
    toks = norm(text).split()[:6]
    if not toks: return None
    W = [w for w in words if t0 - 0.05 <= w["t"] <= t1]
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text):  # tieng Nhat: khop chuoi ky tu noi lien
        q = "".join(norm(text).split()); s, own = "", []
        for i, w in enumerate(W): x = "".join(norm(w["w"]).split()); s += x; own += [i] * len(x)
        p = s.find(q[:12]) if q else -1
        return W[own[p]]["t"] if p >= 0 else None
    for i in range(len(W)):
        if all(i + k < len(W) and norm(W[i + k]["w"]) == toks[k] for k in range(len(toks))): return W[i]["t"]
    return None
# cat them canh tai cau neo cua anh AI (de moi anh co canh rieng, dung luc)
anchors = {}
blk = {}
for l in lines: blk.setdefault(l["block"], [l["start"], l["end"]]); blk[l["block"]][1] = l["end"]
for aid, info in sorted(imgs.items()):
    b = blk.get(info.get("block"))
    t = phrase_time(info.get("text", ""), b[0], b[1]) if b else None
    if t is None: t = phrase_time(info.get("text", ""), 0, 1e9)
    if t is None: continue
    anchors[aid] = t
    for i, c in enumerate(cuts):
        if c[0] + 0.8 < t < c[3] - 0.8:
            lw = [w for w in words if c[0] - 0.01 <= w["t"] < c[3]]; n = len([w for w in lw if w["t"] < t - 0.01]); ws = c[1].split()
            if 0 < n < len(ws): cuts[i:i + 1] = [[c[0], " ".join(ws[:n]), c[2], t], [t, " ".join(ws[n:]), c[2], c[3]]]
            break
# gop doan qua ngan voi doan sau (cung khoi, cung nguoi noi), khong vuot --max, khong nuot diem neo anh
merged = []
for c in cuts:
    if merged:
        p = merged[-1]
        if p[3] - p[0] < a.min and c[3] - p[0] <= a.max and p[2]["block"] == c[2]["block"] and p[2]["slot"] == c[2]["slot"] and not any(abs(t - c[0]) < 0.05 for t in anchors.values()):
            p[1] = p[1] + " " + c[1]; p[3] = c[3]; continue
    merged.append(c)

dur = round(lines[-1]["end"] + 1.5, 3)
shots = []
for i, (st, txt, l, _en) in enumerate(merged):
    s = 0.0 if i == 0 else max(shots[-1]["start"] + 0.4, round(st - a.lead, 3))
    if shots: shots[-1]["end"] = s
    sh = {"id": f"s{i+1:03d}", "start": s, "end": None, "line": txt, "speaker": l["slot"], "char": l["char"], "block": l["block"], "scene": "", "set": "", "in": {"type": "cut"}, "sfx": [], "notes": ""}
    if l["slot"] != "NARRATOR": sh["talk"] = [l["start"], l["end"]]
    if l.get("drop"): sh["notes"] = "DROP"
    if re.match(r"(?i)^so what if", txt): sh["notes"] = (sh["notes"] + " TITLE").strip()
    shots.append(sh)
shots[-1]["end"] = dur
# gan anh AI: theo thoi diem cau neo (chinh xac), khong tim thay thi theo khoi
used = set()
for aid, info in sorted(imgs.items()):
    hit = None
    if aid in anchors:
        t = anchors[aid]; hit = next((sh for sh in shots if sh["start"] - 0.4 <= t < sh["end"] and "img" not in sh.get("args", {})), None)
    if not hit:
        cand = [sh for sh in shots if sh["block"] == info.get("block") and "img" not in sh.get("args", {})]; hit = cand[0] if cand else None
    if hit: hit.setdefault("args", {})["img"] = aid; hit["tpl"] = "ai"; used.add(aid)
miss = [k for k in imgs if k not in used]
write_json(out, {"title": read_json(os.path.join(P, "config.json"), {}).get("title", ""), "duration": dur, "shots": shots, "music": [{"start": 0, "end": dur, "bed": "curious"}]})
cfg = read_json(os.path.join(P, "config.json"), {}); cfg["duration"] = dur; write_json(os.path.join(P, "config.json"), cfg)
ds = sorted(sh["end"] - sh["start"] for sh in shots)
print(f"Xong: {len(shots)} shot nhap, dai {dur} giay, trung vi {ds[len(ds)//2]:.1f} giay/shot ({len(shots) / dur * 60:.0f} shot/phut) -> {out}")
if imgs: print(f"Gan {len(used)}/{len(imgs)} anh AI." + (f" Chua gan duoc: {', '.join(miss[:20])}" if miss else ""))
