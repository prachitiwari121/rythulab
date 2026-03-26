"""
IEF Calculation — Irrigation / Environmental Fitness Score
Given a set of crop IDs (and an optional farm CF context), returns an IEF
value in [0.6, 1.0].  Lower IEF means the combination uses resources more
efficiently; higher means more stress/competition in the system.

Algorithm
---------
IEF starts at 0.9.

Step 2 — positive contributions (efficiency gains, subtract from IEF):
  MF1 (Shade Medium)          : -0.05
  MF2 (Shade Dense)           : -0.10
  MF9 (Water Retention)       : -0.05
  MF8 (Evaporation Reduction) : -0.05
  MF17 (Organic Matter Add)   : -0.05
  ≥ 2 distinct height classes : -0.05  (root / canopy complementarity)
  ≥ 3 distinct height classes : -0.10  (strong complementarity — replaces -0.05)

Step 3 — negative contributions (inefficiency, add to IEF):
  ≥ 2 crops with High/Very High water demand    : +0.10
  Any height class shared by ≥ 2 crops          : +0.05
  CF9 (WHC) is Weak / Very Weak                 : +0.05

Step 4 — bound:
  IEF = max(0.6, min(IEF, 1.0))
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from crop_micro_feature_extract import get_produced_micro_features_by_cropid
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
    from crop_micro_feature_extract import get_produced_micro_features_by_cropid

# Returned value is Dict[str, List[str]]  (crop_id -> [MF codes])
# Populated lazily in _load_crop_data()
_PRODUCED_MF_MAP: Optional[Dict[str, List[str]]] = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_DETAILS_DIR = SHEETS_DIR / "crop_details"

# ---------------------------------------------------------------------------
# Height-class ordinals (shared convention across phase files)
# ---------------------------------------------------------------------------
HEIGHT_CLASS_ORDER: Dict[str, int] = {
    "EXTRA LOW": 1,
    "LOW": 2,
    "MEDIUM LOW": 3,
    "MEDIUM": 4,
    "TALL": 5,
    "VERY TALL": 6,
}
HEIGHT_CLASS_LABEL: Dict[int, str] = {v: k.title() for k, v in HEIGHT_CLASS_ORDER.items()}

# ---------------------------------------------------------------------------
# In-memory caches (populated lazily on first call)
# ---------------------------------------------------------------------------
_CROP_HEIGHTS: Dict[str, int] = {}       # CropID -> height class ordinal
_CROP_WATER_DEMAND: Dict[str, str] = {}  # CropID -> "LOW" | "MEDIUM" | "HIGH" | "VERY HIGH"
_PRODUCED_MF_MAP: Optional[Dict[str, List[str]]] = None  # full produced-MF map
_DATA_LOADED: bool = False


def _load_crop_data() -> None:
    """Read all matrix CSVs once and populate height and water-demand caches.
    Also loads the produced-MF map."""
    global _DATA_LOADED, _PRODUCED_MF_MAP
    if _DATA_LOADED:
        return
    _DATA_LOADED = True

    # Load MF produced map (returns Dict[str, List[str]])
    _PRODUCED_MF_MAP = get_produced_micro_features_by_cropid()

    if not CROP_DETAILS_DIR.exists():
        return

    for csv_path in sorted(CROP_DETAILS_DIR.glob("*.csv")):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))

        if len(rows) < 2:
            continue

        cropid_row: Optional[List[str]] = None
        height_class_row: Optional[List[str]] = None
        water_demand_row: Optional[List[str]] = None

        for row in rows:
            if not row:
                continue
            first = str(row[0]).strip().upper()
            if first == "CROPID":
                cropid_row = row
            elif first.startswith("CROP HEIGHT CLASS"):
                height_class_row = row
            elif "WATER DEMAND CLASS" in first:
                water_demand_row = row

        if not cropid_row:
            continue

        if height_class_row:
            for idx in range(1, min(len(cropid_row), len(height_class_row))):
                cid = str(cropid_row[idx]).strip().upper()
                raw = str(height_class_row[idx]).strip().upper()
                if cid and raw in HEIGHT_CLASS_ORDER:
                    _CROP_HEIGHTS[cid] = HEIGHT_CLASS_ORDER[raw]

        if water_demand_row:
            for idx in range(1, min(len(cropid_row), len(water_demand_row))):
                cid = str(cropid_row[idx]).strip().upper()
                raw = str(water_demand_row[idx]).strip().upper()
                if cid and raw:
                    _CROP_WATER_DEMAND[cid] = raw


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_ief(
    crop_ids: List[str],
    farm_cf: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Compute the IEF score for a set of crop IDs.

    Args:
        crop_ids: List of crop IDs, e.g. ["CRP0001", "CRP0002"].
        farm_cf:  Optional dict of farm context factors.
                  Recognises "CF9" or "CF9_WHC" for water holding capacity.
                  Values like "Weak" or "Very Weak" trigger the WHC penalty.

    Returns:
        {
            "ief": float,                  # bounded to [0.6, 1.0]
            "adjustments": [               # every applied delta with a reason
                {"delta": float, "reason": str},
                ...
            ]
        }
    """
    _load_crop_data()

    ief: float = 0.9
    adjustments: List[Dict[str, Any]] = []

    normalized_ids = [cid.strip().upper() for cid in crop_ids]

    # ------------------------------------------------------------------
    # Step 2 — positive contributions
    # ------------------------------------------------------------------

    # Collect all MF codes produced by any crop in the selection
    all_produced: set[str] = set()
    produced_map = _PRODUCED_MF_MAP or {}
    for cid in normalized_ids:
        all_produced.update(produced_map.get(cid, []))

    # Shade / microclimate
    if "MF1" in all_produced:
        ief -= 0.05
        adjustments.append({"delta": -0.05, "reason": "MF1 (Shade Medium) present — reduces thermal stress"})

    if "MF2" in all_produced:
        ief -= 0.10
        adjustments.append({"delta": -0.10, "reason": "MF2 (Shade Dense) present — strong microclimate benefit"})

    # Soil moisture
    if "MF9" in all_produced:
        ief -= 0.05
        adjustments.append({"delta": -0.05, "reason": "MF9 (Water Retention) present — improves soil moisture"})

    if "MF8" in all_produced:
        ief -= 0.05
        adjustments.append({"delta": -0.05, "reason": "MF8 (Evaporation Reduction) present — reduces water loss"})

    # Soil health
    if "MF17" in all_produced:
        ief -= 0.05
        adjustments.append({"delta": -0.05, "reason": "MF17 (Organic Matter Addition) present — improves soil health"})

    # Root / canopy complementarity (height class diversity)
    crop_height_classes: Dict[str, int] = {
        cid: _CROP_HEIGHTS[cid]
        for cid in normalized_ids
        if cid in _CROP_HEIGHTS
    }
    distinct_classes = set(crop_height_classes.values())
    n_classes = len(distinct_classes)

    if n_classes >= 3:
        ief -= 0.10
        adjustments.append({
            "delta": -0.10,
            "reason": f"Crops span {n_classes} distinct height classes — strong root/canopy complementarity",
        })
    elif n_classes >= 2:
        ief -= 0.05
        adjustments.append({
            "delta": -0.05,
            "reason": f"Crops span {n_classes} distinct height classes — moderate root/canopy complementarity",
        })

    # ------------------------------------------------------------------
    # Step 3 — negative contributions
    # ------------------------------------------------------------------

    # High water demand clustering
    high_water_crops = [
        cid for cid in normalized_ids
        if _CROP_WATER_DEMAND.get(cid) in ("HIGH", "VERY HIGH")
    ]
    if len(high_water_crops) >= 2:
        ief += 0.10
        adjustments.append({
            "delta": 0.10,
            "reason": (
                f"{len(high_water_crops)} crops have High/Very High water demand "
                f"({', '.join(high_water_crops)}) — competition risk"
            ),
        })

    # Same height-class competition
    class_counts = Counter(crop_height_classes.values())
    shared_classes = [
        HEIGHT_CLASS_LABEL.get(cls, str(cls))
        for cls, cnt in class_counts.items()
        if cnt >= 2
    ]
    if shared_classes:
        ief += 0.05
        adjustments.append({
            "delta": 0.05,
            "reason": (
                f"Multiple crops share height class(es) {shared_classes} — "
                "same-layer competition risk"
            ),
        })

    # CF9 WHC penalty
    if farm_cf:
        cf9_raw = (
            farm_cf.get("CF9") or farm_cf.get("CF9_WHC") or ""
        ).strip().upper()
        if cf9_raw in ("WEAK", "VERY WEAK", "LOW", "VERY LOW"):
            ief += 0.05
            adjustments.append({
                "delta": 0.05,
                "reason": f"CF9 WHC is '{cf9_raw.title()}' — poor soil water holding capacity",
            })

    # ------------------------------------------------------------------
    # Step 4 — bound
    # ------------------------------------------------------------------
    ief = round(max(0.6, min(ief, 1.0)), 4)

    return {
        "ief": ief,
        "adjustments": adjustments,
    }


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    # Sample 1: eco-efficient mix — tall shade crop (Silver Oak) over ground crop (Ginger)
    # Expected: MF2 shade (-0.10), height diversity (-0.05 or -0.10), moderate WHC
    sample1_ids = ["CRP0103", "CRP0032", "CRP0002"]
    result1 = calculate_ief(sample1_ids, farm_cf={"CF9": "Moderate"})
    print("=== Sample 1: Eco-efficient mix ===")
    print(json.dumps(result1, indent=2))

    # Sample 2: competing pair — two high-water cereals, same height class, weak WHC
    # Expected: high water penalty (+0.10), same-layer penalty (+0.05), WHC penalty (+0.05)
    sample2_ids = ["CRP0001", "CRP0003"]  # Paddy + Jowar (both Medium Low, Paddy=Very High water)
    result2 = calculate_ief(sample2_ids, farm_cf={"CF9": "Weak"})
    print("\n=== Sample 2: Competing cereals ===")
    print(json.dumps(result2, indent=2))

    # Sample 3: maximal positive contributions
    # Silver Oak (MF2 shade, Tall) + Ginger (MF8/MF9 likely, Extra Low) + Paddy (Very High water)
    sample3_ids = ["CRP0103", "CRP0032", "CRP0031", "CRP0007"]
    result3 = calculate_ief(sample3_ids)
    print("\n=== Sample 3: Multi-crop diversity (no CF9 passed) ===")
    print(json.dumps(result3, indent=2))
