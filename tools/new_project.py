"""new_project.py — tao thu muc du an video moi.
  python tools/new_project.py --name never-forget --title "What If You Never Forgot Anything?" [--aspect 16:9|9:16] [--resolution 1080p] [--style dusk] [--captions] [--pack doodle --lang vi]
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import write_json
ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True); ap.add_argument("--title", default="")
ap.add_argument("--aspect", default="16:9"); ap.add_argument("--resolution", default="1080p")
ap.add_argument("--style", default="dusk"); ap.add_argument("--captions", action="store_true")
ap.add_argument("--pack", default="", help="bo phong cach ngach (vd doodle); de trong = nguoi que What If")
ap.add_argument("--lang", default="en")
a = ap.parse_args()
root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects", a.name)
for d in ["input", "anh", "timeline", "story", "scenes/sets", "scenes/shots", "build", "out"]: os.makedirs(os.path.join(root, d), exist_ok=True)
cfg = os.path.join(root, "config.json")
if not os.path.exists(cfg):
    write_json(cfg, {"title": a.title or a.name, "aspect": a.aspect, "resolution": a.resolution, "fps": 24, "style": a.style,
                     "captions": bool(a.captions or a.aspect == "9:16"), "bars": None, "fadeIn": 0.4, "fadeOut": 0.8,
                     "pack": a.pack, "lang": a.lang, "music": {"enabled": True, "gainDb": -15}, "sfx": {"enabled": True, "gainDb": -4}, "loudness": -14})
print("Du an:", root)
