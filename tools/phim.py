"""phim.py — phim KHONG LOI DOC: doc file kich ban canh (01-PHIM-<slug>.txt) -> story/shots.json nhap (thoi luong, chu, bo dem, nhac, SFX, mau canh doan san).
  python tools/phim.py --project projects/<ten> --phim "<01-PHIM-<slug>.txt>" [--force]

Dinh dang 01-PHIM (moi canh 1 dong dau + cac dong chu):
  TITLE: DISCIPLINE                (dau file, tuy chon)
  ACCENT: red | pink | amber | teal
  [B07] 5s | CẢNH: phòng ngủ đêm, đồng hồ 5:00 kêu, cậu nằm ngủ | HUD: DAY 1 | NHẠC: sad | SFX: alarm_beep@0.3, whoosh_mid
  > Every day started the same.        chu ke chuyen (trang)
  ~ just five more minutes...          giong cam do (chu viet tay mau nhan)
  " [girl] hi.                         bong bong loi noi ([ai] tuy chon, mac dinh hero)
  ! 30 minutes later...                chu to giua man hinh
  @ jay: day 150!!                     tin nhan den (canh dien thoai)
  @me: i relapsed.                     tin nhan minh gui
  {2.5} > He didn't.                   {giay} = hien o giay thu may cua canh (tuy chon)
  # ghi chu                            bo qua
HUD: "DAY 47" | "DAY 3..30" (dem dan) | "DAY 412 -> 0" (gach ve 0) | "SEEN 1,388; KNOWN 0" (2 dong) | "-" (tat). Khong ghi = giu nhu canh truoc.
NHẠC: sad | dark | rise | resolve | hope | tension | none. Khong ghi = giu nhac dang chay.
Dau dong dac biet: "THẺ KẾT: WORD. / dong phu / dong phu mau nhan", "KÊU GỌI" -> mau card / cta.
"""
import argparse, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_json, write_json

ap = argparse.ArgumentParser(); ap.add_argument("--project", required=True); ap.add_argument("--phim", required=True); ap.add_argument("--force", action="store_true")
a = ap.parse_args(); P = a.project
out = os.path.join(P, "story", "shots.json")
if os.path.exists(out) and not a.force: sys.exit("Da co story/shots.json (them --force de ghi de).")
raw = open(a.phim, encoding="utf-8-sig").read()
nfc = lambda s: unicodedata.normalize("NFC", s)
low = lambda s: nfc(s).lower()

meta = {}; beats = []; cur = None
HEAD = re.compile(r"^\s*\[?\s*(B\d+[A-Za-z]?)\s*\]?\s*(\d+(?:[.,]\d+)?)\s*s?\s*(\|.*)?$", re.I)
for line in raw.splitlines():
    s = nfc(line.rstrip())
    if not s.strip() or s.strip().startswith("#"): continue
    m = HEAD.match(s)
    if m:
        cur = {"id": m.group(1).lower(), "dur": float(m.group(2).replace(",", ".")), "tags": {}, "texts": []}
        for part in (m.group(3) or "").split("|")[1:]:
            if ":" in part: k, v = part.split(":", 1); cur["tags"][low(k).strip()] = v.strip()
            elif part.strip(): cur["tags"][low(part).strip()] = ""
        beats.append(cur); continue
    mm = re.match(r"^\s*([A-Z]+)\s*:\s*(.+)$", s)
    if not cur and mm: meta[mm.group(1).lower()] = mm.group(2).strip(); continue
    if not cur: continue
    t_at = None; body = s.strip()
    mt = re.match(r"^\{(\d+(?:[.,]\d+)?)\}\s*(.*)$", body)
    if mt: t_at = float(mt.group(1).replace(",", ".")); body = mt.group(2)
    if body.startswith("@me:"): cur["texts"].append({"kind": "chat", "me": True, "t": body[4:].strip(), "at": t_at}); continue
    if body.startswith("@"): nm, _, tx = body[1:].partition(":"); cur["texts"].append({"kind": "chat", "me": False, "name": nm.strip(), "t": tx.strip(), "at": t_at}); continue
    k = {">": "narr", "~": "tempt", '"': "say", "“": "say", "!": "big"}.get(body[:1])
    if not k: cur["texts"].append({"kind": "narr", "t": body, "at": t_at}); continue
    tx = body[1:].strip(); who = None
    mw = re.match(r"^\[([^\]]+)\]\s*(.*)$", tx)
    if mw: who, tx = mw.group(1).strip(), mw.group(2)
    item = {"kind": k, "t": tx, "at": t_at}
    if who: item["who"] = who
    cur["texts"].append(item)
