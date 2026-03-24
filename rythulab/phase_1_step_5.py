"""
Phase 1 Step 5 — Crop Characteristics Extractor
Reads agronomic characteristics for each crop from the crop detail matrix CSVs
and returns them keyed by crop ID, shaped to exactly match cs_s5 frontend fields.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_DETAILS_DIR = SHEETS_DIR / "crop_details"
PEST_CSV = SHEETS_DIR / "Pests" / "AP_Disease_CF_MF_Triggers_filled - AP_Pest_CF_MF_Triggers.csv"

# All crop detail matrix files in order
CROP_DETAIL_FILES = [
    "1.Cereals_and_Millets_Crop_Matrix - Sheet1.csv",
    "2.Pulse_Crop_Matrix_Complete - Sheet1.csv",
    "3.Oilseed_Crop_Matrix_Complete - Sheet1.csv",
    "4.Leafy_and_Vegetable_Matrix - Sheet1.csv",
    "5. Vegetables_Crop_Matrix - Sheet1.csv",
    "6.Commercial_and_Spices_Matrix_Complete - Sheet1.csv",
    "7.Plantation_and_Spice_Crops_Matrix - Sheet1.csv",
    "8.Gourds_Melons_and_Roots_Matrix - Sheet1.csv",
    "9.Fruit_and_Plantation_Crops_Matrix - Sheet1.csv",
    "10.Forage_Crops_Matrix - Sheet1.csv",
    "11.Medicinal_and_Aromatic_Crops_Matrix - Sheet1.csv",
]

# Maps an internal key -> regex pattern to match against the CSV "Parameter" column.
# Order matters: more specific patterns before broader ones.
_ROW_PATTERNS: List[tuple[str, re.Pattern]] = [
    # Temperature
    ("temp",         re.compile(r"threshold level of temperature", re.IGNORECASE)),
    # pH range
    ("pH_r",         re.compile(r"threshold level of ph\b", re.IGNORECASE)),
    # Rain reliability (best available proxy for humidity requirement)
    ("hum",          re.compile(r"rain reliability", re.IGNORECASE)),
    # Root depth class (used for display as rootD AND computation as rd)
    ("rootD",        re.compile(r"root depth class", re.IGNORECASE)),
    # Crop height — numeric value string like "0.5 - 1.5 m"
    ("h_str",        re.compile(r"crop height meters\s*\(value\)", re.IGNORECASE)),
    # Canopy spread — value string like "0.3 - 0.5 m"
    ("cSpread",      re.compile(r"canopy spread\s+meters\s*\(value\)", re.IGNORECASE)),
    # Canopy nature (density class: Dense / Medium / Sparse …)
    ("cNature",      re.compile(r"canopy density", re.IGNORECASE)),
    # Growth habit
    ("gHabit",       re.compile(r"growth habit", re.IGNORECASE)),
    # Per-parameter sensitivity rows — used to build `crit` (High/Very High only)
    ("sens_nitrogen",     re.compile(r"sensitivity to nitrogen", re.IGNORECASE)),
    ("sens_phosphorus",   re.compile(r"sensitivity to phosphorus", re.IGNORECASE)),
    ("sens_potassium",    re.compile(r"sensitivity to potassium", re.IGNORECASE)),
    ("sens_organic",      re.compile(r"sensitivity to organic carbon", re.IGNORECASE)),
    ("sens_ec",           re.compile(r"sensitivity to ec", re.IGNORECASE)),
    ("sens_texture",      re.compile(r"sensitivity to texture", re.IGNORECASE)),
    ("sens_depth",        re.compile(r"sensitivity to depth", re.IGNORECASE)),
    ("sens_whc",          re.compile(r"sensitivity to water holding capacity", re.IGNORECASE)),
    ("sens_compaction",   re.compile(r"sensitivity to compaction", re.IGNORECASE)),
    ("sens_drainage",     re.compile(r"sensitivity to drainage", re.IGNORECASE)),
    ("sens_erosion",      re.compile(r"sensitivity to erosion", re.IGNORECASE)),
    ("sens_groundwater",  re.compile(r"sensitivity to groundwater depth", re.IGNORECASE)),
    ("sens_irrigation",   re.compile(r"sensitivity to irrigation", re.IGNORECASE)),
    ("sens_rain",         re.compile(r"sensitivity to rain", re.IGNORECASE)),
    ("sens_pest",         re.compile(r"sensitivity to pest pressure", re.IGNORECASE)),
    ("sens_earthworm",    re.compile(r"sensitivity to earthworm", re.IGNORECASE)),
    ("sens_slope",        re.compile(r"sensitivity to slope", re.IGNORECASE)),
    ("sens_calcium",      re.compile(r"sensitivity to calcium", re.IGNORECASE)),
    ("sens_bulk",         re.compile(r"sensitivity to bulk density", re.IGNORECASE)),
    # Crop functional group — used to derive N-fixation
    ("func_group",   re.compile(r"crop functional group", re.IGNORECASE)),
    # Wind tolerance threshold
    ("windTol",      re.compile(r"threshold level of wind speed", re.IGNORECASE)),
    # Salinity / EC threshold
    ("sal",          re.compile(r"threshold level of electrical conductivity", re.IGNORECASE)),
    # Crop family
    ("family",       re.compile(r"crop family name", re.IGNORECASE)),
    # Major pests (raw string with PEST IDs)
    ("pests_raw",    re.compile(r"mention 5 major pests", re.IGNORECASE)),
    # Frost suitability (for frostSens display)
    ("frostSens",    re.compile(r"crop suitability under frost risk", re.IGNORECASE)),
    # Nitrogen demand class — mapped to c.res for resource pressure step
    ("res",          re.compile(r"nitrogen demand class", re.IGNORECASE)),
    # Sensitivity fields
    ("sens_ph",      re.compile(r"sensitivity to ph\b", re.IGNORECASE)),
    ("sens_temp",    re.compile(r"sensitivity to temperature", re.IGNORECASE)),
    ("sens_heat",    re.compile(r"sensitivity to heat days", re.IGNORECASE)),
    ("sens_frost",   re.compile(r"sensitivity to frost", re.IGNORECASE)),
    ("sens_airflow", re.compile(r"sensitivity to wind", re.IGNORECASE)),
    ("sens_subm",    re.compile(r"sensitivity to flood risk", re.IGNORECASE)),
    ("sens_extreme", re.compile(r"sensitivity to drought risk", re.IGNORECASE)),
]

# Build a set of internal keys for fast lookup
_ALL_KEYS = {k for k, _ in _ROW_PATTERNS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_pest_map(pest_csv: Path = PEST_CSV) -> Dict[str, str]:
    """Return {PestID -> Pest name} from the pest triggers CSV."""
    mapping: Dict[str, str] = {}
    if not pest_csv.exists():
        return mapping
    with pest_csv.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pest_id = (row.get("PestID") or "").strip()
            pest_name = (row.get("Pest") or "").strip()
            if pest_id and pest_name:
                mapping[pest_id] = pest_name
    return mapping


def _parse_pest_string(raw: str, pest_map: Dict[str, str]) -> List[str]:
    """Parse 'PEST0001 (High), PEST0002 (Medium)' → ['Stem Borer (High)', …]."""
    if not raw:
        return []
    result = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        m = re.match(r"^(PEST\d+)\s*(?:\(([^)]*)\))?", chunk)
        if not m:
            continue
        pest_id = m.group(1)
        severity = (m.group(2) or "").strip()
        name = pest_map.get(pest_id, pest_id)
        # Split off the scientific name for brevity: "Stem Borer (Scirpophaga incertulas)" → "Stem Borer"
        common = name.split("(")[0].strip()
        result.append(f"{common} ({severity})" if severity else common)
    return result


def _h_midpoint(height_str: str) -> float:
    """Extract the numeric midpoint from '0.5 - 1.5 m' → 1.0."""
    nums = re.findall(r"\d+\.?\d*", height_str or "")
    if not nums:
        return 0.0
    vals = [float(n) for n in nums]
    return round(sum(vals) / len(vals), 2)


def _derive_n_fix(func_group: str) -> str:
    """Return 'Yes' if the crop's functional group suggests N-fixation."""
    fg = (func_group or "").lower()
    if any(kw in fg for kw in ("legume", "pulse", "n-fix", "nitrogen fix", "bean", "gram")):
        return "Yes"
    return "No"


