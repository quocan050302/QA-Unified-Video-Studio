"""validator.py — Bo kiem dinh tien trinh (Preflight Validator) dung chung cho CLI, app.py va test.
  python tools/validator.py --project projects/<ten> [--json] [--stage <preflight|render|mix>]
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_json

PACK_TEMPLATES = {
    "squire": {
        "scene", "army", "close", "top", "map", "plan", "board",
        "xray", "frame", "item", "split", "title", "black", "ai"
    },
    "dem": {
        "scene", "phone", "clock", "calendar", "note", "face",
        "black", "card", "cta"
    },
    "doodle": {
        "comp", "host", "bighead", "ai", "map", "compare", "scale",
        "measure", "list", "note", "counter", "timeline", "chart",
        "icons", "title", "branch", "endcard"
    }
}

def validate_project(project_dir: str, stage: str = "preflight") -> dict:
    P = Path(project_dir).resolve()
    report = {
        "project": P.name,
        "path": str(P),
        "status": "PASS",
        "stage": stage,
        "shots_total": 0,
        "shots_renderable": 0,
        "missing_ids": [],
        "missing_templates": [],
        "missing_assets": [],
        "import_errors": [],
        "runtime_errors": [],
        "timeline_errors": [],
        "fatal_errors": [],
        "warnings": []
    }

    # 1. Kiem tra thu muc va config.json
    if not P.is_dir():
        report["fatal_errors"].append(f"Thu muc du an khong ton tai: {P}")
        report["status"] = "BLOCKED"
        return report

    cfg_file = P / "config.json"
    if not cfg_file.is_file():
        report["fatal_errors"].append("Thieu config.json")
        report["status"] = "BLOCKED"
        return report

    try:
        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    except Exception as e:
        report["fatal_errors"].append(f"config.json loi cu phap: {e}")
        report["status"] = "BLOCKED"
        return report

    pack = cfg.get("pack", "")
    if not pack:
        report["fatal_errors"].append("config.json thieu truong 'pack'")
        report["status"] = "BLOCKED"
        return report

    aspect = cfg.get("aspect", "16:9")
    if aspect not in ("16:9", "9:16"):
        report["fatal_errors"].append(f"config.json aspect khong hop le: {aspect}")
        report["status"] = "BLOCKED"
        return report

    resolution = cfg.get("resolution", "1080p")
    if resolution not in ("720p", "1080p", "1440p", "2160p"):
        report["fatal_errors"].append(f"config.json resolution khong hop le: {resolution}")
        report["status"] = "BLOCKED"
        return report
    
    known_templates = PACK_TEMPLATES.get(pack, set())
    is_2d_only = cfg.get("render_mode") == "canvas2d_only"

    # 2. Kiem tra story/shots.json
    shots_file = P / "story" / "shots.json"
    if not shots_file.is_file():
        report["fatal_errors"].append("Thieu story/shots.json (chua tao storyboard)")
        report["status"] = "BLOCKED"
        return report

    try:
        story = json.loads(shots_file.read_text(encoding="utf-8"))
    except Exception as e:
        report["fatal_errors"].append(f"story/shots.json loi cu phap: {e}")
        report["status"] = "BLOCKED"
        return report

    shots = story.get("shots", [])
    report["shots_total"] = len(shots)

    if not isinstance(shots, list) or len(shots) == 0:
        report["fatal_errors"].append("story/shots.json khong co shot nao (0 shots)")
        report["status"] = "BLOCKED"
        return report

    duration = story.get("duration", 0)
    if not isinstance(duration, (int, float)) or duration <= 0:
        # Fallback to last shot end
        last_end = shots[-1].get("end") if shots else 0
        if not last_end or last_end <= 0:
            report["fatal_errors"].append(f"Do dai story/shots.json khong hop le (duration={duration})")
            report["status"] = "BLOCKED"

    # Tap hop anh hien co trong <proj>/anh/
    anh_dir = P / "anh"
    existing_assets = set()
    if anh_dir.is_dir():
        for f in anh_dir.iterdir():
            if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                existing_assets.add(f.stem)

    # Tap hop custom scenes trong scenes/shots/*.js
    scenes_dir = P / "scenes" / "shots"
    custom_scenes = set()
    if scenes_dir.is_dir():
        for f in scenes_dir.iterdir():
            if f.is_file() and f.suffix == '.js':
                custom_scenes.add(f.stem)
                try:
                    for m in re.finditer(r"""registerShot\s*\(\s*['"]([^'"]+)['"]""", f.read_text(encoding="utf-8", errors="ignore")):
                        custom_scenes.add(m.group(1))
                except OSError:
                    pass

    seen_ids = set()
    prev_end = 0.0

    for i, s in enumerate(shots):
        sid = s.get("id")
        if not sid or not isinstance(sid, str):
            report["fatal_errors"].append(f"Shot o vi tri {i} khong co 'id' hop le")
            continue
        
        if sid in seen_ids:
            report["fatal_errors"].append(f"Trung lap shot ID: '{sid}'")
        seen_ids.add(sid)

        st = s.get("start")
        en = s.get("end")
        if st is None or en is None or not isinstance(st, (int, float)) or not isinstance(en, (int, float)):
            report["timeline_errors"].append(f"Shot '{sid}' co moc thoi gian khong hop le (start={st}, end={en})")
        elif en <= st:
            report["timeline_errors"].append(f"Shot '{sid}' co end <= start ({st} -> {en})")
        elif i > 0 and st < prev_end - 0.5:
            report["warnings"].append(f"Shot '{sid}' de len shot truoc do qua 0.5s")
        prev_end = en if en is not None else prev_end

        # Kiem tra dinh nghia do hoa (getShot qua custom_scenes hoac getTemplate qua tpl)
        has_custom = sid in custom_scenes
        tpl = s.get("tpl")
        has_tpl = tpl in known_templates

        if not has_custom and not has_tpl:
            report["missing_ids"].append(sid)
            if tpl and tpl not in known_templates:
                report["missing_templates"].append(f"{sid}: template '{tpl}' chua dang ky trong pack '{pack}'")
        else:
            report["shots_renderable"] += 1

        # Kiem tra tham chieu anh can thiet
        args = s.get("args") or {}
        img_refs = []
        for key in ("img", "bgImg"):
            val = args.get(key)
            if val and isinstance(val, str): img_refs.append(val)
        for key in ("imgs", "layers", "items"):
            for item in args.get(key, []):
                if isinstance(item, str): img_refs.append(item)
                elif isinstance(item, dict) and item.get("img"): img_refs.append(item["img"])

        for ref in img_refs:
            if ref not in existing_assets:
                report["missing_assets"].append(f"Shot {sid} can anh '{ref}' nhung khong tim thay trong anh/")

        if is_2d_only and (s.get("kind") == "3d" or s.get("tpl") == "3d" or args.get("kind") == "3d"):
            report["fatal_errors"].append(f"KH03_2D_ONLY_VIOLATION: Shot '{sid}' khai bao 3D trong che do render_mode=canvas2d_only")

    if is_2d_only and (P / "scenes").is_dir():
        for js_f in sorted((P / "scenes").rglob("*.js")):
            try:
                js_txt = js_f.read_text(encoding="utf-8", errors="ignore")
                if re.search(r"""kind\s*:\s*['"]3d['"]|three3d\.js|from\s+['"]three['"]|import\s*\(\s*['"][^'"]*three3d""", js_txt):
                    rel_js = js_f.relative_to(P).as_posix()
                    report["fatal_errors"].append(f"KH03_2D_ONLY_VIOLATION: File '{rel_js}' chua dinh nghia 3D / Three.js trong che do canvas2d_only")
            except OSError:
                pass

    # 3. Kiem tra am thanh tuy theo pack va stage
    if pack == "squire":
        voice_file = P / "timeline" / "voice.wav"
        if stage in ("mix", "final") and not voice_file.is_file():
            report["timeline_errors"].append("Pack squire can timeline/voice.wav de mix am thanh")
        elif voice_file.is_file():
            try:
                # Kiem tra voice duration vs story duration
                sz = voice_file.stat().st_size
                if sz < 1000:
                    report["timeline_errors"].append(f"timeline/voice.wav qua nho ({sz} bytes)")
            except Exception:
                pass

    # 4. Kiem tra stale build neu o stage mix
    if stage == "mix":
        video_silent = P / "build" / "video_silent.mp4"
        if not video_silent.is_file():
            report["fatal_errors"].append("Chua co build/video_silent.mp4 de mix (can render video truoc)")
        else:
            # So sanh mtime
            v_mtime = video_silent.stat().st_mtime
            s_mtime = shots_file.stat().st_mtime
            if v_mtime < s_mtime - 2:
                report["fatal_errors"].append(
                    "build/video_silent.mp4 cu hon story/shots.json (storyboard da bi sua doi sau khi render). "
                    "Vui long render lai truoc khi mix."
                )

    # 5. Opt-in validation for KH-03.0.R1 script_beat_director_v1 editorial contracts
    if cfg.get("editorial_mode") == "script_beat_director_v1":
        sp_file = P / "story" / "shot_plan.json"
        map_file = P / "story" / "shot_to_line_map.json"
        if not sp_file.is_file():
            report["fatal_errors"].append("editorial_mode='script_beat_director_v1' thieu story/shot_plan.json")
        else:
            try:
                sp = json.loads(sp_file.read_text(encoding="utf-8"))
                sp_shots = sp.get("shots", [])
                exp_frames = int(sp.get("total_frames", 720))
                if not sp_shots:
                    report["fatal_errors"].append("story/shot_plan.json khong co shots")
                else:
                    cursor_f = 0
                    for s_item in sp_shots:
                        fs, fe = int(s_item.get("frame_start", -1)), int(s_item.get("frame_end", -1))
                        if fs != cursor_f or fe < fs:
                            report["timeline_errors"].append(
                                f"shot_plan frame continuity gap/overlap tai {s_item.get('id')}: {fs}..{fe} (cho doi {cursor_f})"
                            )
                            break
                        cursor_f = fe + 1
                    if cursor_f != exp_frames:
                        report["timeline_errors"].append(
                            f"shot_plan khong phu du {exp_frames} frames (ket thuc tai {cursor_f})"
                        )
            except Exception as exc:
                report["fatal_errors"].append(f"Loi doc story/shot_plan.json: {exc}")

        if not map_file.is_file():
            report["fatal_errors"].append("editorial_mode='script_beat_director_v1' thieu story/shot_to_line_map.json")
        else:
            try:
                cw = json.loads(map_file.read_text(encoding="utf-8"))
                sm = cw.get("summary", {})
                if float(sm.get("word_coverage_ratio", 0.0)) < 0.999:
                    report["timeline_errors"].append(
                        f"shot_to_line_map bo sot tu (coverage={sm.get('word_coverage_ratio')})"
                    )
            except Exception as exc:
                report["fatal_errors"].append(f"Loi doc story/shot_to_line_map.json: {exc}")

    # 6. Opt-in fail-closed validation for KH-03.0.R2 roman_action_director_v2 projects
    elif cfg.get("editorial_mode") == "roman_action_director_v2":
        from kh03_action_registry import validate_action_bindings
        from kh03_script_beat_director import parse_js_renderer_handlers

        req_r2_files = [
            "story/shot_plan.json",
            "story/action_graph.json",
            "story/action_bindings.json",
            "story/scene_manifest.json",
            "story/shot_to_line_map.json",
        ]
        for rel_f in req_r2_files:
            if not (P / rel_f).is_file():
                report["fatal_errors"].append(f"editorial_mode='roman_action_director_v2' thieu {rel_f}")

        if (P / "story" / "shot_plan.json").is_file() and (P / "story" / "scene_manifest.json").is_file():
            try:
                sp = read_json(P / "story" / "shot_plan.json")
                sm_manifest = read_json(P / "story" / "scene_manifest.json")
                if sp.get("render_mode") != "canvas2d_only":
                    report["fatal_errors"].append("R2 bat buoc render_mode='canvas2d_only'")
                sp_shots = sp.get("shots", [])
                exp_frames = int(sp.get("total_frames", 720))
                cursor_f = 0
                for s_item in sp_shots:
                    fs, fe = int(s_item.get("frame_start", -1)), int(s_item.get("frame_end", -1))
                    if fs != cursor_f or fe < fs:
                        report["timeline_errors"].append(
                            f"shot_plan frame continuity gap/overlap tai {s_item.get('id')}: {fs}..{fe} (cho doi {cursor_f})"
                        )
                        break
                    cursor_f = fe + 1
                if sp_shots and cursor_f != exp_frames:
                    report["timeline_errors"].append(
                        f"shot_plan khong phu du {exp_frames} frames (ket thuc tai {cursor_f})"
                    )
                bind_res = validate_action_bindings(
                    sp,
                    asset_manifest=sm_manifest,
                    renderer_registry=parse_js_renderer_handlers() or None,
                )
                if not bind_res.get("valid"):
                    for err in bind_res.get("errors", []):
                        report["fatal_errors"].append(
                            f"R2 ActionRegistry fail-closed [{err.get('error_code')}]: {err.get('message', err)}"
                        )
            except Exception as exc:
                report["fatal_errors"].append(f"Loi R2 validator: {exc}")

    # Danh gia trang thai chung
    if (report["fatal_errors"] or report["missing_ids"] or report["missing_templates"] or
        report["missing_assets"] or report["timeline_errors"] or report["import_errors"]):
        report["status"] = "BLOCKED"
    else:
        report["status"] = "PASS"

    return report

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Kiem dinh chat luong du an (Preflight Validator)")
    ap.add_argument("project_pos", nargs="?", default=None, help="Duong dan du an (positional)")
    ap.add_argument("--project", default=None, help="Duong dan du an")
    ap.add_argument("--stage", default="preflight", choices=["preflight", "render", "mix", "final"])
    ap.add_argument("--json", action="store_true", help="Xuat ket qua JSON")
    args = ap.parse_args()
    proj = args.project or args.project_pos
    if not proj:
        ap.error("the following arguments are required: --project or project")

    rep = validate_project(proj, stage=args.stage)
    
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        status_sym = "[PASS]" if rep["status"] == "PASS" else "[BLOCKED]"
        print(f"{status_sym} Du an: {rep['project']} | Trinh trang: {rep['status']}")
        print(f"  Shots: {rep['shots_renderable']}/{rep['shots_total']} hop le")
        if rep["missing_ids"]:
            print(f"  THIEU {len(rep['missing_ids'])} shot chua co hinh anh: {', '.join(rep['missing_ids'][:20])}")
        if rep["missing_templates"]:
            print(f"  Template chua dang ky: {', '.join(rep['missing_templates'][:10])}")
        if rep["missing_assets"]:
            print(f"  Anh AI thieu: {', '.join(rep['missing_assets'][:10])}")
        if rep["timeline_errors"]:
            print("  Loi timeline:")
            for e in rep["timeline_errors"][:5]: print(f"    - {e}")
        if rep["fatal_errors"]:
            print("  Loi nghiem trong:")
            for e in rep["fatal_errors"][:5]: print(f"    - {e}")
        if rep["warnings"]:
            print("  Canh bao:")
            for w in rep["warnings"][:5]: print(f"    - {w}")

    sys.exit(0 if rep["status"] == "PASS" else 1)
