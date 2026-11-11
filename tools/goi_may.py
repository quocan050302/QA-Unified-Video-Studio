"""goi_may.py — dong goi mot du an de dung BAN CUOI bang card do hoa tren may Windows cua nguoi dung.

  python tools/goi_may.py --project projects/<slug> --out <thu muc xuat> [--title "<tieu de>"] [--remix] [--part-mb 25]

Lam gi:
  1. Tron am thanh tren may nay (tools/mix.py --no-video) -> build/mix.m4a (AAC 192k, da chuan -14 LUFS).
  2. Gom bo dung toi thieu (engine, tools, render.mjs, player.html, package.json, chi cac pack du an can)
     + du an (story, timeline khong kem file am thanh, dem, scenes, anh..., build/mix.m4a) thanh cac file
     <slug>-may-1.zip, <slug>-may-2.zip... moi file <= --part-mb MB (de chep ve may nguoi dung, gioi han 30 MB/file).
  3. Viet DUNG-VIDEO-<SLUG>.bat + _ghep-<slug>.ps1: bam dup la tu cai Node/ffmpeg (winget) neu thieu, giai nen vao
     %LOCALAPPDATA%\\h2-2d-studio-gpu, npm install, dung hinh bang Edge/Chrome + GPU, ghep tieng -> "<tieu de>.mp4"
     ngay canh file .bat. Tien do ghi vao render-log.txt canh file .bat (Claude doc duoc qua device_stage_files).
Chep TAT CA file trong --out vao thu muc du an tren may nguoi dung (device_commit_files), roi bao nguoi dung bam dup file .bat.
"""
import argparse, json, os, re, shutil, subprocess, sys, zipfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--title", default=""); ap.add_argument("--remix", action="store_true")
ap.add_argument("--part-mb", type=float, default=25)
a = ap.parse_args()
P = os.path.abspath(a.project); slug = os.path.basename(P.rstrip("/\\"))
OUT = os.path.abspath(a.out); os.makedirs(OUT, exist_ok=True)
cfg = json.load(open(os.path.join(P, "config.json"), encoding="utf-8"))
title = a.title or cfg.get("title") or slug
safe_title = re.sub(r'[<>:"/\\|?*%^&!\x00-\x1f]', "", title.replace("&", "and")).strip().rstrip(".") or slug

# ---------- 1. am thanh
B = os.path.join(P, "build"); os.makedirs(B, exist_ok=True)
wav, m4a = os.path.join(B, "mix.wav"), os.path.join(B, "mix.m4a")
if a.remix or not os.path.exists(wav):
    subprocess.run([sys.executable, os.path.join(KIT, "tools", "mix.py"), "--project", P, "--no-video"], check=True)
# bitrate am thanh: toi da 192k, ha xuong de file m4a <= ~27 MB (gioi han chep 30 MB/file) voi video dai
try: dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav], capture_output=True, text=True).stdout.strip())
except Exception: dur = 0
kbps = int(min(192, max(96, 27e6 * 8 / 1000 / dur))) if dur > 0 else 192
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "aac", "-b:a", f"{kbps}k", m4a], check=True)

# ---------- 2. chon file
def walk(base, skip_dirs=(), skip_ext=()):
    for r, d, fs in os.walk(base):
        d[:] = [x for x in d if x not in ("__pycache__", "node_modules") + tuple(skip_dirs)]
        for f in fs:
            if not f.lower().endswith(tuple(skip_ext)): yield os.path.join(r, f)

packs, todo = set(), []
if cfg.get("pack"): todo.append(cfg["pack"])
for f in walk(os.path.join(P, "scenes")) if os.path.isdir(os.path.join(P, "scenes")) else []:
    if f.endswith(".js"): todo += re.findall(r"/packs/([A-Za-z0-9_-]+)/", open(f, encoding="utf-8", errors="ignore").read())
while todo:
    k = todo.pop()
    if k in packs or not os.path.isdir(os.path.join(KIT, "packs", k)): continue
    packs.add(k)
    for f in walk(os.path.join(KIT, "packs", k)):
        if f.endswith((".js", ".mjs")):
            s = open(f, encoding="utf-8", errors="ignore").read()
            todo += re.findall(r"\.\./([A-Za-z0-9_-]+)/", s) + re.findall(r"/packs/([A-Za-z0-9_-]+)/", s)

items = []   # (duong dan that, ten trong zip)
for top in ["engine", "tools"]:
    for f in walk(os.path.join(KIT, top)): items.append((f, os.path.relpath(f, KIT)))
for f in ["render.mjs", "player.html", "package.json", "package-lock.json"]:
    if os.path.exists(os.path.join(KIT, f)): items.append((os.path.join(KIT, f), f))
has_dem = os.path.exists(os.path.join(P, "dem", "index.json"))
for k in sorted(packs):
    # pack dia hinh (chikei): du an da co luoi do cao rieng trong dem/ -> bo du lieu goc ~37 MB cua pack
    skip = ("dem",) if has_dem and os.path.exists(os.path.join(KIT, "packs", k, "dia_hinh.py")) else ()
    for f in walk(os.path.join(KIT, "packs", k), skip_dirs=skip): items.append((f, os.path.relpath(f, KIT)))
AUD = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac")
for name in sorted(os.listdir(P)):
    p = os.path.join(P, name)
    if name in ("build", "out", "input") or name == "config.json": continue
    if os.path.isdir(p):
        for f in walk(p, skip_ext=AUD if name == "timeline" else ()): items.append((f, os.path.relpath(f, KIT)))
    else: items.append((p, os.path.relpath(p, KIT)))
