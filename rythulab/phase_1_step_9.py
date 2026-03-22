from __future__ import annotations

import csv
import re
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_DETAILS_DIR = SHEETS_DIR / "crop_details"
CROP_LIST_PATH = CROP_DETAILS_DIR / "0.List of All crops - Sheet1.csv"

# ---------------------------------------------------------------------------
# Competition threshold sets
# ---------------------------------------------------------------------------

_MEDIUM_DENSE_CANOPY = {"medium", "dense", "very dense"}
_WIDE_CANOPY_SPREAD = {"wide", "very wide"}
_WIDE_ROOT_SPREAD = {"medium", "wide", "very wide"}
_HIGH_DEMAND = {"high", "very high"}
_PEST_SEVERITY_MEDIUM_HIGH = {"medium", "high"}

_DEMAND_RESOURCES: List[tuple] = [
    ("water_demand_class", "Water"),
    ("nitrogen_demand_class", "Nitrogen"),
    ("phosphorus_demand_class", "Phosphorus"),
    ("potassium_demand_class", "Potassium"),
    ("calcium_demand_class", "Calcium"),
]

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _n(value: Any) -> str:
    """Normalise to lowercase, stripped string."""
    return str(value or "").strip().lower()


def _parse_pests(raw: str) -> Dict[str, str]:
    """
    Parse   'Stem Borer (High), Brown Plant Hopper (High), Leaf Folder (Medium), ...'
    into    {'stem borer': 'high', 'brown plant hopper': 'high', ...}
    """
    raw = (raw or "").strip()
    if not raw or _n(raw) in {"no", "n/a", "none", "-"}:
        return {}

    pests: Dict[str, str] = {}
    for token in raw.split(","):
        token = token.strip()
        m = re.match(r"^(.+?)\s*\((\w+)\)\s*$", token)
        if m:
            name = m.group(1).strip().lower()
            severity = m.group(2).strip().lower()
            pests[name] = severity
    return pests


def _shared_pests_medium_high(
    pests_a: Dict[str, str], pests_b: Dict[str, str]
) -> List[str]:
    """Return pest names where both crops have medium or high severity."""
    return [
        name
        for name, sev_a in pests_a.items()
        if sev_a in _PEST_SEVERITY_MEDIUM_HIGH
        and pests_b.get(name, "") in _PEST_SEVERITY_MEDIUM_HIGH
    ]


# ---------------------------------------------------------------------------
# CSV loading — crop attributes
# ---------------------------------------------------------------------------

_ATTR_MATCHERS = [
    ("height_class", lambda p: "crop height class" in p),
    ("canopy_density", lambda p: "canopy density" in p),
    (
        "canopy_spread_class",
        lambda p: "canopy spread" in p and "meter" not in p and "(value)" not in p,
    ),
    ("growth_habit", lambda p: "growth habit" in p),
    ("root_depth_class", lambda p: "root depth class" in p),
    (
        "root_spread_class",
        lambda p: "root spread" in p and "meter" not in p and "(value)" not in p,
    ),
    ("growth_duration_class", lambda p: "growth duration class" in p),
    (
        "water_demand_class",
        lambda p: "water demand" in p and "class" in p,
    ),
    ("nitrogen_demand_class", lambda p: "nitrogen demand" in p and "class" in p),
    ("phosphorus_demand_class", lambda p: "phosphorus demand" in p and "class" in p),
    (
        "potassium_demand_class",
        lambda p: ("potasium demand" in p or "potassium demand" in p) and "class" in p,
    ),
    ("calcium_demand_class", lambda p: "calcium demand" in p and "class" in p),
    ("major_pests_raw", lambda p: "major pests" in p),
]


def _find_attr_key(param: str) -> Optional[str]:
    param_lower = param.lower()
    for attr_key, matcher in _ATTR_MATCHERS:
        if matcher(param_lower):
            return attr_key
    return None


def _parse_crop_matrix(path: Path, out: Dict[str, Dict[str, str]]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))

    if not rows:
        return

    # Find the CropID row
    cropid_row: Optional[List[str]] = None
    for row in rows:
        if row and _n(row[0]) == "cropid":
            cropid_row = row
            break

    if cropid_row is None:
        return

    # Map column index -> CropID
    col_to_cid: Dict[int, str] = {}
    for col_idx, val in enumerate(cropid_row[1:], start=1):
        cid = val.strip().upper()
        if cid:
            col_to_cid[col_idx] = cid

    if not col_to_cid:
        return

    for cid in col_to_cid.values():
        out.setdefault(cid, {})

    for row in rows:
        if not row:
            continue
        param = str(row[0] or "").strip()
        attr_key = _find_attr_key(param)
        if attr_key is None:
            continue
        for col_idx, cid in col_to_cid.items():
            if col_idx < len(row):
                out[cid][attr_key] = str(row[col_idx] or "").strip()


def _load_all_crop_attributes() -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    for csv_path in sorted(CROP_DETAILS_DIR.glob("*.csv")):
        if csv_path.name.startswith("0."):
            continue
        try:
            _parse_crop_matrix(csv_path, result)
        except Exception:
            pass
    return result


