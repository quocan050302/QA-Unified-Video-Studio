"""assign_visuals.py — Tu dong phan tich kich ban va gan hinh anh hoat hinh (template + args)
cho storyboard cua pack squire.
  python tools/assign_visuals.py --project projects/<ten> [--force] [--all]
"""
import argparse, json, os, re, sys, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_json, write_json

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

def detect_theme(full_text: str):
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

def assign_visuals(proj_dir: str, force: bool = False, target_ids: list = None):
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
        raise ValueError(f"story/shots.json khong co shot nao (0 shots).")
    
    # Tao backup an toan truoc khi sua
    backup_file = os.path.join(P, "story", "shots.backup.json")
    if not os.path.exists(backup_file):
        shutil.copyfile(shots_file, backup_file)
    
    # Thu thap toan bo van ban de xac dinh chu de
    full_text = " ".join(s.get("line", "") for s in shots)
    theme = detect_theme(full_text)
    
    is_vertical = cfg.get("aspect") == "9:16"
    
    # Danh sach boi canh luan phien
    bg_cycle = ["field", "plain", "castle", "field", "mud", "hall"]
    time_cycle = ["day", "golden", "sunset", "dusk", "day", "night"]
    camera_moves = ["in", "right", "out", "left", "in", "still"]
    
    # Quan sat template gan nhat de chong lap lai
    recent_tpls = []
    
    assigned_count = 0
    preserved_count = 0
    
    for idx, sh in enumerate(shots):
        sid = sh.get("id", f"s{idx+1:03d}")
        
        # Neu chi dinh target_ids ma khong trung thi bo qua
        if target_ids and sid not in target_ids:
            continue
        
        # Neu shot da co tpl hop le va khong co co force -> giu nguyen
        existing_tpl = sh.get("tpl")
        existing_args = sh.get("args")
        if not force and existing_tpl in SQUIRE_TEMPLATES and existing_args and isinstance(existing_args, dict):
            preserved_count += 1
            recent_tpls.append(existing_tpl)
            continue
        
        line = (sh.get("line") or "").strip()
        l_low = line.lower()
        dur = (sh.get("end") or 0) - (sh.get("start") or 0)
        
        bg_choice = bg_cycle[idx % len(bg_cycle)]
        time_choice = time_cycle[idx % len(time_cycle)]
        move_choice = camera_moves[idx % len(camera_moves)]
        
        # Can nhac thoi gian ngay/dem theo loi thoai
        if re.search(r"\b(night|2 a\.m\.|2 o'clock|midnight|sleep|dark|moon)\b", l_low):
            time_choice = "night"
        elif re.search(r"\b(sunset|sun is going down|evening|dusk)\b", l_low):
            time_choice = "sunset"
        elif re.search(r"\b(morning|dawn|sun rises?|sunrise)\b", l_low):
            time_choice = "dawn"
            
        if re.search(r"\b(castle|hall|inside|room|bed|walls?)\b", l_low):
            bg_choice = "castle" if bg_choice not in ("castle", "hall") else bg_choice
        elif re.search(r"\b(mud|rain|wet|trench)\b", l_low):
            bg_choice = "mud"
        
        # 1. Kiem tra Board / So lieu thong ke
        is_stats = bool(re.search(r"\b(\d+|hundred|thousand|million|percent|grams?|cubes?|hours?|miles?)\b", l_low) and
                        re.search(r"\b(roughly|burns?|about|stats?|numbers?|data|worth|thirty|hundred and twenty)\b", l_low))
        
        # 2. Kiem tra Item / Vat pham / Vu khi
        item_match = re.search(r"\b(shield|sword|helmet|sandals?|weapon|spear|pilum|bow|arrows?|organ|liver|brain|tea|supplement|sugar|torch|chest|anvil|coin)\b", l_low)
        
        # 3. Kiem tra Ban do
        is_map = bool(re.search(r"\b(map|territory|continent|europe|border|across the sea|marched across|geography)\b", l_low))
        
        # 4. Kiem tra So do chien thuat tren cao
        is_top = bool(re.search(r"\b(formation|flank|behind them|surround|tactics?|positions?|layout|camp|fort)\b", l_low))
        
        # 5. Kiem tra Doan quan hanh quan / Dong nguoi
        is_army = bool(re.search(r"\b(army|soldiers?|legion|troops?|hundreds|thousands?|twenty miles|marching|men in line|host|ranks)\b", l_low))
        
        # 6. Kiem tra Can mat (Cau hoi / Cam xuc / Phan ung)
        is_close = bool("?" in line or
                        re.search(r"\b(who|why|how|wonder|strange|feet are bleeding|all you want|tired|pain|secret|online|telling you|truth is)\b", l_low) or
                        dur < 2.5)
        
        # 7. Kiem tra Split (So sanh / Hai mat)
        is_split = bool(re.search(r"\b(versus|vs|on the other hand|myth|instead of|two things|differ)\b", l_low))
        
        # Chon template voi quy tac chong lap
        chosen_tpl = None
        
        if is_split and recent_tpls[-2:].count("split") == 0:
            chosen_tpl = "split"
        elif is_map and recent_tpls[-2:].count("map") == 0:
            chosen_tpl = "map"
        elif is_top and recent_tpls[-2:].count("top") == 0:
            chosen_tpl = "top"
        elif is_stats and recent_tpls[-2:].count("board") == 0:
            chosen_tpl = "board"
        elif item_match and recent_tpls[-2:].count("item") == 0 and not is_close:
            chosen_tpl = "item"
        elif is_army and recent_tpls[-2:].count("army") == 0:
            chosen_tpl = "army"
        elif is_close and recent_tpls[-2:].count("close") == 0:
            chosen_tpl = "close"
        else:
            chosen_tpl = "scene"
            
        # Neu template duoc chon giong voi 2 shot lien truoc, dao qua template khac
        if len(recent_tpls) >= 2 and recent_tpls[-1] == chosen_tpl and recent_tpls[-2] == chosen_tpl:
            chosen_tpl = "close" if chosen_tpl == "scene" else "scene"
            
        recent_tpls.append(chosen_tpl)
        
        # Xay dung args chi tiet theo chosen_tpl
        args = {"move": move_choice}
        
        if chosen_tpl == "board":
            # Tach cac con so neu co
            nums = re.findall(r"\d+", line)
            v1 = int(nums[0]) if len(nums) > 0 else 30
            v2 = int(nums[1]) if len(nums) > 1 else 120
            args.update({
                "title": "DATA ANALYSIS",
                "bars": [
                    {"label": "STAGE 1", "v": min(v1, 100), "at": 0.2, "top": str(v1)},
                    {"label": "STAGE 2", "v": min(v2, 100), "at": 0.6, "top": str(v2)}
                ],
                "max": max(100, v1, v2)
            })
            
        elif chosen_tpl == "item":
            matched_word = item_match.group(1).lower() if item_match else "shield"
            # Map ve cac prop ho tro boi templates.js:
            # shield, pavise, sword, spear, pilum, pollaxe, axe, bow, crossbow, rifle, torch,
            # flag, tent, tree, castle, helmet, gauntlet, arrow, arrows, sack, barrel, rock,
            # campfire, chest, coin, anvil, lantern, cart, skull
            kind_map = {
                "shield": "shield", "sword": "sword", "helmet": "helmet", "sandals": "sack",
                "weapon": "sword", "spear": "spear", "pilum": "pilum", "bow": "bow",
                "arrow": "arrow", "arrows": "arrows", "organ": "chest", "liver": "chest",
                "brain": "skull", "tea": "sack", "supplement": "coin", "sugar": "sack",
                "torch": "torch", "chest": "chest", "anvil": "anvil", "coin": "coin"
            }
            thing_kind = kind_map.get(matched_word, "shield")
            thing_obj = {"kind": thing_kind, "s": 0.55 if not is_vertical else 0.4, "x": 0.5, "y": 0.5}
            if thing_kind == "shield" and theme["shield"]:
                thing_obj.update(theme["shield"])
            args.update({
                "thing": thing_obj,
                "bg": bg_choice if bg_choice in ("castle", "hall") else "plain",
                "time": time_choice,
                "sway": True,
                "blur": 14
            })
            
        elif chosen_tpl == "map":
            args.update({
                "view": [5, 36, 24, 47] if theme["name"] == "roman" else [-5, 42, 10, 52],
                "places": [{"text": "FIELD", "lon": 12.5, "lat": 41.9, "at": 0.3}],
                "routes": [{"pts": [[10.0, 43.5], [12.5, 41.9]], "at": 0.5, "dur": 1.0}],
                "troops": [{"lon": 12.5, "lat": 41.9, "side": "red", "at": 0.8}],
                "compass": True
            })
            
        elif chosen_tpl == "top":
            args.update({
                "ground": {"color": "#c9ad7a", "grass": True},
                "blocks": [
                    {"x": 0.32, "y": 0.5, "w": 0.08, "h": 0.14, "side": "blue", "face": 1, "path": [[0.8, 0.45, 0.5]], "spears": True},
                    {"x": 0.68, "y": 0.5, "w": 0.08, "h": 0.14, "side": "red", "face": -1}
                ],
                "arrows": [{"from": [0.32, 0.5], "to": [0.55, 0.5], "at": 0.4}],
                "dust": [{"x": 0.45, "y": 0.5, "s": 0.12, "at": 0.6}]
            })
            
        elif chosen_tpl == "army":
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
            
        elif chosen_tpl == "close":
            # Chon bieu cam mat
            face = "neutral"
            if re.search(r"\b(tired|feet are bleeding|sleep|exhausted|burns?)\b", l_low):
                face = "tired"
            elif re.search(r"\b(pain|bleeding|hurt|wound|toxic)\b", l_low):
                face = "pain"
            elif re.search(r"\b(who|why|strange|secret|online)\b", l_low):
                face = "confused"
            elif re.search(r"\b(reassuring|truth|impressive)\b", l_low):
                face = "calm"
            elif re.search(r"\b(determined|fight|stand|hold)\b", l_low):
                face = "determined"
                
            pose = "think" if face in ("confused", "neutral") else "shrug" if face == "tired" else "stand"
            
            args.update({
                "preset": theme["hero"],
                "face": face,
                "pose": pose,
                "talk": bool(sh.get("speaker") and sh.get("speaker") != "NARRATOR"),
                "x": 0.5,
                "y": 0.48,
                "R": 0.24 if not is_vertical else 0.18,
                "bg": bg_choice,
                "time": time_choice
            })
            
        elif chosen_tpl == "split":
            args.update({
                "left": {
                    "bg": "plain",
                    "time": "day",
                    "people": [{"preset": theme["hero"], "x": 0.48, "h": 0.55 if not is_vertical else 0.4, "face": "confused"}]
                },
                "right": {
                    "bg": "field",
                    "time": "sunset",
                    "people": [{"preset": theme["alt"], "x": 0.52, "h": 0.55 if not is_vertical else 0.4, "face": "determined", "flip": True}]
                },
                "slant": 0.08
            })
            
        else: # scene
            is_walking = bool(re.search(r"\b(marched|walk|moving|going|shift|advance|twenty miles)\b", l_low))
            face = "tired" if re.search(r"\b(tired|sleep|burns?)\b", l_low) else "determined" if is_walking else "neutral"
            pose = "march" if is_walking else "guard" if re.search(r"\b(nobody lies down|stop|stand|guard)\b", l_low) else "stand"
            
            p1 = {
                "preset": theme["hero"],
                "x": 0.45 if not is_walking else 0.35,
                "h": 0.58 if not is_vertical else 0.42,
                "pose": pose,
                "face": face,
                "weapon": theme["weapon"]
            }
            if theme["shield"]:
                p1["shield"] = theme["shield"]
            if is_walking:
                p1["walk"] = True
                p1["speed"] = 0.8
                
            people_list = [p1]
            
            # Them nguoi thu hai o canh thoai hoac canh dong
            if not is_vertical and (idx % 2 == 1 or re.search(r"\b(together|they|we|nobody|someone)\b", l_low)):
                people_list.append({
                    "preset": theme["alt"],
                    "x": 0.72,
                    "h": 0.55,
                    "pose": "stand",
                    "face": "neutral",
                    "flip": True,
                    "weapon": theme["weapon"]
                })
            
            bg_opts = {}
            if bg_choice in ("field", "plain"):
                bg_opts["trees"] = 2
                bg_opts["bushes"] = 3
                if idx % 3 == 0:
                    bg_opts["castle"] = True
                if idx % 4 == 0:
                    bg_opts["tents"] = 3
                    
            args.update({
                "bg": bg_choice,
                "time": time_choice,
                "bgOpts": bg_opts,
                "people": people_list
            })
            
            # Neu co mua ten hoac mua bao
            if re.search(r"\b(arrow|arrows|volley|attack)\b", l_low):
                args["fx"] = [{"kind": "volley", "at": 0.2, "n": 30}]
            elif time_choice == "night" and bg_choice in ("field", "plain"):
                args["props"] = [{"kind": "campfire", "x": 0.58, "y": 0.85, "s": 0.16}]
                
        # Gan tpl va args vao shot
        sh["tpl"] = chosen_tpl
        sh["args"] = args
        sh["scene"] = f"Visual {chosen_tpl}: {line[:40]}"
        assigned_count += 1

    # Luu ket qua vao shots.json
    story["shots"] = shots
    write_json(shots_file, story)
    
    # Kiem tra va tao default thumbnail script neu chua co
    thumb_path = os.path.join(P, "scenes", "shots", "thumb.js")
    if not os.path.exists(thumb_path):
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        title_text = cfg.get("title", "VIDEO").upper()
        # Chia thanh 2 dong ngan
        words = title_text.split()
        if len(words) > 3:
            mid = len(words) // 2
            t_lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        else:
            t_lines = [title_text]
            
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
        print(f"Da khoi tao scenes/shots/thumb.js cho thumbnail")

    print(f"Xong assign_visuals: Da gan hinh anh cho {assigned_count} shots (giu nguyen {preserved_count} shots da co) -> {shots_file}")
    return assigned_count, preserved_count

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gan visuals (tpl + args) cho storyboard Squire")
    ap.add_argument("project_pos", nargs="?", default=None, help="Thu muc du an (positional)")
    ap.add_argument("--project", default=None, help="Thu muc du an")
    ap.add_argument("--force", action="store_true", help="Ghi de ca cac shot da co visuals")
    ap.add_argument("--shots", help="Danh sach id shot can gan (phay phan cach)")
    args = ap.parse_args()
    proj = args.project or args.project_pos
    if not proj:
        ap.error("the following arguments are required: --project or project")
    
    targets = [s.strip() for s in args.shots.split(",") if s.strip()] if args.shots else None
    assign_visuals(proj, force=args.force, target_ids=targets)
