"""visual_facts.py — Trích xuất và xác thực dữ liệu số lượng (quantity facts)
từ kịch bản để đảm bảo hiển thị infographic trung thực, không bịa số liệu.
"""
import re
from typing import List, Dict, Any, Optional

# Bản đồ số chữ tiếng Anh cơ bản
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

UNITS_MAP = {
    "mph": "mph",
    "miles per hour": "mph",
    "mile per hour": "mph",
    "km/h": "km/h",
    "kmh": "km/h",
    "kilometers per hour": "km/h",
    "kg": "kg",
    "kilograms": "kg",
    "kilos": "kg",
    "pounds": "lbs",
    "pound": "lbs",
    "lbs": "lbs",
    "percent": "%",
    "%": "%",
    "seconds": "s",
    "second": "s",
    "minutes": "min",
    "minute": "min",
    "hours": "hrs",
    "hour": "hrs",
    "miles": "miles",
    "mile": "miles",
}


def parse_spelled_number(text: str) -> Optional[float]:
    """Chuyển đổi chuỗi chữ số tiếng Anh như 'three-point-eight' hoặc 'one hundred and twenty' thành float."""
    t = text.lower().replace("-", " ").strip()
    
    # Trường hợp số thập phân chữ: "three point eight"
    m_point = re.match(r"^([a-z]+)\s+point\s+([a-z]+)$", t)
    if m_point:
        whole_str, frac_str = m_point.group(1), m_point.group(2)
        if whole_str in NUMBER_WORDS and frac_str in NUMBER_WORDS:
            return float(NUMBER_WORDS[whole_str]) + float(NUMBER_WORDS[frac_str]) / 10.0

    # Phân tích các số nguyên ghép: e.g. "one hundred and twenty", "thirty five"
    words = t.replace(" and ", " ").split()
    total = 0
    curr = 0
    for w in words:
        if w in NUMBER_WORDS:
            curr += NUMBER_WORDS[w]
        elif w == "hundred":
            curr = (curr or 1) * 100
        elif w == "thousand":
            total += (curr or 1) * 1000
            curr = 0
        elif w == "million":
            total += (curr or 1) * 1000000
            curr = 0
        else:
            return None
    return float(total + curr) if (total + curr) > 0 else None


def extract_quantity_facts(line: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
    """Trích xuất danh sách các sự kiện số lượng có căn cứ từ câu nói."""
    if not line:
        return []
    
    facts = []
    l_low = line.lower()

    # Loại bỏ các mẫu không phải số đo đạc (năm thế kỷ, giờ giấc, chương mục)
    ignored_patterns = [
        r"\b\d+(?:st|nd|rd|th)\s+century\b",
        r"\b(?:century|century's)\b",
        r"\b\d{1,2}\s*(?:a\.m\.|p\.m\.|o'clock)\b",
        r"\bchapter\s+\d+\b",
        r"\bpart\s+\d+\b",
    ]
    cleaned_line = l_low
    for pat in ignored_patterns:
        cleaned_line = re.sub(pat, " ", cleaned_line)

    # 1. Tìm kiếm số thập phân dạng chữ có đơn vị: e.g. "three-point-eight miles per hour"
    spelled_pat = r"\b((?:[a-z]+[\s\-]+)?point[\s\-]+[a-z]+)\s*(mph|miles per hour|mile per hour|km/h|percent|kg|pounds)?\b"
    for m in re.finditer(spelled_pat, cleaned_line):
        num_str = m.group(1)
        unit_str = m.group(2) or ""
        val = parse_spelled_number(num_str)
        if val is not None:
            unit_norm = UNITS_MAP.get(unit_str.strip(), unit_str.strip())
            # Nếu chưa có đơn vị đi kèm ngay sau, tìm trong phạm vi 3 từ tiếp theo
            if not unit_norm:
                after_text = cleaned_line[m.end():m.end() + 25]
                for u_key, u_val in UNITS_MAP.items():
                    if re.search(r"\b" + re.escape(u_key) + r"\b", after_text):
                        unit_norm = u_val
                        break
            facts.append({
                "raw_text": m.group(0),
                "value": val,
                "unit": unit_norm,
                "span": m.span(),
                "confidence": 0.95 if unit_norm else 0.8,
                "source": "spelled_decimal"
            })

    # 2. Tìm kiếm số chữ thông thường: e.g. "one hundred and twenty", "thirty"
    word_num_pat = r"\b((?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\s+(?:hundred(?:\s+and)?\s+)?(?:[a-z]+)?)\s*(mph|miles per hour|km/h|percent|kg|pounds|miles)?\b"
    for m in re.finditer(word_num_pat, cleaned_line):
        num_str = m.group(1)
        unit_str = m.group(2) or ""
        val = parse_spelled_number(num_str)
        if val is not None and val not in [f["value"] for f in facts]:
            unit_norm = UNITS_MAP.get(unit_str.strip(), unit_str.strip())
            facts.append({
                "raw_text": m.group(0),
                "value": val,
                "unit": unit_norm,
                "span": m.span(),
                "confidence": 0.9 if unit_norm else 0.75,
                "source": "spelled_integer"
            })

    # 3. Tìm kiếm số thực số học (digits): e.g. "3.8", "120", "20 miles"
    digit_pat = r"\b(\d+(?:[\.,]\d+)?)\s*(mph|miles per hour|mile per hour|km/h|percent|%|kg|pounds|lbs|seconds|hours|miles)?\b"
    for m in re.finditer(digit_pat, cleaned_line):
        num_str = m.group(1).replace(",", ".")
        try:
            val = float(num_str)
        except ValueError:
            continue
        
        # Tránh thêm lại nếu trùng giá trị từ spelled
        if any(abs(f["value"] - val) < 1e-5 for f in facts):
            continue

        unit_str = m.group(2) or ""
        unit_norm = UNITS_MAP.get(unit_str.strip(), unit_str.strip())
        if not unit_norm:
            after_text = cleaned_line[m.end():m.end() + 25]
            for u_key, u_val in UNITS_MAP.items():
                if re.search(r"\b" + re.escape(u_key) + r"\b", after_text):
                    unit_norm = u_val
                    break

        facts.append({
            "raw_text": m.group(0),
            "value": val,
            "unit": unit_norm,
            "span": m.span(),
            "confidence": 0.95 if unit_norm else 0.75,
            "source": "numeric_digits"
        })

    return facts


def is_anatomical_chest(line: str) -> bool:
    """Kiểm tra từ 'chest' trong ngữ cảnh là lồng ngực (anatomical torso) hay rương gỗ (treasure chest)."""
    l_low = line.lower()
    if "chest" not in l_low:
        return False
    
    # Các từ liên quan đến cơ thể, giải phẫu học, áo giáp
    anatomical_tokens = [
        "arms", "legs", "armor", "armour", "plate", "torso", "body", "ribs",
        "breath", "heart", "head", "shoulder", "greaves", "pauldrons", "harness",
        "steel", "breastplate", "cuirass", "flesh", "muscles", "waist"
    ]
    for token in anatomical_tokens:
        if token in l_low:
            return True

    # Các từ liên quan đến rương báu, kho tàng
    furniture_tokens = ["treasure", "gold", "coins", "wooden", "locked", "storage", "box", "loot", "trunk"]
    for token in furniture_tokens:
        if token in l_low:
            return False

    # Mặc định trong ngữ cảnh quân sự/áo giáp: chest là lồng ngực
    return True