def _load_crop_label_map() -> Dict[str, str]:
    label_map: Dict[str, str] = {}
    if not CROP_LIST_PATH.exists():
        return label_map
    with CROP_LIST_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = str(row.get("CropID") or "").strip().upper()
            name = str(row.get("Crop Name") or "").strip()
            if cid:
                label_map[cid] = name
    return label_map


# ---------------------------------------------------------------------------
# Lazy-loaded module-level caches
# ---------------------------------------------------------------------------

_CROP_ATTRS: Optional[Dict[str, Dict[str, str]]] = None
_CROP_LABELS: Optional[Dict[str, str]] = None


def _get_crop_attrs() -> Dict[str, Dict[str, str]]:
    global _CROP_ATTRS
    if _CROP_ATTRS is None:
        _CROP_ATTRS = _load_all_crop_attributes()
    return _CROP_ATTRS


def _get_crop_labels() -> Dict[str, str]:
    global _CROP_LABELS
    if _CROP_LABELS is None:
        _CROP_LABELS = _load_crop_label_map()
    return _CROP_LABELS


def _crop_label(crop_id: str) -> str:
    return _get_crop_labels().get(crop_id.upper(), crop_id)


# ---------------------------------------------------------------------------
# Pairwise competition checks
# ---------------------------------------------------------------------------


def _make_warning(
    id_a: str,
    label_a: str,
    id_b: str,
    label_b: str,
    warning_type: str,
    message: str,
    **extra: Any,
) -> Dict[str, Any]:
    return {
        "crop_a_id": id_a,
        "crop_a_label": label_a,
        "crop_b_id": id_b,
        "crop_b_label": label_b,
        "warning_type": warning_type,
        "message": message,
        **extra,
    }


