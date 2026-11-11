"""ja_hien.py — tieng Nhat: thay chu doc (hiragana) bang chu hien thi (kanji, so) + moc tung cum chu cho phu de va 'at'.

Chay SAU prep_voice.py. File voice (02-VOICE) co the viet phien am hiragana de giong AI doc dung,
con phu de / nhan / 'at' phai la chu hien thi (02-HIENTHI, cung so doan, ngan bang '|').
  python tools/ja_hien.py --project projects/<ten> --text "<02-HIENTHI-<slug>.txt>" [--sep '|']

- Moi doan '|' cua 02-HIENTHI ung voi 1 doan cua 02-VOICE (1 file voice). Doc gop 1 file (--single) cung duoc:
  bo dung tu tim diem bat dau tung doan theo khoang lang.
- Ket qua ghi de timeline/lines.json (moi cau 1 dong, chu da tach cum bang dau cach), words.json (moi cum 1 muc),
  transcript.txt. Giu nguyen voice.wav.
"""
import argparse, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SR, load_audio, read_json, write_json, pauses

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True); ap.add_argument("--text", required=True)
ap.add_argument("--sep", default="|")
a = ap.parse_args(); TL = os.path.join(a.project, "timeline")

# ---------- tach cum (gan dung bunsetsu): cat khi chuyen tu hiragana sang kanji/katakana/so, sau dau cau
def cls(c):
    o = ord(c)
    if 0x3041 <= o <= 0x309f: return "H"
    if 0x30a0 <= o <= 0x30ff or c == "ー": return "T"
    if 0x3400 <= o <= 0x9fff or 0xf900 <= o <= 0xfaff or c in "々〆ヶ": return "K"
    if c.isalnum() or c in "０１２３４５６７８９.,%％": return "N"
    if c in "、。，．！？!?」』）)…・：:": return "PE"
    if c in "「『（(": return "PO"
    return "O"

def ja_tokens(text):
    toks, cur, prev = [], "", None
    for c in re.sub(r"\s+", "", text):
        k = cls(c)
        new = cur and ((k in ("K", "T", "N") and prev == "H") or k == "PO" or (prev == "PE" and k != "PE"))
        if new: toks.append(cur); cur = ""
        cur += c; prev = k
        if prev == "PO": prev = "O"
    if cur: toks.append(cur)
    # cum qua dai (hiragana lien) -> chia doi
    out = []
    for t in toks:
        while len(t) > 12: out.append(t[:8]); t = t[8:]
        out.append(t)
    return out

def mora(t):
    w = 0.0
    for c in t:
        k = cls(c)
        if k == "H" or k == "T": w += 0 if c in "ゃゅょぁぃぅぇぉャュョァィゥェォ" else 1
        elif k == "K": w += 1.8
        elif k == "N": w += 1.6
        elif c in "、，": w += 0.9
    return max(w, 0.5)

def sentences_ja(seg):
    parts = re.findall(r"[^。！？!?]+[。！？!?」』]*", seg)
    return [p.strip() for p in parts if p.strip()] or [seg]

def align(y, units):
    """units: trong so tung don vi; tra ve moc bat dau (giay, tinh tu dau y). Moc bam vao khoang lang gan du doan."""
    L = len(y) / SR; n = len(units)
    if n <= 1: return [0.0]
    pz = [(s, e) for s, e in pauses(y, 0.09) if 0.1 < s and e < L - 0.1]
    speech = max(L - sum(e - s for s, e in pz) * 0.7, L * 0.5)
    res = [0.0]; t = 0.0; rem = sum(units)
    for i in range(n - 1):
        rate = (L - t) / max(rem, 1e-6)
        exp = t + units[i] * rate; win = max(0.35, units[i] * rate * 0.45)
        cand = [(abs((s + e) / 2 - exp) - 0.5 * min(e - s, 0.5), e) for s, e in pz if t + 0.25 < e and abs((s + e) / 2 - exp) < win]
        nt = min(cand)[1] - 0.03 if cand else exp
        nt = min(max(nt, t + 0.25), L - 0.2 * (n - 1 - i)); res.append(nt); t = nt; rem -= units[i]
    return res

