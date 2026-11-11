"""doctor.py — kiem tra may co du cong cu de dung video. Them --install de tu cai phan con thieu."""
import importlib.util, json, os, platform, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OS = platform.system()
fix_cmds, ok_all = [], True
def ok(name, cond, detail="", fix=None):
    global ok_all
    print(f"[{'OK' if cond else 'THIEU'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        ok_all = False
        if fix: fix_cmds.append(fix)
def ver(cmd):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip().splitlines()[0]
    except Exception: return ""
ok("Python >= 3.9", sys.version_info >= (3, 9), sys.version.split()[0])
for m in ("numpy", "scipy", "soundfile"):
    ok(f"Python: {m}", importlib.util.find_spec(m) is not None, fix=f'"{sys.executable}" -m pip install numpy scipy soundfile' + (" --break-system-packages" if OS == "Linux" else ""))
ok("ffmpeg", shutil.which("ffmpeg") is not None, ver(["ffmpeg", "-version"])[:40], {"Windows": "winget install --id Gyan.FFmpeg -e", "Darwin": "brew install ffmpeg"}.get(OS, "sudo apt-get install -y ffmpeg"))
ok("ffprobe", shutil.which("ffprobe") is not None)
nv = ver(["node", "--version"]); ok("Node.js >= 18", nv.startswith("v") and int(nv[1:].split(".")[0]) >= 18, nv, {"Windows": "winget install OpenJS.NodeJS.LTS", "Darwin": "brew install node"}.get(OS, "cai Node 20 LTS"))
need = json.load(open(os.path.join(ROOT, "package.json"), encoding="utf-8")).get("dependencies", {})
miss = [k for k in need if not os.path.isdir(os.path.join(ROOT, "node_modules", *k.split("/")))]
ok("Goi Node (playwright, font, ban do, 3D)", not miss, ("thieu: " + ", ".join(miss)) if miss else f"{len(need)} goi", fix="npm install")
packs = sorted(d for d in os.listdir(os.path.join(ROOT, "packs"))) if os.path.isdir(os.path.join(ROOT, "packs")) else []
print(f"[--] Bo phong cach co san: {', '.join(packs) or 'khong co'} (+ nguoi que What If)")
exe = ""
try: exe = subprocess.run(["node", "-e", "import('playwright').then(p=>console.log(p.chromium.executablePath()))"], capture_output=True, text=True, cwd=ROOT, timeout=60).stdout.strip()
except Exception: pass
ok("Chromium chay ngam", bool(exe) and os.path.exists(exe) or bool(os.environ.get("PLAYWRIGHT_BROWSERS_PATH")), exe[-60:], "npx playwright install chromium")
sfx = os.path.join(ROOT, "audio", "sfx"); mus = os.path.join(ROOT, "audio", "music")
ok("Thu vien SFX + nhac", os.path.isdir(sfx) and len(os.listdir(sfx)) >= 30 and os.path.isdir(mus) and len(os.listdir(mus)) >= 6, fix=f'"{sys.executable}" audio/build_audio.py')
# pack co audio.py rieng (vd dem: nhac sad/dark/rise, SFX bao thuc, kinh vo...) phai da tao xong
for pk in packs:
    if os.path.exists(os.path.join(ROOT, "packs", pk, "audio.py")):
        have = os.path.isdir(mus) and any(f.startswith({"dem": "bed_sad_", "squire": "bed_medieval_"}[pk]) for f in os.listdir(mus)) if pk in ("dem", "squire") else True
        ok(f"Nhac + SFX rieng cua pack {pk}", have, fix=f'"{sys.executable}" audio/build_audio.py')
if "--install" in sys.argv and fix_cmds:
    for c in dict.fromkeys(fix_cmds):
        print("\n>>>", c); subprocess.run(c, shell=True, cwd=ROOT)
elif fix_cmds:
    print("\nCach sua:"); [print("  " + c) for c in dict.fromkeys(fix_cmds)]
print("\nSAN SANG" if ok_all else "\nChua du — chay lai voi --install hoac lam theo cach sua o tren.")