items.append((m4a, os.path.relpath(m4a, KIT)))
c2 = dict(cfg); c2.pop("aa", None); c2.pop("gl", None)   # may co card: bat khu rang cua, de Chromium tu chon GPU
cfg_name = os.path.relpath(os.path.join(P, "config.json"), KIT)

# ---------- 3. chia phan <= part-mb
for f in os.listdir(OUT):
    if re.match(rf"{re.escape(slug)}-may-\d+\.zip$", f): os.remove(os.path.join(OUT, f))
lim = a.part_mb * 1e6; parts = []; cur = None; cur_sz = 0
def new_part():
    global cur, cur_sz
    if cur: cur.close()
    n = len(parts) + 1; path = os.path.join(OUT, f"{slug}-may-{n}.zip"); parts.append(path)
    cur = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED); cur_sz = 0
new_part(); cur.writestr(cfg_name.replace(os.sep, "/"), json.dumps(c2, ensure_ascii=False, indent=1))
for src, arc in items:
    sz = os.path.getsize(src)
    if sz > 29e6: sys.exit(f"File qua lon de chep ({sz/1e6:.0f} MB): {src}")
    if cur_sz + sz > lim and cur_sz > 0: new_part()   # file lon hon part-mb (<= 29 MB) nam rieng 1 phan
    cur.write(src, arc.replace(os.sep, "/")); cur_sz += sz
cur.close()

# ---------- 4. file chay tren Windows
S = slug.upper()
ps = f"""$ErrorActionPreference = 'Stop'
$b = Join-Path $env:LOCALAPPDATA 'h2-2d-studio-gpu\\projects\\{slug}\\build'
$out = Join-Path $PSScriptRoot '{safe_title.replace("'", "''")}.mp4'
& ffmpeg -v error -y -i (Join-Path $b 'video_silent.mp4') -i (Join-Path $b 'mix.m4a') -map 0:v -map 1:a -c copy -shortest -movflags +faststart $out
Write-Host ('Video: ' + $out)
"""
open(os.path.join(OUT, f"_ghep-{slug}.ps1"), "w", encoding="utf-8-sig", newline="\r\n").write(ps)
bat = f"""@echo off
chcp 65001 >nul
setlocal
title Dung video {slug} bang card do hoa
set "HERE=%~dp0"
set "STUDIO=%LOCALAPPDATA%\\h2-2d-studio-gpu"
set "LOG=%HERE%render-log.txt"
set "PATH=%PATH%;C:\\Program Files\\nodejs;%LOCALAPPDATA%\\Microsoft\\WinGet\\Links"
echo ================================================================
echo   DUNG VIDEO {S} - ban cuoi bang card do hoa tren may cua ban
echo   Dung tat cua so nay cho den khi hien chu XONG.
echo ================================================================
echo.
echo [1/5] Kiem tra Node.js ...
where node >nul 2>nul
if %errorlevel%==0 goto has_node
echo     Chua co Node.js - dang cai (can mang) ...
winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
:has_node
node -v
echo [2/5] Kiem tra ffmpeg ...
where ffmpeg >nul 2>nul
if %errorlevel%==0 goto ff_ok
echo     Chua co ffmpeg - dang cai ...
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
where ffmpeg >nul 2>nul
if %errorlevel%==0 goto ff_ok
echo     Chua tim thay ffmpeg sau khi cai. Dong cua so nay roi bam dup file .bat lan nua.
pause
exit /b 1
:ff_ok
echo [3/5] Giai nen bo dung ...
if not exist "%STUDIO%" mkdir "%STUDIO%"
powershell -NoProfile -Command "Get-ChildItem -LiteralPath $env:HERE -Filter '{slug}-may-*.zip' | Sort-Object Name | ForEach-Object {{ Expand-Archive -Force -LiteralPath $_.FullName -DestinationPath $env:STUDIO }}"
cd /d "%STUDIO%"
echo [4/5] Cai thu vien (lan dau 1-3 phut, cac lan sau vai giay) ...
call npm install --no-audit --no-fund --loglevel=error
if exist "projects\\{slug}\\build\\video_silent.mp4" del /q "projects\\{slug}\\build\\video_silent.mp4"
echo [5/5] Dang dung hinh ... (tien do hien o cua so thu hai)
echo Bat dau: %date% %time% > "%LOG%"
start "Tien do dung video" powershell -NoExit -Command "Get-Content -LiteralPath $env:LOG -Wait"
node render.mjs --project projects\\{slug} >> "%LOG%" 2>&1
if not exist "projects\\{slug}\\build\\video_silent.mp4" goto fail
echo Ghep tieng ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%_ghep-{slug}.ps1" >> "%LOG%" 2>&1
if errorlevel 1 goto fail
echo Xong: %date% %time% >> "%LOG%"
echo XONG >> "%LOG%"
echo.
echo ================================================================
echo   XONG! Video nam ngay trong thu muc nay.
echo ================================================================
pause
exit /b 0
:fail
echo LOI >> "%LOG%"
echo.
echo Co loi. Bao lai cho Claude (Claude doc duoc file render-log.txt).
pause
exit /b 1
"""
open(os.path.join(OUT, f"DUNG-VIDEO-{S}.bat"), "w", encoding="utf-8", newline="\r\n").write(bat)
print("Pack:", ", ".join(sorted(packs)) or "(khong)")
for f in sorted(os.listdir(OUT)): print(f"  {f}  {os.path.getsize(os.path.join(OUT, f))/1e6:.1f} MB")
print(f"Xong. Chep tat ca file trong {OUT} vao thu muc du an tren may nguoi dung, roi bao bam dup DUNG-VIDEO-{S}.bat")
