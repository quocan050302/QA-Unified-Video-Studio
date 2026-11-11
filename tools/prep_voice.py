"""prep_voice.py — ghep voice tung dong (Dgt Auto TTS / ElevenLabs) thanh 1 file + moc thoi gian tung cau, tung chu.

Che do 1 (khuyen dung): moi khoi V### la 1 file mp3, xuat tu Dgt theo file 02-VOICE-<slug>-DGT.txt
  python tools/prep_voice.py --project projects/<ten> --voice-dir "<thu muc mp3>" --voice-txt "<02-VOICE-<slug>.txt>" [--map "<02-VOICE-<slug>-MAP.txt>"]
Che do 2: mot file voice lien cho ca bai + kich ban (moi dong = 1 cau hoac doan van)
  python tools/prep_voice.py --project projects/<ten> --single "<voice.mp3>" --script "<script.txt>"

Ket qua trong projects/<ten>/timeline/: voice.wav, blocks.json, lines.json, words.json, transcript.txt
"""
import argparse, glob, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SR, load_audio, save_wav, write_json, trim, pauses, sentences

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--voice-dir"); ap.add_argument("--voice-txt"); ap.add_argument("--map")
ap.add_argument("--lines", help="1 giong doc: file chu, moi dong = 1 file voice (dong 1 -> 1.mp3...)")
ap.add_argument("--sep", default="|", help="ky tu tach doan (Auto Split cua tool voice), mac dinh |")
ap.add_argument("--drop", default="", help="cac dong can tat nhac, vd 57,112")
ap.add_argument("--single"); ap.add_argument("--script")
ap.add_argument("--gap", type=float, default=0.30, help="khoang nghi giua 2 khoi cung nguoi noi")
ap.add_argument("--speaker-gap", type=float, default=0.18, help="khoang nghi khi doi nguoi noi")
ap.add_argument("--max-pause", type=float, default=0.45, help="cat moi khoang lang ben trong dai hon muc nay (0 = giu nguyen)")
ap.add_argument("--lead", type=float, default=0.5, help="khoang lang dau video")
ap.add_argument("--lang", default="en", help="ngon ngu voice cho whisper: en, vi, ja...")
ap.add_argument("--whisper", default="", help="che do 1 file: dung faster-whisper (vd small) de lay moc tung chu chinh xac hon; can mang toi huggingface.co lan dau")
a = ap.parse_args()
P = a.project; TL = os.path.join(P, "timeline"); os.makedirs(TL, exist_ok=True)

def parse_voice_txt(path):
    txt = open(path, encoding="utf-8-sig").read()
    blocks = []
    for m in re.finditer(r"^===\s*(V\d+)\s*\|\s*([^=]*?)\s*===\s*\n(.*?)(?=^===|\Z)", txt, re.S | re.M):
        head = [x.strip() for x in m.group(2).split("|")]
        slot_char = head[0].split("·"); slot = slot_char[0].strip(); char = slot_char[1].strip() if len(slot_char) > 1 else ""
        body = " ".join(l.strip() for l in m.group(3).strip().splitlines() if l.strip())
        blocks.append({"id": m.group(1), "slot": slot, "char": char, "drop": any(h.upper() == "DROP" for h in head[1:]), "text": body})
    return blocks

def parse_lines(path):
    raw = open(path, encoding="utf-8-sig").read()
    # co ky tu tach (mac dinh |) thi moi doan giua 2 ky tu tach = 1 file voice; khong co thi moi dong = 1 file
    rows = [" ".join(x.split()) for x in raw.split(a.sep)] if a.sep and a.sep in raw else raw.splitlines()
    rows = [r.strip() for r in rows if r.strip()]
    drop = {int(x) for x in a.drop.replace(" ", "").split(",") if x}
    return [{"id": f"V{i:03d}", "slot": "NARRATOR", "char": "", "drop": i in drop, "text": t} for i, t in enumerate(rows, 1)]

def parse_map(path):
    m = {}
    if not path or not os.path.exists(path): return m
    for line in open(path, encoding="utf-8-sig"):
        r = re.match(r"\s*(\d+)\s*\S+\s*(V\d+)", line)
        if r: m[int(r.group(1))] = r.group(2)
    return m

def tighten(y, maxp):
    if maxp <= 0: return y
    out, last = [], 0
    for s, e in pauses(y, maxp + 0.05):
        cut = (e - s) - maxp; a0 = int((s + maxp / 2) * SR); a1 = int((s + maxp / 2 + cut) * SR)
        out.append(y[last:a0]); last = a1
    out.append(y[last:]); return np.concatenate(out)

