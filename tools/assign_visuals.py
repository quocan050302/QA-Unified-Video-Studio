"""assign_visuals.py — Tu dong phan tich kich ban va gan hinh anh hoat hinh (template + args)
cho storyboard cua pack squire, phu hop chinh xac voi noi dung loi thoai va hanh dong thuc te.
  python tools/assign_visuals.py --project projects/<ten> [--force] [--upgrade-generated] [--shots s001,s002]
"""
import argparse, json, os, re, sys, shutil, time
from typing import List, Dict, Any, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_json, write_json
from visual_facts import extract_quantity_facts, is_anatomical_chest

SQUIRE_TEMPLATES = {
    "scene", "army", "close", "top", "map", "plan", "board",
    "xray", "frame", "item", "split", "title", "black"
}

CAST_PRESETS = {
    "knight15", "knight14", "knight13", "knight12", "whiteArmor",
    "frenchKnight", "frenchKnight2", "englishArcher", "crossbowman",
    "king", "henry", "peasant", "smith", "monk", "lady", "norman",
    "william", "saxon", "viking", "hastatus", "princeps", "triarius",
    "latin", "velites", "legionary", "senator", "consul", "greek",
    "spartan", "samurai", "ashigaru", "ronin", "officer"
}


def detect_theme(full_text: str) -> Dict[str, Any]:
    """Xac dinh chu de lich su chu dao tu toan bo van ban."""
    txt = full_text.lower()
    score_roman = len(re.findall(r"\b(roman|rome|legion|legionary|scutum|pilum|hastatus|princeps|centurion|caesar|latin|consul)\b", txt))
    score_greek = len(re.findall(r"\b(greek|greece|sparta|spartan|phalanx|hoplite|athens)\b", txt))
    score_samurai = len(re.findall(r"\b(samurai|katana|japan|japanese|ninja|shogun|ronin|ashigaru)\b", txt))
    score_knight = len(re.findall(r"\b(knight|castle|armor|armour|shield|sword|lance|horse|feudal|medieval|king|archer|arrow|bow|plate|mail)\b", txt))

    if score_roman > max(score_greek, score_samurai, score_knight, 0):
        return {
            "name": "roman",
            "hero": "hastatus",
            "alt": "princeps",
            "elite": "triarius",
            "enemy": "latin",
            "flag": "eagle",
            "weapon": "pilum",
            "shield": {"type": "scutum", "color": "#c9473a", "charge": "lightning", "chargeColor": "#f5d342"}
        }
    elif score_greek > max(score_samurai, score_knight, 0):
        return {
            "name": "greek",
            "hero": "spartan",
            "alt": "greek",
            "elite": "spartan",
            "enemy": "latin",
            "flag": "standard",
            "weapon": "spear",
            "shield": {"type": "round", "color": "#a8652d", "charge": "star", "chargeColor": "#c9473a"}
        }
    elif score_samurai > max(score_knight, 0):
        return {
            "name": "samurai",
            "hero": "samurai",
            "alt": "ashigaru",
            "elite": "samurai",
            "enemy": "ronin",
            "flag": "standard",
            "weapon": "katana",
            "shield": None
        }
    else:
        return {
            "name": "knight",
            "hero": "knight15",
            "alt": "knight14",
            "elite": "whiteArmor",
            "enemy": "frenchKnight2",
            "flag": "standard",
            "weapon": "sword",
            "shield": {"type": "heater", "color": "#c9473a", "charge": "lion", "chargeColor": "#f5d342"}
        }


