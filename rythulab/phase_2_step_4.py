from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

try:
    from crop_micro_feature_extract import get_produced_micro_features_by_cropid
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
    from crop_micro_feature_extract import get_produced_micro_features_by_cropid

try:
    from rythulab.sheets.mf_labels.mf_label_extract import annotate_mf_codes, build_mf_label_map
    from rythulab.sheets.cf_label_extract import (
        annotate_cf_code,
        build_cf_label_map,
        build_label_to_cf_number_map,
    )
except ModuleNotFoundError:
    import sys

    sheets_dir = Path(__file__).resolve().parent / "sheets"
    sys.path.append(str(sheets_dir))
    sys.path.append(str(sheets_dir / "mf_labels"))

    from mf_label_extract import annotate_mf_codes, build_mf_label_map
    from cf_label_extract import annotate_cf_code, build_cf_label_map, build_label_to_cf_number_map

try:
    from rythulab.phase_1_step_1 import load_step1_results
except ModuleNotFoundError:
    from phase_1_step_1 import load_step1_results


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CF_FARM_FEATURES_PATH = SHEETS_DIR / "cf_labels" / "crop suitability sheets - Farm context features.csv"
CF_MF_IMPACT_MATRIX_PATH = SHEETS_DIR / "CFvsMF" / "CF_MF_Impact_Matrix - Select CF_MF interactions.csv"
MICRO_FEATURES_DIR = SHEETS_DIR / "Crop Micro Features"

WEAK_STATUSES = {"very weak", "weak"}
CF_CODE_RE = re.compile(r"^(CF\d+)", re.IGNORECASE)


def _extract_mf_code_from_column(column_header):
    """Extract MF code like MF1, MF3G from a column header like MF1_PartialShade."""
    match = re.match(r"(MF\d+[A-Z]*)", column_header.upper())
    return match.group(1) if match else None


def _extract_cf_number(value: object) -> str | None:
    match = CF_CODE_RE.match(str(value or "").strip().upper())
    return match.group(1) if match else None


def _extract_status_value(raw_value: Any) -> Any:
    if isinstance(raw_value, dict):
        raise ValueError(
            "farm_cf_values must use primitive values (e.g., {'CF1': 'Weak'}), not nested objects like {'CF1': {'slab': 'Weak'}}"
        )
    return raw_value


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_cf_input_key(key: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(key or "").strip().upper())


def _build_cf_input_alias_map(
    cf_mf_impact_map: Dict[str, List[str]], farm_features_path: Path | str = CF_FARM_FEATURES_PATH
) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    bare_to_full: Dict[str, str] = {}

    for full_key in cf_mf_impact_map:
        upper_key = str(full_key).strip().upper()
        alias_map[_normalize_cf_input_key(upper_key)] = full_key

        cf_number = _extract_cf_number(upper_key)
        if cf_number:
            bare_to_full[cf_number] = full_key
            alias_map[_normalize_cf_input_key(cf_number)] = full_key

        if "_" in upper_key:
            suffix = upper_key.split("_", 1)[1]
            alias_map[_normalize_cf_input_key(suffix)] = full_key

    label_to_cf_number = build_label_to_cf_number_map(farm_features_path)
    for label, cf_number in label_to_cf_number.items():
        full_key = bare_to_full.get(str(cf_number).upper())
        if full_key:
            alias_map[_normalize_cf_input_key(label)] = full_key

    return alias_map


def _normalize_farm_cf_values(
    farm_cf_values: Dict[str, Any],
    cf_mf_impact_map: Dict[str, List[str]],
    farm_features_path: Path | str = CF_FARM_FEATURES_PATH,
) -> tuple[Dict[str, Any], List[Dict[str, str]]]:
    if not isinstance(farm_cf_values, dict):
        raise ValueError("farm_cf_values must be a JSON object like {'CF1': 'Weak', 'CF9': 'Very Weak'}")

    alias_map = _build_cf_input_alias_map(cf_mf_impact_map, farm_features_path)
    normalized: Dict[str, Any] = {}
    unsupported_inputs: List[Dict[str, str]] = []

    for key, raw_value in (farm_cf_values or {}).items():
        status = _extract_status_value(raw_value)

        if status is None or str(status).strip() == "":
            raise ValueError(
                f"farm_cf_values['{key}'] must be a non-empty primitive value like 'Weak' or 'Very Weak'"
            )

        normalized_key = alias_map.get(_normalize_cf_input_key(key))
        if not normalized_key:
            unsupported_inputs.append({
                "input_key": str(key),
                "status": str(status or ""),
            })
            continue
        normalized[normalized_key] = status

    return normalized, unsupported_inputs


def build_cf_mf_impact_map(impact_matrix_path=CF_MF_IMPACT_MATRIX_PATH):
    """
    Builds a map of CF -> list of MF codes that positively impact (+) it.
    Returns: { "CF1_N": ["MF23", "MF24", "MF27"], ... }
    """
    impact_matrix_path = Path(impact_matrix_path)
    cf_improving_mfs = {}

    with impact_matrix_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        mf_columns = {
            col: _extract_mf_code_from_column(col)
            for col in reader.fieldnames or []
            if col != "CF" and _extract_mf_code_from_column(col)
        }

        for row in reader:
            cf_code = str(row.get("CF", "")).strip()
            if not cf_code:
                continue

            improving_mfs = []
            for col, mf_code in mf_columns.items():
                raw_value = str(row.get(col, "")).strip()
                if raw_value == "+":
                    improving_mfs.append(mf_code)
                    continue
                numeric_value = _safe_float(raw_value)
                if numeric_value is not None and numeric_value > 0:
                    improving_mfs.append(mf_code)
            cf_improving_mfs[cf_code] = improving_mfs

    return cf_improving_mfs


