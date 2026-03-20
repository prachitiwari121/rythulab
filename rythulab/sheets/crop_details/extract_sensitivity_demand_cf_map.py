from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, Optional

try:
    from rythulab.sheets.cf_label_extract import build_cf_info_map
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from cf_label_extract import build_cf_info_map


CROP_DETAILS_DIR = Path(__file__).resolve().parent

SENSITIVITY_RE = re.compile(r"^\s*sensit(?:ive|ivity)\s+to\s+(.+?)(?:\s*\(|$)", re.IGNORECASE)
DEMAND_CLASS_RE = re.compile(r"^\s*(.+?)\s+demand\s+class(?:\s*\(|$)", re.IGNORECASE)

FEATURE_TO_CF_PATTERNS = [
    (r"nitrogen", "CF1"),
    (r"phosphorus", "CF2"),
    (r"potassium", "CF3"),
    (r"organic\s+carbon", "CF4"),
    (r"\bp\s*h\b|soil\s+ph", "CF5"),
    (r"\bec\b|salinity", "CF6"),
    (r"texture", "CF7"),
    (r"depth", "CF8"),
    (r"water\s+holding\s+capacity", "CF9"),
    (r"compaction", "CF10"),
    (r"drainage", "CF11"),
    (r"erosion", "CF12"),
    (r"ground\s*water|groundwater", "CF13"),
    (r"irrigation", "CF14"),
    (r"rain\s+reliab", "CF15"),
    (r"temp|temperature", "CF16"),
    (r"heat\s+days|heat\s+stress", "CF17"),
    (r"frost", "CF18"),
    (r"wind", "CF19"),
    (r"bio\s*index|biological\s+index", "CF20"),
    (r"pest\s+pressure|pest", "CF21"),
    (r"earthworm", "CF22"),
    (r"slope", "CF23"),
    (r"flood\s+risk", "CF24"),
    (r"drought\s+risk", "CF25"),
    (r"\bca\b|calcium", "CF26"),
    (r"bulk\s+density", "CF27"),
    (r"water\s+demand", "CF14"),
]


def _normalize_text(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_feature(parameter_name: str) -> tuple[Optional[str], Optional[str]]:
    sensitivity_match = SENSITIVITY_RE.search(parameter_name or "")
    if sensitivity_match:
        return "sensitivity", sensitivity_match.group(1).strip()

    demand_match = DEMAND_CLASS_RE.search(parameter_name or "")
    if demand_match:
        return "demand_class", demand_match.group(1).strip()

    return None, None


def _map_feature_to_cf(
    feature: str,
    cf_info_map: Dict[str, Dict[str, object]],
) -> Optional[str]:
    normalized_feature = _normalize_text(feature)

    for pattern, cf_code in FEATURE_TO_CF_PATTERNS:
        if re.search(pattern, normalized_feature, re.IGNORECASE):
            return cf_code

    for cf_code, info in cf_info_map.items():
        label = str(info.get("label") or "")
        normalized_label = _normalize_text(label)
        if normalized_feature and (
            normalized_feature in normalized_label or normalized_label in normalized_feature
        ):
            return cf_code

    return None


def extract_row_name_to_cf_map(
    crop_details_dir: Path = CROP_DETAILS_DIR,
) -> Dict[str, Optional[str]]:
    cf_info_map = build_cf_info_map()
    row_to_cf: Dict[str, Optional[str]] = {}

    for csv_path in sorted(crop_details_dir.glob("*.csv")):
        if csv_path.name.startswith("0.List"):
            continue

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            records = list(reader)

        if not records:
            continue

        for row in records[1:]:
            if not row:
                continue

            parameter = (row[0] or "").strip()
            row_type, feature = _extract_feature(parameter)
            if not row_type or not feature:
                continue

            cf_code = _map_feature_to_cf(feature, cf_info_map)

            if parameter not in row_to_cf:
                row_to_cf[parameter] = cf_code
                continue

            existing = row_to_cf.get(parameter)
            if existing is None and cf_code is not None:
                row_to_cf[parameter] = cf_code

    return row_to_cf


def export_mapping_map(
    output_path: Optional[Path] = None,
    crop_details_dir: Path = CROP_DETAILS_DIR,
) -> Path:
    output_path = output_path or (crop_details_dir / "sensitivity_demand_row_to_cf_map.json")
    row_to_cf = extract_row_name_to_cf_map(crop_details_dir)

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(row_to_cf, handle, ensure_ascii=False, indent=2)

    return output_path


def main() -> None:
    output = export_mapping_map()
    print(f"Row-name to CF map exported to: {output}")


if __name__ == "__main__":
    main()