def split_sentences(y, sents):
    """moc bat dau tung cau trong 1 doan am thanh: gan ranh gioi vao khoang lang that (quy hoach dong)."""
    L = len(y) / SR; n = len(sents)
    if n == 1: return [0.0]
    w = [max(1, len(re.sub(r"[\W_]", "", s))) for s in sents]; tot = sum(w)
    exp, acc = [], 0
    for x in w[:-1]: acc += x; exp.append(acc / tot * L)
    pz = [(s, e) for s, e in pauses(y, 0.12 if n <= 6 else 0.08) if e < L - 0.15 and s > 0.1]
    P_, Z = n - 1, len(pz)
    if n > 6:
        # doan dai (1 file voice lien): di tuan tu, moi moc du doan tu moc that truoc do -> khong troi
        # quy hoach dong toan doan: moi cau dai gan voi du doan theo so ky tu, ranh gioi uu tien khoang lang dai
        rs = max(L - sum(e - s_ for s_, e in pz), L * 0.5) / tot
        B = [e - 0.02 for s_, e in pz]; D = [e - s_ for s_, e in pz]; Zn = len(B)
        def c(k, a, b):
            d = w[k] * rs; act = b - a
            return ((act - d - 0.15) / max(d, 0.5)) ** 2
        INF = 1e18; f = [[INF] * Zn for _ in range(P_)]; bk = [[-1] * Zn for _ in range(P_)]
        for z in range(Zn): f[0][z] = c(0, 0.0, B[z]) - 0.8 * min(D[z], 0.6)
        for k in range(1, P_):
            for z in range(Zn):
                best, arg = INF, -1
                for z2 in range(z - 1, -1, -1):
                    if B[z] - B[z2] > w[k] * rs * 3 + 2.5: break
                    if f[k - 1][z2] >= INF: continue
                    v = f[k - 1][z2] + c(k, B[z2], B[z])
                    if v < best: best, arg = v, z2
                if arg >= 0: f[k][z] = best - 0.8 * min(D[z], 0.6); bk[k][z] = arg
        endc = [f[P_ - 1][z] + c(n - 1, B[z], L) if f[P_ - 1][z] < INF else INF for z in range(Zn)]
        if Zn >= P_ and min(endc) < INF:
            z = min(range(Zn), key=lambda q: endc[q]); res = [0.0] * P_
            for k in range(P_ - 1, -1, -1): res[k] = B[z]; z = bk[k][z]
        else: res = exp
    elif Z >= P_ and P_ > 0:
        avg = max(L / n, 0.5); cost = lambda k, z: 0.5 * abs((pz[z][0] + pz[z][1]) / 2 - exp[k]) / avg - 0.6 * min(pz[z][1] - pz[z][0], 0.8)
        INF = 1e9; f = [[INF] * (Z + 1) for _ in range(P_ + 1)]
        for z in range(Z + 1): f[0][z] = 0.0
        for k in range(1, P_ + 1):
            for z in range(k, Z + 1): f[k][z] = min(f[k][z - 1], f[k - 1][z - 1] + cost(k - 1, z - 1))
        res = [0.0] * P_; k, z = P_, Z
        while k > 0:
            if z > k and abs(f[k][z] - f[k][z - 1]) < 1e-12: z -= 1; continue
            res[k - 1] = pz[z - 1][1] - 0.02; k -= 1; z -= 1
    else:
        res = exp
    out, last = [0.0], 0.0
    for t in res: t = max(t, last + 0.3); out.append(t); last = t
    return out

def words_in(sent, t0, t1):
    ws = sent.split(); wl = [max(1, len(re.sub(r"[\W_]", "", x))) + 1 for x in ws]; tot = sum(wl); out = []; acc = 0
    for x, l in zip(ws, wl):
        s = t0 + (t1 - t0) * acc / tot; acc += l; e = t0 + (t1 - t0) * acc / tot
        out.append({"w": re.sub(r"^[\"'(“]+|[\"'),.!?:;”…]+$", "", x), "t": round(s, 3), "e": round(e - 0.03, 3)})
    return out

if a.single:
    script = open(a.script, encoding="utf-8-sig").read() if a.script else ""
    sents = sentences(script)
    y = trim(load_audio(a.single)); y = tighten(y, a.max_pause)
    offs = split_sentences(y, sents) if sents else [0.0]
    lead = np.zeros(int(a.lead * SR)); voice = np.concatenate([lead, y])
    blocks = [{"id": "V001", "slot": "NARRATOR", "char": "", "drop": False, "text": script, "start": a.lead, "end": round(a.lead + len(y) / SR, 3)}]
    lines, words = [], []
    for i, s in enumerate(sents):
        st = a.lead + offs[i]; en = a.lead + (offs[i + 1] if i + 1 < len(offs) else len(y) / SR)
        lines.append({"id": f"L{i+1:03d}", "block": "V001", "slot": "NARRATOR", "char": "", "text": s, "start": round(st, 3), "end": round(en, 3), "drop": False})
        words += words_in(s, st, en - 0.08)