def analyze_weak_cf_mitigating_crops(
    farm_cf_values,
    impact_matrix_path=CF_MF_IMPACT_MATRIX_PATH,
    micro_features_dir=MICRO_FEATURES_DIR,
    farm_features_path=CF_FARM_FEATURES_PATH,
):
    """
    Given context feature values for a farm, identifies crops that can improve
    weak or very weak CFs by producing the relevant micro features.

    Args:
        farm_cf_values (dict): A dict mapping CF code/label to its status value.
            Keys should be CF numbers like 'CF1', 'CF2', 'CF3'.
            Full CF codes like 'CF1_N' and human-readable labels are also tolerated.
            Values must be primitive, non-empty statuses (e.g., 'Weak', 'Very Weak', 'Good').
            e.g. { "CF1": "Very Weak", "CF9": "Weak", "CF16": "Good" }
        impact_matrix_path: Path to CF_MF_Impact_Matrix CSV.
        micro_features_dir: Path to Crop Micro Features directory.
        farm_features_path: Path to Farm context features CSV for label mapping.

    Returns:
        dict with keys:
            - weak_cfs: annotated list of CF codes that are Weak or Very Weak
            - cf_analysis: per-CF breakdown of needed MFs and crops that produce them
            - recommended_crops: aggregated list of crops with full reasons
    """
    cf_mf_impact_map = build_cf_mf_impact_map(impact_matrix_path)
    produced_by_crop = get_produced_micro_features_by_cropid(micro_features_dir)
    mf_label_map = build_mf_label_map()
    step1_scores = load_step1_results()
    normalized_farm_cf_values, unsupported_inputs = _normalize_farm_cf_values(
        farm_cf_values,
        cf_mf_impact_map,
        farm_features_path,
    )

    weak_cfs = []
    for full_cf_code, status in normalized_farm_cf_values.items():
        if str(status).strip().lower() in WEAK_STATUSES:
            weak_cfs.append((full_cf_code, status))

    cf_analysis = []
    aggregated_crops = {}

    for full_cf_code, cf_status in weak_cfs:
        cf_label = annotate_cf_code(full_cf_code, farm_features_path).get("cf_label", full_cf_code)
        improving_mfs = cf_mf_impact_map.get(full_cf_code, [])

        if not improving_mfs:
            cf_analysis.append({
                "cf": annotate_cf_code(full_cf_code, farm_features_path),
                "status": cf_status,
                "improving_mfs": [],
                "crops_producing_improving_mfs": [],
            })
            continue

        # Find crops that produce any of the improving MFs
        crops_for_cf = []
        for crop_name, produced_mfs in produced_by_crop.items():
            if step1_scores and crop_name not in step1_scores:
                continue
            matching_mfs = sorted(set(produced_mfs) & set(improving_mfs))
            if not matching_mfs:
                continue

            reasons = [
                (
                    f"Produces {mf_label_map.get(mf_code, mf_code)}, "
                    f"which improves {cf_label} (currently {cf_status})"
                )
                for mf_code in matching_mfs
            ]

            crops_for_cf.append({
                "crop": crop_name,
                "step1_score": step1_scores.get(crop_name),
                "produces_mfs": annotate_mf_codes(matching_mfs),
                "reasons": reasons,
            })

            # Aggregate across all weak CFs
            agg = aggregated_crops.setdefault(crop_name, {"crop": crop_name, "step1_score": step1_scores.get(crop_name), "supports": []})
            agg["supports"].append({
                "cf": annotate_cf_code(full_cf_code, farm_features_path),
                "cf_status": cf_status,
                "produces_mfs": annotate_mf_codes(matching_mfs),
                "reasons": reasons,
            })

        crops_for_cf.sort(key=lambda x: (-len(x["produces_mfs"]), x["crop"]))

        cf_analysis.append({
            "cf": annotate_cf_code(full_cf_code, farm_features_path),
            "status": cf_status,
            "improving_mfs": annotate_mf_codes(improving_mfs),
            "crops_producing_improving_mfs": crops_for_cf,
        })

    recommended_crops = sorted(
        aggregated_crops.values(),
        key=lambda x: (-len(x["supports"]), x["crop"]),
    )

    return {
        "weak_cfs": [annotate_cf_code(full, farm_features_path) for full, _ in weak_cfs],
        "unsupported_inputs": unsupported_inputs,
        "cf_analysis": cf_analysis,
        "recommended_crops": recommended_crops,
    }


if __name__ == "__main__":
    sample_farm_cf_values = {
        "CF1": "Very Weak",
        "CF9": "Weak",
        "CF16": "Moderate",
        "CF11": "Weak",
        "CF20": "Very Weak",
        "CF22": "Good",
    }

    result = analyze_weak_cf_mitigating_crops(sample_farm_cf_values)
    print(json.dumps(result, indent=2))