if not beats: sys.exit("Khong doc duoc canh nao. Dong dau canh dang: [B01] 5s | CẢNH: ...")

def tag(b, *names):
    for n in names:
        for k, v in b["tags"].items():
            if k.startswith(n): return v
    return None
SETS = [("phòng ngủ", "bedroom"), ("giường", "bedroom"), ("bedroom", "bedroom"), ("thành phố", "city"), ("city", "city"), ("phố", "street"), ("mưa", "street"), ("trạm xe", "street"), ("street", "street"),
        ("tủ đồ", "lockers"), ("hành lang", "lockers"), ("locker", "lockers"), ("lớp", "classroom"), ("class", "classroom"), ("sân bóng", "court"), ("court", "court"), ("quán", "cafe"), ("cà phê", "cafe"), ("cafe", "cafe"),
        ("phòng tập", "gym"), ("gym", "gym"), ("bao cát", "gym"), ("cầu thang", "stairs"), ("stairs", "stairs"), ("đồi", "hill"), ("núi", "hill"), ("hoàng hôn", "hill"), ("hill", "hill"), ("gương", "mirror"), ("mirror", "mirror"),
        ("bếp", "kitchen"), ("kitchen", "kitchen"), ("cửa", "doorway"), ("door", "doorway"), ("khoảng tối", "void"), ("void", "void"), ("đèn rọi", "void")]
def guess(scene):
    s = low(scene or "")
    if re.search(r"(cận|close).{0,12}(điện thoại|phone|màn hình)|tin nhắn|chat|feed|lướt|email|hộp thư", s): return "phone", None
    if re.search(r"(cận|close).{0,12}(đồng hồ|clock)", s): return "clock", None
    if re.search(r"(cận|close).{0,12}(lịch|calendar)", s): return "calendar", None
    if re.search(r"sổ tay|notebook|viết chữ", s): return "note", None
    if re.search(r"(cận|close).{0,12}(mặt|face)", s): return "face", None
    if re.search(r"màn đen|nền đen|black", s): return "black", None
    for k, v in SETS:
        if k in s: return "scene", v
    return "scene", "bedroom"

def hud_of(v):
    v = (v or "").strip()
    if v in ("-", "—", "none", "tắt", "off", ""): return None
    rows = []
    for part in re.split(r"[;/]", v):
        part = part.strip()
        m = re.match(r"^([A-Za-zÀ-ỹ ]+?)\s+(\d[\d,]*)\s*(?:(\.\.|→|->)\s*(\d[\d,]*))?\s*$", part)
        if not m: rows.append({"label": part, "n": ""}); continue
        num = lambda x: int(re.sub(r"[^\d]", "", x)) if re.sub(r"[^\d]", "", x) else 0
        r = {"label": m.group(1).strip().upper(), "n": num(m.group(2))}
        if m.group(3) == "..": r = {"label": r["label"], "from": r["n"], "to": num(m.group(4))}
        elif m.group(3): r["reset"] = {"at": None, "to": num(m.group(4))}
        rows.append(r)
    return rows