def _match_row_key(param: str) -> Optional[str]:
    """Return the first internal key whose pattern matches `param`, or None."""
    for key, pattern in _ROW_PATTERNS:
        if pattern.search(param):
            return key
    return None


# Ordered list of (internal_key, short_label) for all sensitivity parameters.
# Used by _derive_crit to build the "High" sensitivity parameter list.
_SENS_LABELS: List[tuple[str, str]] = [
    ("sens_nitrogen",   "Nitrogen"),
    ("sens_phosphorus", "Phosphorus"),
    ("sens_potassium",  "Potassium"),
    ("sens_organic",    "Organic Carbon"),
    ("sens_ph",         "Soil pH"),
    ("sens_ec",         "Salinity/EC"),
    ("sens_texture",    "Soil Texture"),
    ("sens_depth",      "Soil Depth"),
    ("sens_whc",        "Water Holding Capacity"),
    ("sens_compaction", "Compaction"),
    ("sens_drainage",   "Drainage"),
    ("sens_erosion",    "Erosion"),
    ("sens_groundwater","Groundwater Depth"),
    ("sens_irrigation", "Irrigation"),
    ("sens_rain",       "Rain Reliability"),
    ("sens_temp",       "Temperature"),
    ("sens_heat",       "Heat Days"),
    ("sens_frost",      "Frost"),
    ("sens_airflow",    "Wind"),
    ("sens_subm",       "Flood Risk"),
    ("sens_extreme",    "Drought Risk"),
    ("sens_calcium",    "Calcium"),
    ("sens_bulk",       "Bulk Density"),
    ("sens_pest",       "Pest Pressure"),
    ("sens_earthworm",  "Earthworm Activity"),
    ("sens_slope",      "Slope"),
]

