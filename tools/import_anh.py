"""import_anh.py — nap danh sach anh AI (file 04-ANH-AI) va chep anh nguoi dung da tao vao <du an>/anh/.
  python tools/import_anh.py --project projects/<ten> --list "<04-ANH-AI-<slug>.txt>" [--dir "<thu muc anh da tao>"]
File 04 gom cac khoi:
  ### A001 | V003 | <cau neo trong loi doc>
  <prompt tieng Anh>
Anh trong --dir dat ten bat dau bang ma anh (A001.png, a001.jpg, "A001 (1).png", "A001_xyz.webp" deu nhan). Thieu anh nao thi bao.
Ghi ra <du an>/input/anh-ai.json de draft_shots.py tu gan anh vao dung shot.
"""
import argparse, glob, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import write_json
ap = argparse.ArgumentParser(); ap.add_argument("--project", required=True); ap.add_argument("--list", required=True); ap.add_argument("--dir", default="")
a = ap.parse_args()
txt = open(a.list, encoding="utf-8-sig").read()
items = {}
for m in re.finditer(r"^#{2,3}\s*([A-Z]\d{3})\s*\|\s*(V\d+)\s*\|\s*(.*?)\s*$\n(.*?)(?=^#{2,3}\s*[A-Z]\d{3}|\Z)", txt, re.M | re.S):
    items[m.group(1)] = {"block": m.group(2), "text": m.group(3).strip().strip('"“”'), "prompt": m.group(4).strip()}
if not items: sys.exit("Khong doc duoc anh nao. Dong dau moi anh phai dang: ### A001 | V003 | <cau neo>")
write_json(os.path.join(a.project, "input", "anh-ai.json"), items)
os.makedirs(os.path.join(a.project, "anh"), exist_ok=True)
got = set()
if a.dir:
    for f in sorted(glob.glob(os.path.join(a.dir, "*"))):
        if not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")): continue
        m = re.match(r"(?i)\s*([a-z]\d{3})", os.path.basename(f))
        if not m: continue
        aid = m.group(1).upper(); ext = os.path.splitext(f)[1].lower()
        if aid in got: continue
        shutil.copyfile(f, os.path.join(a.project, "anh", aid + ext)); got.add(aid)
have = {os.path.splitext(x)[0].upper() for x in os.listdir(os.path.join(a.project, "anh"))}
miss = [k for k in items if k not in have]
print(f"{len(items)} anh trong danh sach, da co {len(items) - len(miss)} anh trong {a.project}/anh/.")
if miss: print("Chua co anh:", ", ".join(miss))