def hints(scene, st, texts):
    """doan san boi canh + nhan vat tu mo ta canh tieng Viet (Claude se sua lai cho dung)."""
    s = low(scene or ""); sa = {}; acts = {}; actors = []
    m = re.search(r"(\d{1,2}[:h]\d{2})", s)
    if m and st == "bedroom": sa["clock"] = m.group(1).replace("h", ":")
    if st == "bedroom" and re.search(r"kêu|reo|ring", s): sa["ring"] = True
    m = re.search(r"lịch(?: tháng)? ?([a-z]{3})?[^,;]*?tô (\d+)", s)
    if m and st == "bedroom": sa["calendar"] = {"month": (m.group(1) or "oct").upper(), "fill": int(m.group(2))}
    if "đèn bàn" in s and not re.search(r"đèn bàn tắt", s): sa["lamp"] = True
    if "laptop" in s or "máy tính" in s: sa["laptop"] = True
    if "bình minh" in s: sa["sky" if st == "bedroom" else "time"] = "dawn"
    elif "hoàng hôn" in s and st == "city": sa["time"] = "dusk"
    elif re.search(r"\bđêm\b", s) and st == "city": sa["time"] = "night"
    if "mưa" in s and st == "bedroom": sa["sky"] = "rain"
    if "cửa neon" in s or "neon" in s and st == "street": sa["neonDoor"] = 0.3
    if "chim" in s and st == "city": sa["birds"] = True
    who = "band" if "băng đô" in s else "hooded" if "trùm mũ" in s else "hoodie" if "hoodie" in s else "hero"
    face = next((f for k, f in [("khóc", "cry"), ("sợ", "scared"), ("sốc", "shock"), ("buồn", "sad"), ("mệt", "tired"), ("quyết tâm", "determined"), ("gồng", "effort"), ("cười", "smile"), ("trống rỗng", "empty"), ("lo", "worried"), ("giận", "angry")] if k in s), "neutral")
    if st == "bedroom" and re.search(r"nằm|ngủ trong chăn|trong chăn", s):
        acts["bed"] = {"face": "sleep" if "ngủ" in s and "không ngủ" not in s else face}
        if "với tay" in s: acts["bed"]["arm"] = {"at": 0.8}
    elif re.search(r"ngồi mép giường|ngồi trên giường", s): actors.append({"who": who, "x": "bed.sit", "pose": "sitphone" if "điện thoại" in s else "sitsad" if face in ("sad", "cry", "empty") else "sit", "face": face, **({"hold": "phone", "glowFace": "#9fb6ff"} if "điện thoại" in s else {})})
    elif re.search(r"ngồi bàn|ngồi ở bàn", s) and st == "bedroom": actors.append({"who": who, "x": "desk.seat", "pose": "sitdesk", "face": face, "facing": 1})
    elif re.search(r"chạy", s): actors.append({"who": who, "x": 0.15, "run": {"to": 0.85}, "face": "determined"})
    elif re.search(r"đi bộ|bước đi|đi ngang", s): actors.append({"who": who, "x": 0.2, "walk": {"to": 0.75}, "face": face})
    elif re.search(r"ôm gối|ngồi bó gối", s): actors.append({"who": who, "x": 0.5, "pose": "knees", "face": face})
    elif re.search(r"\bcậu\b|nhân vật|anh ta|\bhe\b", s): actors.append({"who": who, "x": 0.45, "pose": "phone" if "điện thoại" in s else "slump" if face in ("sad", "tired", "empty") else "stand", "face": face, **({"hold": "phone", "glowFace": "#9fb6ff"} if "điện thoại" in s else {})})
    if "bóng đen" in s or any(x["kind"] == "tempt" for x in texts):
        actors.append({"who": "voice", "x": 0.62 if not actors else min(0.85, (actors[0]["x"] if isinstance(actors[0]["x"], float) else 0.55) + 0.14), "pose": "reach" if "vai" in s or "với" in s else "stand", "facing": -1, "at": 0.3})
    for k, w in [("bạn bè", "friend"), ("cô gái", "girl"), ("mẹ", "mom"), ("bố", "dad")]:
        if k in s: actors.append({"who": w, "x": 0.72, "pose": "stand", "face": "neutral", "facing": -1})
    if actors: acts["actors"] = actors
    return sa, acts

TEMPT_CPS = 16
def read_time(tx):
    w = len(tx["t"].split())
    if tx["kind"] == "tempt": return 0.9 + len(tx["t"]) / TEMPT_CPS + 0.6
    if tx["kind"] == "say": return 1.6
    if tx["kind"] == "chat": return 1.0 + w * 0.22
    return max(1.8, min(4.5, 1.0 + w * 0.32))

