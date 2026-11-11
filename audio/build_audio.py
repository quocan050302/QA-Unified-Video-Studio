"""build_audio.py — tao thu vien SFX va nen nhac bang code (chay 1 lan sau khi cai). Can numpy, scipy, soundfile.
Sau synth.py + music.py, chay them packs/<ten>/audio.py cua tung bo phong cach (neu co) de tao nhac/SFX rieng cua ngach."""
import glob, os, subprocess, sys
D = os.path.dirname(os.path.abspath(__file__))
extra = sorted(glob.glob(os.path.join(os.path.dirname(D), "packs", "*", "audio.py")))
for f in [os.path.join(D, "synth.py"), os.path.join(D, "music.py")] + extra:
    print(">>", os.path.relpath(f, os.path.dirname(D))); r = subprocess.run([sys.executable, f], cwd=D)
    if r.returncode: sys.exit(f"Loi khi chay {f}")
print("Xong: audio/sfx va audio/music")
