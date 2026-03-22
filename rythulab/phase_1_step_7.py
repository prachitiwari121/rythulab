from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rythulab.sheets.cf_label_extract import build_cf_info_map
    from rythulab.sheets.crop_details.extract_sensitivity_demand_cf_map import extract_row_name_to_cf_map
except ModuleNotFoundError:
    import sys

    sheets_dir = Path(__file__).resolve().parent / "sheets"
    crop_details_dir = sheets_dir / "crop_details"
    sys.path.append(str(sheets_dir))
    sys.path.append(str(crop_details_dir))

    from cf_label_extract import build_cf_info_map
    from extract_sensitivity_demand_cf_map import extract_row_name_to_cf_map


CROP_DETAILS_DIR = Path(__file__).resolve().parent / "sheets" / "crop_details"
LIST_FILE = CROP_DETAILS_DIR / "0.List of All crops - Sheet1.csv"

SENSITIVITY_RE = re.compile(r"^\s*sensit(?:ive|ivity)\s+to\s+", re.IGNORECASE)
DEMAND_RE = re.compile(r"demand\s+class", re.IGNORECASE)
CF_CODE_RE = re.compile(r"^(CF\d+)", re.IGNORECASE)


def _norm(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_high(value: Any) -> bool:
    normalized = _norm(str(value or ""))
    return normalized in {"high", "very high"}


def _status_leq_moderate(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, (int, float)):
        return float(value) <= 3

    text = _norm(str(value))
    if not text:
        return False

    moderate_tokens = ["very weak", "weak", "moderate", "medium"]
    return any(token in text for token in moderate_tokens)


def _extract_cf_number(cf_key: str) -> Optional[str]:
    match = CF_CODE_RE.match(str(cf_key or "").strip().upper())
    return match.group(1) if match else None


def _load_cropid_to_name_map() -> Dict[str, str]:
    if not LIST_FILE.exists():
        raise FileNotFoundError(f"Crop list sheet not found: {LIST_FILE}")

    mapping: Dict[str, str] = {}
    with LIST_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            crop_id = str(row.get("CropID") or "").strip()
            crop_name = str(row.get("Crop Name") or "").strip()
            if crop_id and crop_name:
                mapping[crop_id] = crop_name

    return mapping


def _find_crop_column_by_id(crop_id: str) -> tuple[Path, str]:
    target = crop_id.strip().upper()

    for csv_path in sorted(CROP_DETAILS_DIR.glob("*.csv")):
        if csv_path.name.startswith("0.List"):
            continue

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)

        if not rows:
            continue

        # Find the CropID row
        cropid_row = next(
            (r for r in rows if r and _norm(str(r[0])) == "cropid"),
            None,
        )
        if cropid_row is None:
            continue

        headers = rows[0]
        for col_idx, cell in enumerate(cropid_row[1:], start=1):
            if str(cell or "").strip().upper() == target:
                return csv_path, headers[col_idx]

    raise ValueError(f"CropID '{crop_id}' not found in crop detail matrices")


def _extract_farm_cf_status(cf_code: str, farm_cfs: Dict[str, Any], cf_label: str) -> Any:
    cf_code = str(cf_code or "").upper().strip()
    candidates: List[Any] = []

    for key, value in (farm_cfs or {}).items():
        key_text = str(key or "").strip()
        key_cf = _extract_cf_number(key_text)

        if key_cf == cf_code or _norm(key_text) == _norm(cf_label):
            candidates.append(value)

    for candidate in candidates:
        if isinstance(candidate, dict):
            if candidate.get("slab") not in (None, ""):
                return candidate.get("slab")
            if candidate.get("status") not in (None, ""):
                return candidate.get("status")
            if candidate.get("s") not in (None, ""):
                return candidate.get("s")
            if candidate.get("val") not in (None, ""):
                return candidate.get("val")
        else:
            return candidate

    return None


def check_resource_pressure(crop_id: str, farm_cfs: Dict[str, Any]) -> Dict[str, Any]:
    if not crop_id:
        raise ValueError("crop_id must not be empty")

    cropid_to_name = _load_cropid_to_name_map()
    crop_name = cropid_to_name.get(crop_id, crop_id)

    matrix_path, crop_column = _find_crop_column_by_id(crop_id)
    row_to_cf_map = extract_row_name_to_cf_map(CROP_DETAILS_DIR)
    cf_info_map = build_cf_info_map()

    extracted: Dict[str, Dict[str, Any]] = {}

    with matrix_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parameter = str(row.get("Parameter") or "").strip()
            if not parameter:
                continue

            if not (SENSITIVITY_RE.search(parameter) or DEMAND_RE.search(parameter)):
                continue

            cf_code = row_to_cf_map.get(parameter)
            if not cf_code:
                continue

            value = row.get(crop_column)
            bucket = extracted.setdefault(cf_code, {"sensitivity": None, "demand": None})

            if SENSITIVITY_RE.search(parameter):
                bucket["sensitivity"] = value
            if DEMAND_RE.search(parameter):
                bucket["demand"] = value

    warnings: List[Dict[str, Any]] = []

    for cf_code, values in extracted.items():
        sensitivity = values.get("sensitivity")
        demand = values.get("demand")

        if not (_is_high(sensitivity) and _is_high(demand)):
            continue

        cf_label = str((cf_info_map.get(cf_code) or {}).get("label") or cf_code)
        farm_status = _extract_farm_cf_status(cf_code, farm_cfs, cf_label)

        if not _status_leq_moderate(farm_status):
            continue

        warnings.append(
            {
                "cf_code": cf_code,
                "cf_label": cf_label,
                "sensitivity": sensitivity,
                "demand": demand,
                "farm_cf_status": farm_status,
                "message": (
                    f"{crop_name}: {cf_label} has high sensitivity ({sensitivity}) and "
                    f"high demand ({demand}), while farm CF status is {farm_status} (<= Moderate)."
                ),
            }
        )

    return {
        "crop_id": crop_id,
        "crop_name": crop_name,
        "warning_count": len(warnings),
        "warnings": warnings,
        "has_warning": len(warnings) > 0,
    }


if __name__ == "__main__":
    sample_crop_id = "CRP0058"  # Tomato
    sample_farm_cfs = {
        "CF1": {"slab": "Moderate", "s": 3},
        "CF2": {"slab": "Weak", "s": 2},
        "CF3": {"slab": "Moderate", "s": 3},
        "CF9": {"slab": "Weak", "s": 2},
        "CF14": {"slab": "Moderate", "s": 3},
        "CF17": {"slab": "Moderate", "s": 3},
    }

    sample_result = check_resource_pressure(sample_crop_id, sample_farm_cfs)
    print(json.dumps(sample_result, indent=2, ensure_ascii=False))