shots = []; music = []; t = 0.0; hud = None; bed = None; warn = []
for b in beats:
    d = b["dur"]; scene = tag(b, "cảnh", "canh", "scene") or ""
    tk = tag(b, "thẻ kết", "the ket", "card"); cta = any(k.startswith(("kêu gọi", "keu goi", "cta")) for k in b["tags"])
    h = tag(b, "hud");
    if h is not None: hud = hud_of(h)
    mz = tag(b, "nhạc", "nhac", "music")
    if mz is not None:
        name = low(mz).split()[0] if mz.strip() else "none"; name = {"tắt": "none", "drop": "none", "off": "none", "buồn": "sad", "tối": "dark", "lên": "rise", "kết": "resolve"}.get(name, name)
        if music: music[-1]["end"] = round(t, 3)
        music.append({"start": round(t, 3), "end": None, "bed": name})
    sfx = []
    for x in (tag(b, "sfx") or "").split(","):
        x = x.strip()
        if not x: continue
        nm, _, tt = x.partition("@"); sfx.append({"at": float(tt) if tt else 0.2, "name": nm.strip(), "gain": -8})
    # chu: xep lan luot
    texts = []; cursor = 0.35; chats = []
    for tx in b["texts"]:
        if tx["kind"] == "chat": chats.append(tx); continue
        at = tx["at"] if tx["at"] is not None else cursor
        item = {"kind": tx["kind"], "t": tx["t"], "at": round(at, 2)}
        if tx.get("who"): item["who"] = tx["who"]
        texts.append(item); cursor = at + read_time(tx)
    # man den co tu 2 dong ke chuyen tro len: dong cuoi thanh dong nhan to (big), giong kenh mau
    if re.search(r"màn đen|nền đen|black", low(scene)) and not any(x["kind"] == "big" for x in texts):
        nar = [x for x in texts if x["kind"] == "narr"]
        if len(nar) >= 2: nar[-1]["kind"] = "big"
    # thoi luong: chu ke chuyen giu toi chu ke chuyen ke tiep / het canh; cam do va bong bong co thoi luong rieng
    for i, it in enumerate(texts):
        nxt = next((x["at"] for x in texts[i + 1:] if x["kind"] == it["kind"]), None)
        if it["kind"] in ("narr", "big"): it["dur"] = round((nxt if nxt is not None else d) - it["at"] - 0.15, 2)
        else: it["dur"] = round(min(read_time(it), (nxt if nxt is not None else d) - it["at"] - 0.1), 2)
    if cursor > d + 0.3: warn.append(f"{b['id']}: chu can {cursor:.1f}s nhung canh chi {d}s")
    sh = {"id": b["id"], "start": round(t, 3), "end": round(t + d, 3), "line": " / ".join(x["t"] for x in b["texts"])[:120], "scene": scene, "in": {"type": "cut"}, "sfx": sfx, "notes": ""}
    if tk is not None:
        parts = [x.strip() for x in tk.split("/")]
        args = {"word": parts[0] if parts else "", "texts": []}
        if len(parts) > 1: args["sub"] = parts[1]
        if len(parts) > 2: args["sub2"] = parts[2]; args["sub2At"] = round(min(d - 1.0, 3.0), 2)
        mp = re.search(r"part\s*(\d+)", low(parts[0])) if parts else None
        sh.update({"tpl": "card", "args": args}); sh["in"] = {"type": "dip", "dur": 0.6}
    elif cta: sh.update({"tpl": "cta", "args": {"line": (texts[0]["t"] if texts else "If this hit, like and subscribe.")}})
    else:
        tp, st = guess(scene); args = {"texts": texts}
        if hud and tp != "black": args["hud"] = {"rows": json.loads(json.dumps(hud))}
        for r in (args.get("hud") or {}).get("rows", []):
            if "reset" in r and r["reset"]["at"] is None: r["reset"]["at"] = round(min(d * 0.5, 1.5), 2)
            if "from" in r: r["at"] = 0.3; r["dur"] = round(max(0.6, d - 0.8), 2)
        if tp == "scene":
            args["set"] = st; sa, acts = hints(scene, st, texts); 
            if sa: args["setArgs"] = sa
            if acts.get("bed"): args["bed"] = acts.pop("bed")
            if acts.get("actors"): args["actors"] = acts["actors"]
        if tp == "clock":
            sl = low(scene); tms = re.findall(r"(\d{1,2}:\d{2})", sl)
            if tms: args["time"] = tms[0]
            if len(tms) > 1: args["timeAt"] = [[round(d * 0.4, 2), tms[1]]]
            if re.search(r"kêu|reo|ring", sl): args["ring"] = True
            if "nhấp nháy" in sl: args["blink"] = True
        if tp == "calendar":
            sl = low(scene); mm = re.search(r"tháng\s+([a-z]{3})", sl); nn = re.findall(r"(\d+)\s*(?:tới|đến|->|→)\s*(\d+)", sl)
            args["month"] = (mm.group(1) if mm else "oct").upper()
            if nn: args["from"], args["to"] = int(nn[0][0]), int(nn[0][1])
            else: args["from"], args["to"] = 0, 20
            args["mode"] = "fill" if "tô màu" in sl else "x"
            if re.search(r"xoá|xóa|về 0", sl): args["reset"] = {"at": round(d * 0.6, 2)}
        if tp == "phone":
            s = low(scene); scr = "chat" if (chats or "tin nhắn" in s or "chat" in s) else "email" if ("email" in s or "hộp thư" in s) else "reel" if ("video" in s or "xem" in s) else "feed"
            args["screen"] = scr
            ART = [("mì", "ramen"), ("ramen", "ramen"), ("xe", "car"), ("ô tô", "car"), ("burger", "burger"), ("hamburger", "burger"), ("pizza", "pizza"), ("giày", "sneakers"), ("chó", "dog"), ("mèo", "cat"), ("biển", "beach"), ("núi", "mountain"), ("hoàng hôn", "sunset"),
                   ("tạ", "gym"), ("gym", "gym"), ("đồng hồ đeo tay", "watch"), ("tiền", "money"), ("game", "game"), ("cà phê", "coffee"), ("thành phố", "city"), ("tiệc", "party"), ("selfie", "selfie"), ("cô gái", "girl"), ("gái", "girl"), ("donut", "donut"), ("bánh kem", "cake")]
            found = []
            for k, v in ART:
                i = s.find(k)
                if i >= 0 and v not in [f[1] for f in found]: found.append((i, v))
            found = [v for _, v in sorted(found)]
            if scr == "feed" and found: args["posts"] = found
            if scr == "reel" and found: args["art"] = found[0]
            if scr == "feed" and re.search(r"lướt nhanh|nhanh", s): args["hold"] = 0.6
            if chats:
                c0 = 0.4; msgs = []
                for c in chats:
                    at = c["at"] if c["at"] is not None else c0; msgs.append({"text": c["t"], "me": c["me"], "at": round(at, 2)}); c0 = at + read_time(c)
                    if not c["me"] and c.get("name"): args["name"] = c["name"]
                args["messages"] = msgs
        sh.update({"tpl": tp, "args": args})
        # nhan vat goi y theo chu
        if tp == "scene" and any(x["kind"] == "tempt" for x in texts): sh["notes"] = "co giong cam do: them actor who=voice"
    if hud and sh.get("tpl") not in ("card", "cta"):
        # bo dem da gach ve 0 thi canh sau giu so moi
        for r in hud:
            if "reset" in r: r["n"] = r["reset"]["to"]; r.pop("reset", None)
            if "from" in r: r["n"] = r.pop("to"); r.pop("from", None)
    shots.append(sh); t += d
if music: music[-1]["end"] = round(t, 3)
else: music = [{"start": 0, "end": round(t, 3), "bed": "sad"}]
dur = round(t + 0.6, 3); shots[-1]["end"] = dur
cfg_p = os.path.join(P, "config.json"); cfg = read_json(cfg_p, {}) or {}
if meta.get("accent"): cfg["accent"] = meta["accent"].lower()
if meta.get("title") and not cfg.get("title"): cfg["title"] = meta["title"]
cfg["duration"] = dur; cfg.setdefault("pack", "dem"); write_json(cfg_p, cfg)
write_json(out, {"title": cfg.get("title", meta.get("title", "")), "duration": dur, "shots": shots, "music": music})
print(f"Xong: {len(shots)} canh, dai {dur:.1f} giay ({dur/60:.1f} phut), {len(music)} doan nhac -> {out}")
for w in warn: print("CANH BAO:", w)