else:
    if not (a.voice_dir and (a.voice_txt or a.lines)): sys.exit("Can --voice-dir va --voice-txt (nhieu giong) hoac --lines (1 giong), hoac --single.")
    blocks = parse_lines(a.lines) if a.lines else parse_voice_txt(a.voice_txt)
    if not blocks: sys.exit("Khong doc duoc khoi nao trong file voice (dang '=== V001 | NARRATOR ===').")
    files = [f for f in glob.glob(os.path.join(a.voice_dir, "*")) if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))]
    named = {os.path.splitext(os.path.basename(f))[0].upper(): f for f in files}
    num = lambda f: int(re.search(r"\d+", os.path.basename(f)).group()) if re.search(r"\d+", os.path.basename(f)) else 10 ** 9
    files.sort(key=num); mp = parse_map(a.map)
    audio = {}
    if a.lines: audio = {f"V{num(f):03d}": f for f in files if num(f) < 10 ** 9}
    elif all(b["id"] in named for b in blocks): audio = {b["id"]: named[b["id"]] for b in blocks}
    else:
        for i, f in enumerate(files): audio[mp.get(num(f), blocks[i]["id"] if i < len(blocks) else None)] = f
    missing = [b["id"] for b in blocks if b["id"] not in audio]
    if len(files) != len(blocks): print(f"CANH BAO: {len(files)} file voice nhung co {len(blocks)} {'dong' if a.lines else 'khoi'}. Chi dung cac {'dong' if a.lines else 'khoi'} co file.")
    if missing: print("Khoi chua co voice (bo qua):", ", ".join(missing[:20]))
    blocks = [b for b in blocks if b["id"] in audio]
    voice = [np.zeros(int(a.lead * SR))]; t = a.lead; prev = None; lines, words = [], []; li = 0
    for b in blocks:
        y = tighten(trim(load_audio(audio[b["id"]])), a.max_pause)
        if prev is not None:
            g = a.speaker_gap if b["slot"] != prev else a.gap
            voice.append(np.zeros(int(g * SR))); t += g
        b["start"] = round(t, 3); L = len(y) / SR; b["end"] = round(t + L, 3); b["file"] = os.path.basename(audio[b["id"]])
        sents = sentences(b["text"]) or [b["text"]]
        offs = split_sentences(y, sents)
        for i, s in enumerate(sents):
            li += 1; st = t + offs[i]; en = t + (offs[i + 1] if i + 1 < len(offs) else L)
            lines.append({"id": f"L{li:03d}", "block": b["id"], "slot": b["slot"], "char": b["char"], "text": s, "start": round(st, 3), "end": round(en, 3), "drop": b["drop"]})
            words += words_in(s, st, en - 0.06)
        voice.append(y); t += L; prev = b["slot"]
    voice = np.concatenate(voice)

voice = np.concatenate([voice, np.zeros(int(1.5 * SR))])
save_wav(os.path.join(TL, "voice.wav"), voice)

if a.single and a.whisper:
    # can lai moc bang Whisper: khop tung chu kich ban voi tung chu Whisper nghe duoc
    import difflib
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("Chua cai faster-whisper: python -m pip install faster-whisper")
    model = WhisperModel(a.whisper, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(os.path.join(TL, "voice.wav"), word_timestamps=True, language=a.lang)
    ww = [(x.word, x.start, x.end) for sg in segs for x in (sg.words or [])]
    norm = lambda x: re.sub(r"[\W_]", "", x.lower())
    sw = []; owner = []
    for li, s_ in enumerate(sents):
        for x in s_.split(): sw.append(x); owner.append(li)
    A = [norm(x) for x in sw]; Bw = [norm(x[0]) for x in ww]
    tmap = [None] * len(A)
    for m in difflib.SequenceMatcher(None, A, Bw, autojunk=False).get_matching_blocks():
        for k in range(m.size): tmap[m.a + k] = (ww[m.b + k][1], ww[m.b + k][2])
    known = [i for i, t in enumerate(tmap) if t]
    print(f"Whisper khop {len(known)}/{len(A)} chu ({100 * len(known) // max(1, len(A))}%).")
    for i in range(len(A)):
        if tmap[i] is None:
            lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
            t0 = tmap[lo][1] if lo is not None else 0.0; t1 = tmap[hi][0] if hi is not None else len(voice) / SR - 1.5
            span = (hi if hi is not None else len(A)) - (lo if lo is not None else -1)
            fr = (i - (lo if lo is not None else -1)) / span; t = t0 + (t1 - t0) * fr; tmap[i] = (t, t + 0.2)
    words = [{"w": re.sub(r"^[\"'(\u201c]+|[\"'),.!?:;\u201d\u2026]+$", "", sw[i]), "t": round(tmap[i][0], 3), "e": round(tmap[i][1], 3)} for i in range(len(A))]
    for li, l in enumerate(lines):
        idx = [i for i, o in enumerate(owner) if o == li]
        l["start"] = round(tmap[idx[0]][0] - 0.05, 3); l["end"] = round(tmap[idx[-1]][1] + 0.05, 3)
write_json(os.path.join(TL, "blocks.json"), blocks)
write_json(os.path.join(TL, "lines.json"), lines)
write_json(os.path.join(TL, "words.json"), words)
with open(os.path.join(TL, "transcript.txt"), "w", encoding="utf-8") as f:
    for l in lines: f.write(f"[{l['start']:7.2f} - {l['end']:7.2f}] {l['block']} {l['slot']:<9} {l['text']}\n")
dur = len(voice) / SR
print(f"Xong: {len(blocks)} khoi, {len(lines)} cau, {len(words)} chu. Voice dai {dur:.1f} giay -> {TL}/voice.wav")
print("Buoc tiep: python tools/draft_shots.py --project " + P)
