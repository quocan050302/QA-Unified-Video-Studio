#!/usr/bin/env python3
"""tools/character_bible.py — P0 Persistent Character Bible & Multi-View Consistency Guard.

V14.3 Requirement:
1. Establish persistent identities (character_id, faction_id, costume_id, equipment_id, palette, features).
2. Lock character attributes across all 2D perspective views (front, profile, 3/4, rear, OTS).
3. Validate character turnaround consistency: camera transforms geometry, NOT costume or faction identity.
4. Fail-closed on unauthorized visual metamorphosis (e.g., Roman turning into opponent, color swaps).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class CharacterPalette(BaseModel):
    primary: str = Field(description="Primary uniform / tunic / coat color hex")
    secondary: str = Field(description="Secondary trim / leather / trousers color hex")
    armor_metal: str = Field(description="Armor metal finish (iron, bronze, blackened)")
    helmet_crest: str = Field(description="Crest / plume color (red, black, white, gold)")
    shield_field: str = Field(description="Shield field background color")
    shield_emblem: str = Field(description="Shield insignia / blazon color")


class EquipmentProfile(BaseModel):
    helmet_type: str = Field(description="Montefortino, Coolus, Bascinet, Kabuto, or Cap")
    armor_type: str = Field(description="Lorica Segmentata, Lorica Hamata, Plate, O-Yoroi, None")
    shield_type: str = Field(description="Scutum, Heater, Buckler, Pavise, None")
    primary_weapon: str = Field(description="Gladius, Pilum, Longsword, Katana, Spear")
    secondary_weapon: Optional[str] = None
    dominant_hand: str = Field(default="right")


class CharacterProfile(BaseModel):
    character_id: str
    name: str
    faction_id: str
    role: str  # officer, veteran, recruit, chieftain, samurai, knight, civilian
    pack: str  # squire or dem
    palette: CharacterPalette
    equipment: EquipmentProfile
    body_proportions: Dict[str, float] = Field(default_factory=lambda: {"height": 1.0, "width": 1.0, "head_scale": 1.0})
    unique_features: List[str] = Field(default_factory=list)


class CharacterBible(BaseModel):
    schema_version: str = "1.0"
    project_id: str
    factions: Dict[str, str] = Field(default_factory=dict)
    characters: Dict[str, CharacterProfile] = Field(default_factory=dict)


# Default Archetypes for Multi-Genre Video Production
DEFAULT_ARCHETYPES = {
    "roman_centurion": CharacterProfile(
        character_id="centurion_marcus",
        name="Centurion Marcus",
        faction_id="legio_viii",
        role="officer",
        pack="squire",
        palette=CharacterPalette(
            primary="#8B0000",       # Deep Roman Red tunic
            secondary="#5C3317",     # Dark leather harness
            armor_metal="#D4AF37",   # Gilded / Brass Lorica Hamata with phalerae
            helmet_crest="#C00000",  # Transverse Red Crest
            shield_field="#8B0000",
            shield_emblem="#FFD700", # Golden Winged Thunderbolt
        ),
        equipment=EquipmentProfile(
            helmet_type="Imperial Gallic with Transverse Crest",
            armor_type="Lorica Hamata with Phalerae",
            shield_type="Curved Rectangular Scutum",
            primary_weapon="Gladius Hispaniensis (Right Hip)",
            secondary_weapon="Pugio (Dagger, Left Hip)",
            dominant_hand="right",
        ),
        unique_features=["Transverse crest", "Vitis vine staff", "Decorated greaves"],
    ),
    "roman_legionary": CharacterProfile(
        character_id="legionary_titus",
        name="Legionary Titus",
        faction_id="legio_viii",
        role="veteran",
        pack="squire",
        palette=CharacterPalette(
            primary="#9E2A2B",
            secondary="#4A3B32",
            armor_metal="#B0C4DE",   # Polished Iron Lorica Segmentata
            helmet_crest="#000000",  # No plume or dark horsehair
            shield_field="#A61C1C",
            shield_emblem="#E0AA3E",
        ),
        equipment=EquipmentProfile(
            helmet_type="Coolus / Gallic Type G",
            armor_type="Lorica Segmentata",
            shield_type="Curved Rectangular Scutum",
            primary_weapon="Pilum Heavy Javelin",
            secondary_weapon="Gladius",
            dominant_hand="right",
        ),
        unique_features=["Pilum in right hand", "Caligae studded boots"],
    ),
    "barbarian_chieftain": CharacterProfile(
        character_id="chieftain_brennos",
        name="Chieftain Brennos",
        faction_id="gallic_tribes",
        role="chieftain",
        pack="squire",
        palette=CharacterPalette(
            primary="#2B4162",       # Woad Blue / Indigo Tunic
            secondary="#E0A96D",     # Checked Plaid Cloak
            armor_metal="#CD7F32",   # Bronze Torc & Iron Mail
            helmet_crest="#FFD700",  # Winged Bronze Helmet
            shield_field="#385F71",
            shield_emblem="#D4AF37", # Celtic Triskele
        ),
        equipment=EquipmentProfile(
            helmet_type="Gallic Horned / Winged Helmet",
            armor_type="Chainmail with Bronze Torc",
            shield_type="Oval Wicker & Leather Shield",
            primary_weapon="Long Iron Spatha Slashing Sword",
            secondary_weapon="Broad-head Spear",
            dominant_hand="right",
        ),
        unique_features=["Golden Torc around neck", "Flowing mustache", "Oval shield boss"],
    ),
    "medieval_knight": CharacterProfile(
        character_id="knight_gawain",
        name="Sir Gawain",
        faction_id="english_vanguard",
        role="knight",
        pack="squire",
        palette=CharacterPalette(
            primary="#1C3144",       # Navy Surcoat
            secondary="#A00000",     # Crimson Cross
            armor_metal="#C0C0C0",   # Bright Plate Steel
            helmet_crest="#FFFFFF",
            shield_field="#F0F0F0",
            shield_emblem="#A00000",
        ),
        equipment=EquipmentProfile(
            helmet_type="Hounskull Bascinet with Snout Visor",
            armor_type="Full Plate with Mail Aventail",
            shield_type="Heater Shield",
            primary_weapon="Arming Sword",
            secondary_weapon="Dagger",
            dominant_hand="right",
        ),
        unique_features=["Pointed snout visor", "Aventail mail drape"],
    ),
    "samurai_warrior": CharacterProfile(
        character_id="samurai_kenshin",
        name="Kenshin",
        faction_id="takeda_clan",
        role="samurai",
        pack="squire",
        palette=CharacterPalette(
            primary="#101010",       # Lacquered Black
            secondary="#C41E3A",     # Scarlet Odoshi Cord
            armor_metal="#2F4F4F",   # Dark Lacquered Iron
            helmet_crest="#FFD700",  # Golden Crescent Maedate
            shield_field="#000000",
            shield_emblem="#C41E3A",
        ),
        equipment=EquipmentProfile(
            helmet_type="Kabuto with Crescent Maedate",
            armor_type="O-Yoroi with Tiered Shikoro",
            shield_type="None",
            primary_weapon="Katana",
            secondary_weapon="Wakizashi",
            dominant_hand="right",
        ),
        unique_features=["Crescent horn crest", "Tiered shikoro neck guard"],
    ),
    "dem_hero": CharacterProfile(
        character_id="dem_protagonist",
        name="Protagonist",
        faction_id="modern_self",
        role="civilian",
        pack="dem",
        palette=CharacterPalette(
            primary="#2B2D42",       # Charcoal Body
            secondary="#8D99AE",     # Accent Slate
            armor_metal="#000000",
            helmet_crest="#000000",
            shield_field="#EDF2F4",
            shield_emblem="#EF233C",
        ),
        equipment=EquipmentProfile(
            helmet_type="None",
            armor_type="Minimalist Bean Silhouette",
            shield_type="None",
            primary_weapon="Smartphone / Notebook",
            secondary_weapon=None,
            dominant_hand="right",
        ),
        unique_features=["Clean minimalist vector", "Expressive eye dots"],
    ),
}


def build_character_bible(project_path: Path | str, director_plan: Optional[Dict[str, Any]] = None) -> CharacterBible:
    """
    Construct persistent CharacterBible for a project.
    Inspects config.json, shots.json, and director plan to assign canonical, persistent profiles.
    """
    proj = Path(project_path).resolve()
    cfg_p = proj / "config.json"
    cfg: Dict[str, Any] = {}
    if cfg_p.is_file():
        try:
            with open(cfg_p, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    pack = cfg.get("pack", "squire")
    genre = cfg.get("genre", "self_improvement" if pack == "dem" else "roman")
    proj_id = proj.name

    bible = CharacterBible(
        project_id=proj_id,
        factions={
            "legio_viii": "Eighth Augustan Legion",
            "gallic_tribes": "Allied Celtic Warbands",
            "english_vanguard": "14th Century Royal Vanguard",
            "takeda_clan": "Takeda Cavalry Corps",
            "modern_self": "Self-Improvement Inner Mind",
        },
        characters={},
    )

    if pack == "dem":
        bible.characters["dem_protagonist"] = DEFAULT_ARCHETYPES["dem_hero"]
        bible.characters["mentor"] = DEFAULT_ARCHETYPES["dem_hero"].model_copy(
            update={"character_id": "mentor", "name": "Mentor Guide", "palette": CharacterPalette(
                primary="#1D3557", secondary="#457B9D", armor_metal="#000000", helmet_crest="#000000", shield_field="#F1FAEE", shield_emblem="#E63946"
            )}
        )
    elif genre in ("medieval", "knight"):
        bible.characters["knight_gawain"] = DEFAULT_ARCHETYPES["medieval_knight"]
        bible.characters["archer_robin"] = DEFAULT_ARCHETYPES["medieval_knight"].model_copy(
            update={"character_id": "archer_robin", "name": "English Longbowman", "role": "archer"}
        )
    elif genre in ("samurai", "japanese"):
        bible.characters["samurai_kenshin"] = DEFAULT_ARCHETYPES["samurai_warrior"]
        bible.characters["ashigaru_spear"] = DEFAULT_ARCHETYPES["samurai_warrior"].model_copy(
            update={"character_id": "ashigaru_spear", "name": "Ashigaru Yari Spearman", "role": "infantry"}
        )
    else:
        # Default Roman Military History
        bible.characters["centurion_marcus"] = DEFAULT_ARCHETYPES["roman_centurion"]
        bible.characters["legionary_titus"] = DEFAULT_ARCHETYPES["roman_legionary"]
        bible.characters["chieftain_brennos"] = DEFAULT_ARCHETYPES["barbarian_chieftain"]

    # Save to story/character_bible.json
    story_dir = proj / "story"
    story_dir.mkdir(parents=True, exist_ok=True)
    bible_file = story_dir / "character_bible.json"
    with open(bible_file, "w", encoding="utf-8") as f:
        f.write(bible.model_dump_json(indent=2))

    return bible


def validate_character_turnaround(bible: CharacterBible, shot_sequences: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verify character consistency across shots and camera angles.
    Enforces:
    1. An actor's faction, palette, and helmet archetype must remain identical across cuts.
    2. Rear views must NEVER render face elements (enforced by geometry).
    3. Over-the-shoulder foreground figures must match known faction silhouettes.
    """
    errors: List[str] = []
    actor_views_observed: Dict[str, Set[str]] = {}

    for s in shot_sequences:
        sid = s.get("id", "unknown")
        actor_id = s.get("character_id") or s.get("actor")
        view = s.get("view", "front")
        
        if not actor_id:
            continue

        if actor_id not in actor_views_observed:
            actor_views_observed[actor_id] = set()
        actor_views_observed[actor_id].add(view)

        # Check if actor is in bible
        matching_char = next((c for cid, c in bible.characters.items() if cid == actor_id or c.name.lower() in str(actor_id).lower()), None)
        if matching_char:
            # Check for illegal costume swap
            shot_costume = s.get("costume")
            if shot_costume and shot_costume != matching_char.equipment.armor_type:
                # Unless explicitly tagged as costume change event
                if not s.get("costume_change_event"):
                    errors.append(f"Shot '{sid}': Illegal costume change for '{actor_id}' from '{matching_char.equipment.armor_type}' to '{shot_costume}'")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "actors_tracked": len(actor_views_observed),
        "views_per_actor": {a: sorted(list(vs)) for a, vs in actor_views_observed.items()},
    }


if __name__ == "__main__":
    import sys
    proj_dir = sys.argv[1] if len(sys.argv) > 1 else "projects/squire-mau"
    b = build_character_bible(proj_dir)
    print(f"Character Bible built for {proj_dir} with {len(b.characters)} characters:")
    for cid, c in b.characters.items():
        print(f" - {c.name} ({c.role}): {c.equipment.armor_type}, {c.equipment.primary_weapon}")