def align_dp(y, w):
    """chia doan dai (1 file voice gop) thanh n phan: ranh gioi o khoang lang, do dai gan voi trong so w (quy hoach dong)."""
    L = len(y) / SR; n = len(w)
    if n <= 1: return [0.0]
    pz = [(s, e) for s, e in pauses(y, 0.12) if 0.1 < s and e < L - 0.15]
    tot = sum(w); rs = max(L - sum(e - s for s, e in pz), L * 0.5) / tot
    B = [e - 0.02 for s, e in pz]; D = [e - s for s, e in pz]; Z = len(B); P_ = n - 1
    if Z < P_: return align(y, w)
    c = lambda k, x0, x1: (((x1 - x0) - w[k] * rs - 0.2) / max(w[k] * rs, 0.5)) ** 2
    INF = 1e18; f = [[INF] * Z for _ in range(P_)]; bk = [[-1] * Z for _ in range(P_)]
    for z in range(Z): f[0][z] = c(0, 0.0, B[z]) - 0.8 * min(D[z], 0.7)
    for k in range(1, P_):
        for z in range(Z):
            best, arg = INF, -1
            for z2 in range(z - 1, -1, -1):
                if B[z] - B[z2] > w[k] * rs * 3 + 3: break
                if f[k - 1][z2] < INF:
                    v = f[k - 1][z2] + c(k, B[z2], B[z])
                    if v < best: best, arg = v, z2
            if arg >= 0: f[k][z] = best - 0.8 * min(D[z], 0.7); bk[k][z] = arg
    endc = [f[P_ - 1][z] + c(n - 1, B[z], L) if f[P_ - 1][z] < INF else INF for z in range(Z)]
    if min(endc) >= INF: return align(y, w)
    z = min(range(Z), key=lambda q: endc[q]); res = [0.0] * P_
    for k in range(P_ - 1, -1, -1): res[k] = B[z]; z = bk[k][z]
    return [0.0] + res

raw = open(a.text, encoding="utf-8-sig").read().replace("\r\n", "\n").strip()
segs = [" ".join(x.split()) for x in raw.split(a.sep)] if a.sep and a.sep in raw else [l.strip() for l in raw.splitlines() if l.strip()]
segs = [s for s in segs if s]
blocks = read_json(os.path.join(TL, "blocks.json"), [])
if not blocks or not os.path.exists(os.path.join(TL, "voice.wav")): sys.exit("Chua co timeline/blocks.json, voice.wav. Chay tools/prep_voice.py truoc.")
y = load_audio(os.path.join(TL, "voice.wav"))
# khung thoi gian tung doan
if len(blocks) == len(segs):
    spans = [(b["start"], b["end"], b["id"], b.get("drop", False)) for b in blocks]
elif len(blocks) == 1:
    b = blocks[0]; s0, s1 = b["start"], b["end"]
    st = align_dp(y[int(s0 * SR):int(s1 * SR)], [sum(mora(t) for t in ja_tokens(s)) for s in segs])
    spans = [(s0 + st[i], s0 + (st[i + 1] if i + 1 < len(st) else s1 - s0), f"V{i+1:03d}", False) for i in range(len(segs))]
    for i, (x0, x1, bid, _) in enumerate(spans):
        if i + 1 < len(spans): spans[i] = (x0, spans[i + 1][0] - 0.02, bid, False)
    blocks = [{"id": bid, "slot": "NARRATOR", "char": "", "drop": False, "text": segs[i], "start": round(x0, 3), "end": round(x1, 3)} for i, (x0, x1, bid, _) in enumerate(spans)]
    write_json(os.path.join(TL, "blocks.json"), blocks)
else:
    sys.exit(f"So doan khong khop: 02-HIENTHI co {len(segs)} doan, voice co {len(blocks)} khoi. Kiem tra lai ky tu '{a.sep}' o 2 file.")

lines, words = [], []
for (s0, s1, bid, drop), seg in zip(spans, segs):
    sents = sentences_ja(seg); toks = [ja_tokens(s) for s in sents]
    yy = y[int(s0 * SR):int(s1 * SR)]
    st = align(yy, [sum(mora(t) for t in ts) for ts in toks])
    for i, (s, ts) in enumerate(zip(sents, toks)):
        a0 = s0 + st[i]; a1 = s0 + st[i + 1] if i + 1 < len(st) else s1
        lines.append({"id": f"L{len(lines)+1:03d}", "block": bid, "slot": "NARRATOR", "char": "", "text": " ".join(ts), "start": round(a0, 3), "end": round(a1 - 0.02, 3), "drop": drop})
        # moc tung cum trong cau: bam khoang lang sau dau phay, con lai chia theo mora
        cw = [mora(t) for t in ts]
        sub = y[int(a0 * SR):int(a1 * SR)]
        cl, cur = [], []
        for j, t in enumerate(ts):
            cur.append(j)
            if re.search(r"[、，]$", t) or j == len(ts) - 1: cl.append(cur); cur = []
        cst = align(sub, [sum(cw[j] for j in c) for c in cl]) if len(cl) > 1 else [0.0]
        for ci, c in enumerate(cl):
            c0 = a0 + cst[ci]; c1 = a0 + cst[ci + 1] if ci + 1 < len(cst) else a1 - 0.06
            tot = sum(cw[j] for j in c); acc = 0
            for j in c:
                w0 = c0 + (c1 - c0) * acc / tot; acc += cw[j]; w1 = c0 + (c1 - c0) * acc / tot
                words.append({"w": ts[j], "t": round(w0, 3), "e": round(w1 - 0.02, 3)})

write_json(os.path.join(TL, "lines.json"), lines); write_json(os.path.join(TL, "words.json"), words)
with open(os.path.join(TL, "transcript.txt"), "w", encoding="utf-8") as f:
    for l in lines: f.write(f"{l['start']:8.2f}  {l['block']}  {l['text'].replace(' ', '')}\n")
print(f"Xong: {len(segs)} doan, {len(lines)} cau, {len(words)} cum chu (chu hien thi). -> {TL}")