_HIGH_SENS = {"high", "very high"}


def _derive_crit(data: Dict[str, str]) -> str:
    """Return a comma-separated list of parameters where sensitivity is High or Very High."""
    labels = [
        label
        for key, label in _SENS_LABELS
        if data.get(key, "").strip().lower() in _HIGH_SENS
    ]
    return ", ".join(labels)


def _clean_value(val: str) -> str:
    """Strip extra whitespace/newlines from a cell value."""
    return re.sub(r"\s+", " ", (val or "").strip())


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def get_crop_characteristics(crop_ids: List[str]) -> Dict[str, dict]:
    """
    Given a list of crop IDs (e.g. ['CRP0001', 'CRP0003']), read every crop
    detail matrix CSV and return a dict:

        {
            "CRP0001": {
                "temp": "20 - 35 °C",
                "pH_r": "5.0 - 7.0",
                "hum":  "High",
                "rootD": "Medium",
                "rd":    "Medium",      # alias used by _ck9
                "h":    1.0,            # numeric midpoint, used by _ck9
                "cSpread": "0.3 - 0.5 m",
                "cNature": "Dense",
                "gHabit":  "Erect",
                "crit":    "Nitrogen, Soil pH, Temperature",  # params with High/Very High sensitivity
                "alelo":   "No",
                "nFix":    "No",
                "shadeTol": 0,
                "windTol": "< 15 kmph",
                "sal":     "< 2.0 ds/m",
                "family":  "Poaceae",
                "pests":   ["Stem Borer (High)", "Brown Plant Hopper (High)"],
                "frostSens": "Low",
                "res":       "High",    # nitrogen/resource demand
                "sens": {
                    "ph": "High", "temp": "High", "water": "High",
                    "heat": "High", "frost": "Low", "airflow": "Low",
                    "subm": "Very High", "extreme": "Low"
                }
            },
            ...
        }
    """
    target_ids = {c.strip().upper() for c in crop_ids if c}
    if not target_ids:
        return {}

    pest_map = _build_pest_map()
    result: Dict[str, dict] = {}
    remaining = set(target_ids)  # stop scanning files once all crops found

    for filename in CROP_DETAIL_FILES:
        if not remaining:
            break
        path = CROP_DETAILS_DIR / filename
        if not path.exists():
            continue

        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))

        if not rows:
            continue

        # Find "CropID" row → build column_idx -> crop_id map
        cropid_row: Optional[list] = None
        for row in rows:
            if row and _clean_value(row[0]) == "CropID":
                cropid_row = row
                break
        if not cropid_row:
            continue

        # col_map: crop_id -> column index in this file
        col_map: Dict[str, int] = {}
        for idx, cell in enumerate(cropid_row):
            cid = _clean_value(cell).upper()
            if cid in remaining:
                col_map[cid] = idx

        if not col_map:
            continue  # no target crops in this file

        # Accumulate raw field values per crop for this file
        raw: Dict[str, Dict[str, str]] = {cid: {} for cid in col_map}

        for row in rows:
            if not row:
                continue
            param = _clean_value(row[0])
            key = _match_row_key(param)
            if key is None:
                continue
            for cid, idx in col_map.items():
                if key not in raw[cid]:  # first match wins (more specific patterns first)
                    val = _clean_value(row[idx]) if idx < len(row) else ""
                    raw[cid][key] = val

        # Build structured output for each matched crop
        for cid, data in raw.items():
            fg = data.get("func_group", "")
            result[cid] = {
                "temp":     data.get("temp", ""),
                "pH_r":     data.get("pH_r", ""),
                "hum":      data.get("hum", ""),
                "rootD":    data.get("rootD", ""),
                "rd":       data.get("rootD", ""),   # alias for _ck9
                "h":        _h_midpoint(data.get("h_str", "")),
                "cSpread":  data.get("cSpread", ""),
                "cNature":  data.get("cNature", ""),
                "gHabit":   data.get("gHabit", ""),
                "crit":     _derive_crit(data),
                "alelo":    "No",                    # not in current sheets
                "nFix":     _derive_n_fix(fg),
                "shadeTol": 0,                       # not in current sheets
                "windTol":  data.get("windTol", ""),
                "sal":      data.get("sal", ""),
                "family":   data.get("family", ""),
                "pests":    _parse_pest_string(data.get("pests_raw", ""), pest_map),
                "frostSens": data.get("frostSens", ""),
                "res":      data.get("res", ""),
                "sens": {
                    "ph":      data.get("sens_ph", ""),
                    "temp":    data.get("sens_temp", ""),
                    "water":   data.get("sens_whc", ""),
                    "heat":    data.get("sens_heat", ""),
                    "frost":   data.get("sens_frost", ""),
                    "airflow": data.get("sens_airflow", ""),
                    "subm":    data.get("sens_subm", ""),
                    "extreme": data.get("sens_extreme", ""),
                },
            }
            remaining.discard(cid)

    return result