def _check_pair(
    id_a: str,
    label_a: str,
    attrs_a: Dict[str, str],
    id_b: str,
    label_b: str,
    attrs_b: Dict[str, str],
) -> List[Dict[str, Any]]:
    warnings: List[Dict[str, Any]] = []

    def warn(wtype: str, msg: str, **extra: Any) -> None:
        warnings.append(_make_warning(id_a, label_a, id_b, label_b, wtype, msg, **extra))

    # ------------------------------------------------------------------
    # 1. Light competition — same height class + both medium/dense canopy
    # ------------------------------------------------------------------
    height_a = _n(attrs_a.get("height_class"))
    height_b = _n(attrs_b.get("height_class"))
    density_a = _n(attrs_a.get("canopy_density"))
    density_b = _n(attrs_b.get("canopy_density"))

    if (
        height_a
        and height_a == height_b
        and density_a in _MEDIUM_DENSE_CANOPY
        and density_b in _MEDIUM_DENSE_CANOPY
    ):
        warn(
            "light_competition",
            (
                f"{label_a} and {label_b} share the same height class "
                f"({attrs_a['height_class']}) and both have "
                f"{attrs_a['canopy_density']}/{attrs_b['canopy_density']} canopy density "
                "— light competition likely."
            ),
            height_class=attrs_a.get("height_class"),
            canopy_density_a=attrs_a.get("canopy_density"),
            canopy_density_b=attrs_b.get("canopy_density"),
        )

    # ------------------------------------------------------------------
    # 2. Horizontal canopy competition — both wide canopy spread
    # ------------------------------------------------------------------
    spread_a = _n(attrs_a.get("canopy_spread_class"))
    spread_b = _n(attrs_b.get("canopy_spread_class"))

    if spread_a in _WIDE_CANOPY_SPREAD and spread_b in _WIDE_CANOPY_SPREAD:
        warn(
            "horizontal_canopy_competition",
            (
                f"{label_a} and {label_b} both have wide canopy spread "
                f"({attrs_a['canopy_spread_class']}/{attrs_b['canopy_spread_class']}) "
                "— horizontal canopy competition risk."
            ),
            canopy_spread_a=attrs_a.get("canopy_spread_class"),
            canopy_spread_b=attrs_b.get("canopy_spread_class"),
        )

    # ------------------------------------------------------------------
    # 3. Ground competition — both prostrate growth habit
    # ------------------------------------------------------------------
    habit_a = _n(attrs_a.get("growth_habit"))
    habit_b = _n(attrs_b.get("growth_habit"))

    if "prostrate" in habit_a and "prostrate" in habit_b:
        warn(
            "ground_competition",
            (
                f"{label_a} and {label_b} both have prostrate growth habit "
                "— ground competition risk."
            ),
            growth_habit_a=attrs_a.get("growth_habit"),
            growth_habit_b=attrs_b.get("growth_habit"),
        )

    # ------------------------------------------------------------------
    # 4. Root competition — same root depth class + both medium/wide root spread
    # ------------------------------------------------------------------
    root_depth_a = _n(attrs_a.get("root_depth_class"))
    root_depth_b = _n(attrs_b.get("root_depth_class"))
    root_spread_a = _n(attrs_a.get("root_spread_class"))
    root_spread_b = _n(attrs_b.get("root_spread_class"))

    if (
        root_depth_a
        and root_depth_a == root_depth_b
        and root_spread_a in _WIDE_ROOT_SPREAD
        and root_spread_b in _WIDE_ROOT_SPREAD
    ):
        warn(
            "root_competition",
            (
                f"{label_a} and {label_b} share the same root depth class "
                f"({attrs_a['root_depth_class']}) and both have "
                f"{attrs_a['root_spread_class']}/{attrs_b['root_spread_class']} root spread "
                "— root competition risk."
            ),
            root_depth_class=attrs_a.get("root_depth_class"),
            root_spread_a=attrs_a.get("root_spread_class"),
            root_spread_b=attrs_b.get("root_spread_class"),
        )

    # ------------------------------------------------------------------
    # 5. Temporal competition — same growth duration class
    # ------------------------------------------------------------------
    duration_a = _n(attrs_a.get("growth_duration_class"))
    duration_b = _n(attrs_b.get("growth_duration_class"))

    if duration_a and duration_a == duration_b:
        warn(
            "temporal_competition",
            (
                f"{label_a} and {label_b} share the same growth duration class "
                f"({attrs_a['growth_duration_class']}) "
                "— temporal competition (overlapping growing seasons)."
            ),
            growth_duration_class=attrs_a.get("growth_duration_class"),
        )

    # ------------------------------------------------------------------
    # 6. Resource competition — both high/very high demand for the same resource
    # ------------------------------------------------------------------
    for attr_key, resource_name in _DEMAND_RESOURCES:
        demand_a = _n(attrs_a.get(attr_key))
        demand_b = _n(attrs_b.get(attr_key))
        if demand_a in _HIGH_DEMAND and demand_b in _HIGH_DEMAND:
            warn(
                "resource_competition",
                (
                    f"{label_a} and {label_b} both have "
                    f"{attrs_a[attr_key]}/{attrs_b[attr_key]} {resource_name} demand "
                    f"— {resource_name} resource competition risk."
                ),
                resource=resource_name,
                demand_a=attrs_a.get(attr_key),
                demand_b=attrs_b.get(attr_key),
            )

    # ------------------------------------------------------------------
    # 7. Pest host overlap — shared major pests at medium/high severity
    # ------------------------------------------------------------------
    pests_a = _parse_pests(attrs_a.get("major_pests_raw") or "")
    pests_b = _parse_pests(attrs_b.get("major_pests_raw") or "")
    shared = _shared_pests_medium_high(pests_a, pests_b)

    if shared:
        pest_list = ", ".join(p.title() for p in sorted(shared))
        warn(
            "pest_host_overlap",
            (
                f"{label_a} and {label_b} share common major pests at medium/high severity: "
                f"{pest_list} — pest host overlap risk."
            ),
            shared_pests=shared,
        )

    return warnings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_crop_competition(crop_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Given a list of crop IDs, return all pairwise competition warnings.

    Each warning dict contains:
      crop_a_id, crop_a_label, crop_b_id, crop_b_label,
      warning_type, message
      ... plus type-specific fields (e.g. height_class, shared_pests, resource)

    warning_type values:
      light_competition, horizontal_canopy_competition, ground_competition,
      root_competition, temporal_competition, resource_competition, pest_host_overlap
    """
    # Deduplicate while preserving order
    seen: set = set()
    unique_ids: List[str] = []
    for cid in crop_ids:
        cid_upper = cid.strip().upper()
        if cid_upper and cid_upper not in seen:
            seen.add(cid_upper)
            unique_ids.append(cid_upper)

    if len(unique_ids) < 2:
        return []

    crop_attrs = _get_crop_attrs()
    warnings: List[Dict[str, Any]] = []

    for id_a, id_b in combinations(unique_ids, 2):
        attrs_a = crop_attrs.get(id_a, {})
        attrs_b = crop_attrs.get(id_b, {})
        label_a = _crop_label(id_a)
        label_b = _crop_label(id_b)
        warnings.extend(_check_pair(id_a, label_a, attrs_a, id_b, label_b, attrs_b))

    return warnings


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    # CRP0002 = Maize, CRP0003 = Jowar, CRP0006 = Wheat (similar cereals — likely to
    # share temporal, resource, and pest competition)
    # CRP0052 = Mango, CRP0055 = Coconut (plantation — likely wide canopy spread)
    sample_crop_ids = ["CRP0002", "CRP0003", "CRP0006"]

    results = check_crop_competition(sample_crop_ids)
    print(json.dumps(results, indent=2))
    print(f"\nTotal warnings: {len(results)}")

    # Group by type for summary
    by_type: Dict[str, int] = {}
    for w in results:
        by_type[w["warning_type"]] = by_type.get(w["warning_type"], 0) + 1
    for wtype, count in sorted(by_type.items()):
        print(f"  {wtype}: {count}")