def detect_actions_and_context(line: str, prev_line: str = "", next_line: str = "") -> Dict[str, Any]:
    """Phan tich hanh dong ngu nghia, phu dinh va boi canh khong gian tu loi thoai."""
    l_low = line.lower()
    combined = f"{prev_line} {line} {next_line}".lower()

    # Kiem tra phu dinh
    negation_pat = r"\b(could\s+not|can\s*not|never|nobody|no\s+one|did\s+not|without|refused\s+to|hardly|scarcely|couldn't|can't|didn't|won't|unable\s+to|failed\s+to|impossible\s+to)\s+([a-z\s]{1,20})\b"
    negated_phrases = [m.group(0) for m in re.finditer(negation_pat, l_low)]

    def is_verb_negated(v_pat: str) -> bool:
        for np in negated_phrases:
            if re.search(v_pat, np):
                return True
        return False

    # 1. Hanh dong Nam / Nga / Tren dat
    lie_pat = r"\b(lie|lying|lay|prone|supine|on\s+his\s+back|on\s+the\s+ground|in\s+the\s+mud|fallen|fall\s+down)\b"
    has_lie = bool(re.search(lie_pat, l_low)) and not is_verb_negated(lie_pat)

    # 2. Hanh dong Dung day / Hoi phuc
    rise_pat = r"\b(get\s+back\s+up|get\s+up|got\s+up|stand\s+up|stands\s+up|standing\s+up|rise|rising|recovers?|pushed?\s+(himself\s+)?up)\b"
    has_rise = bool(re.search(rise_pat, l_low)) and not is_verb_negated(rise_pat)

    # 3. Hanh dong Chay
    run_pat = r"\b(run|running|ran|sprint|sprinting|treadmill|jog|jogging)\b"
    has_run = bool(re.search(run_pat, l_low)) and not is_verb_negated(run_pat)

    # 4. Hanh dong Di bo / Hanh quan
    walk_pat = r"\b(walk|walking|marched|marching|advance|advancing|trudge|step|twenty\s+miles)\b"
    has_walk = bool(re.search(walk_pat, l_low)) and not is_verb_negated(walk_pat)

    # 5. Boi canh Phong thi nghiem (Lab) / May chay (Treadmill)
    lab_pat = r"\b(lab|laboratory|treadmill|researcher|experiment|testing|measured|speed\s+test|stamina\s+test)\b"
    has_lab = bool(re.search(lab_pat, l_low))

    # 6. Boi canh Bun lay (Mud) / Mua bao
    mud_pat = r"\b(mud|muddy|wet|rain|storm|puddle|trench|exhaustion)\b"
    has_mud = bool(re.search(mud_pat, l_low))
    if has_mud:
        has_lab = False

    # 7. Hanh dong phuc hop tuan tu: e.g. "lie down, stand up, then run"
    is_sequence = bool(has_lie and (has_rise or has_run)) or bool(
        re.search(r"\b(lie\s+down|lying).*(stand\s+up|get\s+up).*(run)\b", l_low)
    )

    return {
        "has_lie": has_lie,
        "has_rise": has_rise,
        "has_run": has_run,
        "has_walk": has_walk,
        "has_lab": has_lab,
        "has_mud": has_mud,
        "is_sequence": is_sequence,
        "negated_phrases": negated_phrases,
    }


def plan_visual_intent(
    sh: Dict[str, Any],
    idx: int,
    total: int,
    theme: Dict[str, Any],
    is_vertical: bool,
    prev_sh: Optional[Dict[str, Any]] = None,
    next_sh: Optional[Dict[str, Any]] = None,
    recent_tpls: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Hoach dinh y do hinh anh dua tren noi dung kieu hai buoc deterministic."""
    line = (sh.get("line") or "").strip()
    l_low = line.lower()
    dur = float(sh.get("end") or 0) - float(sh.get("start") or 0)
    if dur <= 0:
        dur = 3.0

    prev_line = (prev_sh.get("line") or "") if prev_sh else ""
    next_line = (next_sh.get("line") or "") if next_sh else ""
    actions = detect_actions_and_context(line, prev_line, next_line)
    facts = extract_quantity_facts(line)
    is_anat_chest = is_anatomical_chest(line)

    recent = recent_tpls or []

    # 1. Kiem tra so lieu / thong ke that su
    # Chi su dung template 'board' neu TRONG CAU THUC SU CO SO LIEU HOAC SO CHU DO LUONG
    is_stats_intent = len(facts) > 0 and any(f.get("unit") in ("mph", "%", "kg", "lbs", "s", "min", "hrs", "miles") for f in facts)

    # 2. Kiem tra Item / Vat pham / Vu khi (loai bo chest neu chest la nguc/ao giap)
    item_pat = r"\b(shield|sword|helmet|sandals?|weapon|spear|pilum|bow|arrows?|torch|anvil|coin|cart|barrel|skull)\b"
    has_item_token = bool(re.search(item_pat, l_low))
    if not is_anat_chest and re.search(r"\bchest\b", l_low):
        has_item_token = True

    # 3. Kiem tra Ban do
    is_map = bool(re.search(r"\b(map|territory|continent|europe|border|across the sea|marched across|geography)\b", l_low))

    # 4. Kiem tra So do chien thuat tren cao
    is_top = bool(re.search(r"\b(formation|flank|behind them|surround|tactics?|positions?|layout|camp|fort)\b", l_low))

    # 5. Kiem tra Doan quan hanh quan / Dong nguoi
    is_army = bool(re.search(r"\b(army|soldiers?|legion|troops?|hundreds|thousands?|men in line|host|ranks)\b", l_low))

    # 6. Kiem tra Can mat (Cau hoi / Cam xuc / Quan sat giap)
    is_close = bool("?" in line or
                    re.search(r"\b(who|why|how|wonder|strange|secret|truth is|lead researcher|paying for)\b", l_low) or
                    is_anat_chest)

    # 7. Kiem tra Split (So sanh / Hai mat)
    is_split = bool(re.search(r"\b(versus|vs|on the other hand|myth|instead of|two things|trade off|or leave off)\b", l_low))

    # Chon template voi quy tac chong lap hop ly
    chosen_tpl = "scene"
    if is_stats_intent and recent[-2:].count("board") == 0:
        chosen_tpl = "board"
    elif actions["is_sequence"] or actions["has_lie"] or actions["has_lab"] or actions["has_run"]:
        chosen_tpl = "scene" # Canh hanh dong thuc the
    elif is_split and recent[-2:].count("split") == 0:
        chosen_tpl = "split"
    elif is_map and recent[-2:].count("map") == 0:
        chosen_tpl = "map"
    elif is_top and recent[-2:].count("top") == 0:
        chosen_tpl = "top"
    elif has_item_token and not is_anat_chest and recent[-2:].count("item") == 0 and not is_close:
        chosen_tpl = "item"
    elif is_army and recent[-2:].count("army") == 0:
        chosen_tpl = "army"
    elif is_close and recent[-2:].count("close") == 0 and not actions["has_run"]:
        chosen_tpl = "close"
    else:
        chosen_tpl = "scene"

    # Xac dinh boi canh bg va thoi gian
    bg_choice = "field"
    time_choice = "day"
    if actions["has_lab"]:
        bg_choice = "lab"
        time_choice = "day"
    elif actions["has_mud"]:
        bg_choice = "mud"
        time_choice = "storm" if re.search(r"\b(rain|storm|exhaustion|dangerous)\b", l_low) else "dusk"
    elif re.search(r"\b(castle|hall|inside|room|bed|walls?)\b", l_low):
        bg_choice = "castle"
    elif re.search(r"\b(plain|field|mud)\b", l_low):
        bg_choice = "plain" if idx % 2 == 1 else "field"

    if re.search(r"\b(night|midnight|sleep|dark|moon)\b", l_low):
        time_choice = "night"
    elif re.search(r"\b(sunset|evening|dusk)\b", l_low):
        time_choice = "sunset"
    elif re.search(r"\b(morning|dawn|sunrise)\b", l_low):
        time_choice = "dawn"

    camera_moves = ["in", "right", "out", "left", "in", "still"]
    move_choice = camera_moves[idx % len(camera_moves)]

    # Xac dinh vai tro/muc dich ke chuyen (shot purpose for retention & pacing)
    purpose = "narrative"
    if idx == 0:
        purpose = "hook"
    elif actions["is_sequence"] or actions["has_lie"]:
        purpose = "hook" if idx < 2 else "demonstration"
    elif actions["has_lab"] and (actions["has_run"] or "treadmill" in l_low):
        purpose = "evidence"
    elif facts:
        purpose = "metric"
    elif re.search(r"\b(comment|tell\s+me|pick\s+one|question|what\s+do\s+you)\b", l_low):
        purpose = "cta"
    elif re.search(r"\b(joke|exhaustion|real|price|cost|centuries|trade)\b", l_low):
        purpose = "resolution"

    return {
        "idx": idx,
        "total": total,
        "purpose": purpose,
        "tpl": chosen_tpl,
        "line": line,
        "dur": dur,
        "bg": bg_choice,
        "time": time_choice,
        "move": move_choice,
        "actions": actions,
        "facts": facts,
        "is_anat_chest": is_anat_chest,
        "theme": theme,
        "speaker": sh.get("speaker", "NARRATOR"),
        "confidence": 0.95 if (actions["has_lab"] or actions["is_sequence"] or is_stats_intent) else 0.85
    }


def compile_visual_plan(plan: Dict[str, Any], is_vertical: bool) -> Tuple[str, Dict[str, Any], str]:
    """Bien dich ke hoach y do hinh anh thanh tpl va args chuan cho runtime engine."""
    tpl = plan["tpl"]
    actions = plan["actions"]
    facts = plan["facts"]
    theme = plan["theme"]
    dur = plan["dur"]
    bg_choice = plan["bg"]
    time_choice = plan["time"]
    move_choice = plan["move"]
    line = plan["line"]
    l_low = line.lower()

    args = {"move": move_choice}

    # =========================================================================
    # A. TEMPLATE: BOARD (SO LIEU THUC TE)
    # =========================================================================
    if tpl == "board":
        bars = []
        if facts:
            # Dung so lieu do duoc thuc te
            fact = facts[0]
            val = fact["value"]
            unit = fact["unit"] or "mph"
            label_text = "TREADMILL SPEED" if "speed" in l_low or unit == "mph" else "MEASURED STAT"
            top_str = f"{val:g} {unit}".strip()
            
            bars.append({
                "label": label_text,
                "v": val,
                "at": 0.3,
                "top": top_str
            })
            max_axis = max(val * 1.3, 5.0) if val < 10 else val * 1.25

            # Neu co fact thu 2 THUC SU trong cau
            if len(facts) > 1:
                f2 = facts[1]
                v2 = f2["value"]
                u2 = f2["unit"] or unit
                bars.append({
                    "label": "COMPARISON",
                    "v": v2,
                    "at": 0.7,
                    "top": f"{v2:g} {u2}".strip()
                })
                max_axis = max(val, v2) * 1.25
        else:
            # Fallback an toan khi khong co fact cu the
            bars.append({"label": "METRIC", "v": 1.0, "at": 0.3, "top": "1.0"})
            max_axis = 2.0

        args.update({
            "title": "EXPERIMENT TELEMETRY",
            "bars": bars,
            "max": round(max_axis, 2)
        })

    # =========================================================================
    # B. TEMPLATE: SCENE (CANH HOAT HINH CHINH)
    # =========================================================================
    elif tpl == "scene":
        people = []
        props = []

        # Case 1: Canh chay tren may tap trong phong thi nghiem (Lab Treadmill - Case B)
        if actions["has_lab"] and (actions["has_run"] or "treadmill" in l_low):
            hero_runner = {
                "preset": theme["hero"],
                "x": 0.48,
                "y": 0.86,
                "h": 0.52 if not is_vertical else 0.40,
                "pose": "run",
                "face": "determined",
                "moveMode": "in_place",
                "in_place": True,
                "walk": True,
                "walkMode": "side",
                "speed": 1.5,
                "weapon": None
            }
            people.append(hero_runner)
            # Them treadmill prop ben duoi chan
            props.append({
                "kind": "treadmill",
                "x": 0.48,
                "y": 0.88,
                "s": 0.60 if not is_vertical else 0.45,
                "at": 0.0
            })
            # Them nha khoa hoc/quan sat vien ben canh
            if not is_vertical:
                people.append({
                    "preset": "smith",
                    "x": 0.18,
                    "y": 0.84,
                    "h": 0.50,
                    "pose": "point",
                    "face": "determined",
                    "flip": False
                })

        # Case 2: Canh nam tren bun va dung day (Mud / Lie / Rise - Case A & Case C)
        elif actions["is_sequence"] or actions["has_lie"]:
            hero_lying = {
                "preset": theme["hero"],
                "x": 0.50,
                "y": 0.85,
                "h": 0.54 if not is_vertical else 0.42,
                "pose": "lying",
                "face": "tired",
                "weapon": theme["weapon"]
            }
            if theme["shield"]:
                hero_lying["shield"] = theme["shield"]

            if actions["has_rise"] or actions["is_sequence"]:
                # Chuyen dong dung day thuc su (getUp / rise)
                rise_time = round(dur * 0.35, 2)
                hero_lying["getUp"] = rise_time
                hero_lying["riseDur"] = round(dur * 0.30, 2)
                hero_lying["faceAt"] = [[rise_time, "determined"]]
                if actions["has_run"]:
                    # Pha 3: Chay sau khi dung day
                    run_time = round(dur * 0.68, 2)
                    hero_lying["poseAt"] = [[rise_time, "kneel"], [run_time, "run"]]
                    hero_lying["walk"] = True
                    hero_lying["moveMode"] = "travel"
                    hero_lying["moveAt"] = run_time
                    hero_lying["to"] = 0.85
                    hero_lying["dur"] = round(dur - run_time, 2)
                    hero_lying["speed"] = 1.3
                else:
                    hero_lying["poseAt"] = [[rise_time, "kneel"], [rise_time + 0.6, "stand"]]

            people.append(hero_lying)

        # Case 3: Canh chay thong thuong (Run)
        elif actions["has_run"]:
            hero_run = {
                "preset": theme["hero"],
                "x": 0.25,
                "y": 0.88,
                "h": 0.56 if not is_vertical else 0.42,
                "pose": "run",
                "face": "determined",
                "moveMode": "travel",
                "walk": True,
                "speed": 1.4,
                "to": 0.80,
                "dur": round(dur * 0.85, 2),
                "weapon": theme["weapon"]
            }
            if theme["shield"]:
                hero_run["shield"] = theme["shield"]
            people.append(hero_run)

        # Case 4: Canh di bo / hanh quan (Walk / March)
        elif actions["has_walk"]:
            hero_walk = {
                "preset": theme["hero"],
                "x": 0.35,
                "h": 0.56 if not is_vertical else 0.42,
                "pose": "march",
                "face": "determined",
                "walk": True,
                "speed": 0.9,
                "weapon": theme["weapon"]
            }
            if theme["shield"]:
                hero_walk["shield"] = theme["shield"]
            people.append(hero_walk)

        # Case 5: Canh binh thuong co bo cuc da dang
        else:
            is_exhausted = bool(re.search(r"\b(exhaustion|tired|heavy|cost|burden|energy)\b", l_low))
            face_choice = "tired" if is_exhausted else "determined" if re.search(r"\b(fit|body|steel|armor|protection)\b", l_low) else "neutral"
            pose_choice = "brace" if is_exhausted else "guard" if re.search(r"\b(guard|protect|harness)\b", l_low) else "stand"

            # Thay doi vi tri theo chu ky de tranh dung mot cho x=0.45
            x_pos = [0.42, 0.55, 0.38, 0.60][plan.get("idx", 0) % 4] if not is_vertical else 0.50
            h_size = 0.56 if not is_vertical else 0.42

            hero_stand = {
                "preset": theme["hero"],
                "x": x_pos,
                "h": h_size,
                "pose": pose_choice,
                "face": face_choice,
                "weapon": theme["weapon"]
            }
            if theme["shield"]:
                hero_stand["shield"] = theme["shield"]
            people.append(hero_stand)

            # Them dong doi o mot so canh
            if not is_vertical and (re.search(r"\b(they|soldiers?|together|army|centuries|trade)\b", l_low) or plan.get("idx", 0) % 3 == 1):
                people.append({
                    "preset": theme["alt"],
                    "x": 0.75 if x_pos < 0.5 else 0.25,
                    "h": 0.52,
                    "pose": "stand",
                    "face": "neutral",
                    "flip": x_pos > 0.5,
                    "weapon": theme["weapon"]
                })

        bg_opts = {}
        if bg_choice in ("field", "plain"):
            bg_opts["trees"] = 2
            bg_opts["bushes"] = 3
        elif bg_choice == "mud":
            bg_opts["wet"] = True

        args.update({
            "bg": bg_choice,
            "time": time_choice,
            "bgOpts": bg_opts,
            "people": people
        })
        if props:
            args["props"] = props

    # =========================================================================
    # C. TEMPLATE: CLOSE (CAN MAT HOAC CAN CHI TIET GIAP)
    # =========================================================================
    elif tpl == "close":
        face = "determined"
        if re.search(r"\b(tired|exhausted|suffer|heavy|burden)\b", l_low):
            face = "tired"
        elif re.search(r"\b(who|why|strange|lead researcher)\b", l_low):
            face = "confused"
        elif re.search(r"\b(truth|reassuring|real protection)\b", l_low):
            face = "calm"

        # Neu la mo ta ao giap tren than (chest, arms, legs), pose mang tinh trinh dien/bao ve
        pose = "guard" if plan["is_anat_chest"] else "think" if face == "confused" else "stand"

        args.update({
            "preset": theme["hero"],
            "face": face,
            "pose": pose,
            "talk": bool(plan.get("speaker") and plan.get("speaker") != "NARRATOR"),
            "x": 0.5,
            "y": 0.48,
            "R": 0.24 if not is_vertical else 0.18,
            "bg": bg_choice,
            "time": time_choice
        })

    # =========================================================================
    # D. TEMPLATE: ITEM (VAT PHAM)
    # =========================================================================
    elif tpl == "item":
        # Khong bao gio dung 'chest' cho long nguc
        kind_map = {
            "armor": "armor", "harness": "armor", "cuirass": "armor", "breastplate": "armor",
            "shield": "shield", "sword": "sword", "helmet": "helmet",
            "weapon": "sword", "spear": "spear", "pilum": "pilum", "bow": "bow",
            "arrow": "arrow", "arrows": "arrows", "torch": "torch",
            "anvil": "anvil", "coin": "coin", "cart": "cart"
        }
        matched_kind = "armor" if is_anatomical_chest(line) else "shield"
        for k, v in kind_map.items():
            if re.search(r"\b" + re.escape(k) + r"\b", l_low):
                matched_kind = v
                break

        thing_obj = {"kind": matched_kind, "s": 0.55 if not is_vertical else 0.4, "x": 0.5, "y": 0.5}
        if matched_kind == "shield" and theme["shield"]:
            thing_obj.update(theme["shield"])

        args.update({
            "thing": thing_obj,
            "bg": "plain" if bg_choice in ("field", "plain") else bg_choice,
            "time": time_choice,
            "sway": True,
            "blur": 12
        })

    # =========================================================================
    # E. CAC TEMPLATE KHAC: ARMY, MAP, TOP, SPLIT
    # =========================================================================
    elif tpl == "army":
        args.update({
            "preset": theme["hero"],
            "presets": [theme["hero"], theme["alt"]],
            "rows": 4,
            "cols": 10 if not is_vertical else 6,
            "march": 1,
            "face": "determined",
            "flags": [{"col": 0.5, "row": 0.8, "kind": theme["flag"]}],
            "enemy": theme["enemy"],
            "bg": bg_choice if bg_choice in ("field", "plain", "mud") else "field",
            "time": time_choice
        })
    elif tpl == "map":
        args.update({
            "view": [-5, 43, 15, 55],
            "places": [{"text": "BATTLEFIELD", "lon": 2.3, "lat": 48.8, "at": 0.3}],
            "routes": [{"pts": [[1.0, 47.0], [2.3, 48.8]], "at": 0.5, "dur": 1.0}],
            "troops": [{"lon": 2.3, "lat": 48.8, "side": "blue", "at": 0.8}],
            "compass": True
        })
    elif tpl == "top":
        args.update({
            "ground": {"color": "#c9ad7a", "grass": True},
            "blocks": [
                {"x": 0.32, "y": 0.5, "w": 0.08, "h": 0.14, "side": "blue", "face": 1, "path": [[0.8, 0.45, 0.5]], "spears": True},
                {"x": 0.68, "y": 0.5, "w": 0.08, "h": 0.14, "side": "red", "face": -1}
            ],
            "arrows": [{"from": [0.32, 0.5], "to": [0.55, 0.5], "at": 0.4}]
        })
    elif tpl == "split":
        args.update({
            "left": {
                "bg": "mud",
                "time": "storm",
                "people": [{"preset": theme["hero"], "x": 0.48, "h": 0.52 if not is_vertical else 0.4, "pose": "brace", "face": "tired"}]
            },
            "right": {
                "bg": "field",
                "time": "sunset",
                "people": [{"preset": theme["alt"], "x": 0.52, "h": 0.52 if not is_vertical else 0.4, "pose": "stand", "face": "determined", "flip": True}]
            },
            "slant": 0.08
        })

    scene_label = f"Visual {tpl}: {line[:40]}" if line else f"Visual {tpl}"
    return tpl, args, scene_label


def assign_visuals(
    proj_dir: str,
    force: bool = False,
    upgrade_generated: bool = False,
    target_ids: Optional[List[str]] = None
) -> Tuple[int, int, bool]:
    """Gan visuals cho du an Squire. Ho tro upgrade generated va bao ve tuyet doi manual visuals."""
    P = os.path.abspath(proj_dir)
    cfg = read_json(os.path.join(P, "config.json"), {})
    pack = cfg.get("pack", "squire")
    if pack != "squire":
        raise ValueError(f"assign_visuals chi ho tro pack squire (hien tai la {pack})")

    shots_file = os.path.join(P, "story", "shots.json")
    if not os.path.exists(shots_file):
        raise FileNotFoundError(f"Chua co {shots_file}. Hay chay draft_shots truoc.")

    story = read_json(shots_file, {})
    shots = story.get("shots", [])
    if not shots:
        raise ValueError("story/shots.json khong co shot nao (0 shots).")

    # Thu thap toan bo van ban de xac dinh chu de
    full_text = " ".join(s.get("line", "") for s in shots)
    theme = detect_theme(full_text)
    is_vertical = cfg.get("aspect") == "9:16"

    assigned_count = 0
    preserved_count = 0
    modified = False

    recent_tpls = []

    for idx, sh in enumerate(shots):
        sid = sh.get("id", f"s{idx+1:03d}")
        if target_ids and sid not in target_ids:
            continue

        existing_tpl = sh.get("tpl")
        existing_args = sh.get("args")
        visual_src = sh.get("visual_source", "")

        # 1. Neu la manual edit: BAO VE TUYET DOI tru khi co force ro rang
        if visual_src == "manual" and not force:
            preserved_count += 1
            recent_tpls.append(existing_tpl)
            continue

        # 2. Neu da co visual hop le va khong co co force / upgrade-generated -> giu nguyen
        if not force and not upgrade_generated and existing_tpl in SQUIRE_TEMPLATES and existing_args and isinstance(existing_args, dict):
            preserved_count += 1
            recent_tpls.append(existing_tpl)
            continue

        # Hoach dinh va bien dich y do hinh anh
        prev_sh = shots[idx - 1] if idx > 0 else None
        next_sh = shots[idx + 1] if idx < len(shots) - 1 else None
        plan = plan_visual_intent(sh, idx, len(shots), theme, is_vertical, prev_sh, next_sh, recent_tpls)
        tpl, args, scene_desc = compile_visual_plan(plan, is_vertical)

        # Kiem tra xem co su thay doi that su so voi du lieu cu khong
        if sh.get("tpl") != tpl or sh.get("args") != args or sh.get("purpose") != plan.get("purpose"):
            modified = True

        sh["tpl"] = tpl
        sh["args"] = args
        sh["purpose"] = plan.get("purpose", "narrative")
        sh["scene"] = scene_desc
        sh["visual_source"] = "template_assigned" if not upgrade_generated else "auto_planned"
        sh["visual_version"] = 2
        sh["visual_plan"] = {
            "purpose": plan.get("purpose", "narrative"),
            "confidence": plan["confidence"],
            "detected_actions": [k for k, v in plan["actions"].items() if v and isinstance(v, bool)],
            "has_quantity_facts": len(plan["facts"]) > 0,
            "review_status": "AUTO_PLANNED" if plan["confidence"] >= 0.9 else "NEEDS_REVIEW"
        }

        recent_tpls.append(tpl)
        assigned_count += 1

    # Chi ghi file va tao backup neu CO SU THAY DOI
    if modified:
        ts_backup = os.path.join(P, "story", f"shots.backup_{int(time.time())}.json")
        backup_file = os.path.join(P, "story", "shots.backup.json")
        try:
            shutil.copyfile(shots_file, ts_backup)
            shutil.copyfile(shots_file, backup_file)
        except Exception:
            pass

        story["shots"] = shots
        write_json(shots_file, story)

    # Tao default thumbnail neu chua co
    thumb_path = os.path.join(P, "scenes", "shots", "thumb.js")
    if not os.path.exists(thumb_path):
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        title_text = cfg.get("title", "VIDEO").upper()
        words = title_text.split()
        t_lines = [" ".join(words[:len(words)//2]), " ".join(words[len(words)//2:])] if len(words) > 3 else [title_text]
        thumb_code = f"""import {{ thumb }} from '/packs/squire/pack.js';
thumb({{
  bg: 'field', time: 'sunset',
  hero: {{ preset: '{theme["hero"]}', face: 'determined', x: 0.72, y: 0.5, R: 0.22 }},
  title: {json.dumps(t_lines)},
  symbols: [{{ kind: 'ban', x: 0.28, y: 0.5, r: 0.18, thing: {{ kind: 'shield' }} }}]
}});
"""
        with open(thumb_path, "w", encoding="utf-8") as f:
            f.write(thumb_code)

    print(f"Xong assign_visuals: {assigned_count} shots cap nhat (giu nguyen {preserved_count} shots da co, modified={modified}) -> {shots_file}")
    return assigned_count, preserved_count, modified


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gan visuals (tpl + args) cho storyboard Squire")
    ap.add_argument("project_pos", nargs="?", default=None, help="Thu muc du an (positional)")
    ap.add_argument("--project", default=None, help="Thu muc du an")
    ap.add_argument("--force", action="store_true", help="Ghi de ca cac shot da co visuals")
    ap.add_argument("--upgrade-generated", action="store_true", help="Nang cap cac shot auto-generated, giu nguyen manual")
    ap.add_argument("--shots", help="Danh sach id shot can gan (phay phan cach)")
    args = ap.parse_args()
    proj = args.project or args.project_pos
    if not proj:
        ap.error("the following arguments are required: --project or project")

    targets = [s.strip() for s in args.shots.split(",") if s.strip()] if args.shots else None
    assign_visuals(proj, force=args.force, upgrade_generated=args.upgrade_generated, target_ids=targets)
