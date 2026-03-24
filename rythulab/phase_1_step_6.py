"""
phase_1_step_6.py

Generic farm-feasibility evaluator for Phase 1 Step 6.
Rule logic:
- For each crop parameter where sensitivity is High/Very High,
- Read the crop's recommended threshold/range from crop details,
- Check whether current farm context (CF values) is within that recommendation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from rythulab.phase_1_step_5 import get_crop_characteristics
    from rythulab.sheets.cf_label_extract import get_cf_label
except ModuleNotFoundError:
    from phase_1_step_5 import get_crop_characteristics
    from sheets.cf_label_extract import get_cf_label


RuleResult = Dict[str, Any]

_HIGH_SENS = {"high", "very high"}
_RISK_ORDER = ["none", "low", "medium", "high", "very high"]


def _empty_result(crop_id: str) -> RuleResult:
    return {
        "crop_id": crop_id,
        "warnings": [],
        "checks": [],
        "failed_checks": [],
        "passed_checks": [],
        "all_passed": True,
    }


def _finalize_result(result: RuleResult) -> RuleResult:
    result["failed_count"] = len(result["failed_checks"])
    result["passed_count"] = len(result["passed_checks"])
    result["all_passed"] = result["failed_count"] == 0
    return result


def _canonical_label(label: Any) -> str:
    text = str(label or "").strip().lower()
    text = text.replace("moderate", "medium")
    text = text.replace("very weak", "very high")
    text = text.replace("weak", "high")
    text = text.replace("good", "low")
    return re.sub(r"\s+", " ", text)


def _extract_numeric(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    if not match:
        return None
    return float(match.group(0))


def _extract_all_numbers(text: Any) -> List[float]:
    return [float(v) for v in re.findall(r"\d+(?:\.\d+)?", str(text or ""))]


def _extract_cf_value(cfs: Dict[str, Any], cf_code: str) -> Tuple[List[str], Any, Any]:
    """
    Returns: (input_keys, raw_actual_value, numeric_if_any)
    Accepts cfs payload shape from api._build_phase1_step6_farm_cfs:
      { "CF5": {"val": 6.8, "slab": "Good", ...}, ... }
    """
    target = (cf_code or "").upper()
    for key, value in (cfs or {}).items():
        key_text = str(key or "").strip().upper()
        if not key_text.startswith(target):
            continue

        if isinstance(value, dict):
            raw = value.get("val")
            if raw in (None, ""):
                raw = value.get("slab") or value.get("status")
            numeric = _extract_numeric(raw)
            return [str(key)], raw, numeric

        numeric = _extract_numeric(value)
        return [str(key)], value, numeric

    return [], None, None


def _risk_index(value: Any) -> Optional[int]:
    normalized = _canonical_label(value)
    if normalized not in _RISK_ORDER:
        return None
    return _RISK_ORDER.index(normalized)


def _store_check(result: RuleResult, entry: Dict[str, Any]) -> None:
    result["checks"].append(entry)
    if entry["passed"]:
        result["passed_checks"].append(entry)
        return
    result["failed_checks"].append(entry)
    result["warnings"].append(entry["message"])
    result["all_passed"] = False


def _build_entry(
    parameter: str,
    cf_code: str,
    input_keys: List[str],
    actual_value: Any,
    expected: str,
    passed: bool,
    reason: str,
    severity: str = "severe",
) -> Dict[str, Any]:
    cf_label = get_cf_label(cf_code)
    return {
        "parameter": parameter,
        "cf_codes": [cf_code],
        "cf_labels": [cf_label if cf_label != cf_code else parameter],
        "input_keys": input_keys,
        "actual_value": actual_value,
        "expected": expected,
        "passed": passed,
        "severity": severity,
        "message": f"{parameter}: expected {expected}, got {actual_value}. {reason}",
    }


def _is_high_sensitivity(value: Any) -> bool:
    return _canonical_label(value) in _HIGH_SENS


def _check_numeric_range(
    result: RuleResult,
    cfs: Dict[str, Any],
    *,
    parameter: str,
    cf_code: str,
    recommended: Any,
    reason: str,
) -> None:
    nums = _extract_all_numbers(recommended)
    if not nums:
        return

    if len(nums) >= 2:
        low, high = min(nums[0], nums[1]), max(nums[0], nums[1])
        expected = f"between {low} and {high}"
        mode = "between"
    else:
        # For strings like "< 20 kmph"
        text = str(recommended or "").strip()
        if "<" in text:
            low, high = None, nums[0]
            expected = f"<= {high}"
            mode = "max"
        elif ">" in text:
            low, high = nums[0], None
            expected = f">= {low}"
            mode = "min"
        else:
            # single value fallback: treat as upper bound for tolerance-style fields
            low, high = None, nums[0]
            expected = f"<= {high}"
            mode = "max"

    input_keys, raw_actual, numeric_actual = _extract_cf_value(cfs, cf_code)
    if raw_actual is None or numeric_actual is None:
        return

    if mode == "between":
        passed = low <= numeric_actual <= high
    elif mode == "max":
        passed = numeric_actual <= high
    else:
        passed = numeric_actual >= low

    entry = _build_entry(
        parameter=parameter,
        cf_code=cf_code,
        input_keys=input_keys,
        actual_value=raw_actual,
        expected=expected,
        passed=passed,
        reason=reason,
    )
    _store_check(result, entry)


def _check_categorical_risk(
    result: RuleResult,
    cfs: Dict[str, Any],
    *,
    parameter: str,
    cf_code: str,
    recommended: Any,
    reason: str,
) -> None:
    rec_index = _risk_index(recommended)
    if rec_index is None:
        return

    input_keys, raw_actual, _ = _extract_cf_value(cfs, cf_code)
    if raw_actual is None:
        return

    actual_index = _risk_index(raw_actual)
    if actual_index is None:
        return

    # Suitability labels represent maximum tolerable risk level
    passed = actual_index <= rec_index

    entry = _build_entry(
        parameter=parameter,
        cf_code=cf_code,
        input_keys=input_keys,
        actual_value=raw_actual,
        expected=f"risk <= {str(recommended).strip()}",
        passed=passed,
        reason=reason,
    )
    _store_check(result, entry)


def _check_rain_reliability(
    result: RuleResult,
    cfs: Dict[str, Any],
    *,
    recommended: Any,
    reason: str,
) -> None:
    """
    CF15 is rainfall variability (CV%). Lower is better.
    Crop recommendation comes as reliability class: Low/Medium/High.
    We map that to max-allowed CV thresholds.
    """
    rec = _canonical_label(recommended)
    max_cv_by_reliability = {
        "high": 25.0,
        "medium": 35.0,
        "low": 50.0,
    }
    max_cv = max_cv_by_reliability.get(rec)
    if max_cv is None:
        return

    input_keys, raw_actual, numeric_actual = _extract_cf_value(cfs, "CF15")
    if raw_actual is None or numeric_actual is None:
        return

    passed = numeric_actual <= max_cv
    expected = f"rain variability (CV%) <= {max_cv} for {str(recommended).strip()} reliability"

    entry = _build_entry(
        parameter="Rain Reliability",
        cf_code="CF15",
        input_keys=input_keys,
        actual_value=raw_actual,
        expected=expected,
        passed=passed,
        reason=reason,
    )
    _store_check(result, entry)


def _evaluate_generic_rules(crop_id: str, cfs: Dict[str, Any], result: RuleResult) -> None:
    crop_map = get_crop_characteristics([crop_id])
    crop = crop_map.get(crop_id)
    if not crop:
        raise ValueError(f"'{crop_id}' has no critical parameters defined.")

    sens = crop.get("sens") or {}
    sens_detail = crop.get("sens_detail") or {}

    # Parameter mappings: (sens_key, cf_code, recommended_field, check_type, label, reason)
    mappings = [
        ("ph", "CF5", "pH_r", "range", "Soil pH", "High pH sensitivity: farm pH must be within crop recommended pH range."),
        ("temp", "CF16", "temp", "range", "Temperature", "High temperature sensitivity: farm temperature must be within crop recommended range."),
        ("water", "CF9", "whcRange", "range", "Water Holding Capacity", "High water sensitivity: farm WHC must be within crop recommended range."),
        ("heat", "CF17", "heatTol", "range", "Heat Stress Days", "High heat sensitivity: farm heat-stress days must not exceed crop tolerance."),
        ("airflow", "CF19", "windTol", "range", "Wind Speed", "High wind sensitivity: farm wind should be within crop tolerance."),
        ("frost", "CF18", "frostSens", "risk", "Frost Risk", "High frost sensitivity: farm frost risk must be within crop suitability level."),
        ("subm", "CF24", "floodSuit", "risk", "Flood Risk", "High submergence sensitivity: flood risk must be within crop suitability level."),
        ("extreme", "CF25", "droughtSuit", "risk", "Drought Risk", "High extreme-weather sensitivity: drought risk must be within crop suitability level."),
    ]

    for sens_key, cf_code, rec_field, check_type, label, reason in mappings:
        if not _is_high_sensitivity(sens.get(sens_key)):
            continue

        recommended = crop.get(rec_field)
        if not recommended:
            continue

        if check_type == "range":
            _check_numeric_range(
                result,
                cfs,
                parameter=label,
                cf_code=cf_code,
                recommended=recommended,
                reason=reason,
            )
        else:
            _check_categorical_risk(
                result,
                cfs,
                parameter=label,
                cf_code=cf_code,
                recommended=recommended,
                reason=reason,
            )

    # Additional demand-value/range checks for other sensitive parameters
    demand_mappings = [
        ("nitrogen", "CF1", "thr_n", "Available Nitrogen", "High nitrogen sensitivity: farm N must be within crop demand range."),
        ("phosphorus", "CF2", "thr_p", "Available Phosphorus", "High phosphorus sensitivity: farm P must be within crop demand range."),
        ("potassium", "CF3", "thr_k", "Available Potassium", "High potassium sensitivity: farm K must be within crop demand range."),
        ("organic", "CF4", "thr_soc", "Soil Organic Carbon", "High organic-carbon sensitivity: farm SOC must be within crop demand range."),
        ("ec", "CF6", "thr_ec", "Soil Salinity (EC)", "High EC sensitivity: farm salinity must be within crop tolerance range."),
        ("depth", "CF8", "thr_depth", "Effective Soil Depth", "High soil-depth sensitivity: effective depth must meet crop range."),
        ("groundwater", "CF13", "thr_gw", "Groundwater Depth", "High groundwater-depth sensitivity: farm depth must match crop tolerance."),
        ("slope", "CF23", "thr_slope", "Slope", "High slope sensitivity: farm slope must be within preferred range."),
        ("calcium", "CF26", "thr_calcium", "Available Calcium", "High calcium sensitivity: farm Ca must be within crop demand range."),
        ("bulk", "CF27", "thr_bulk", "Bulk Density", "High bulk-density sensitivity: farm bulk density must match crop tolerance range."),
    ]

    for sens_key, cf_code, rec_field, label, reason in demand_mappings:
        if not _is_high_sensitivity(sens_detail.get(sens_key)):
            continue

        recommended = crop.get(rec_field)
        if not recommended:
            continue

        _check_numeric_range(
            result,
            cfs,
            parameter=label,
            cf_code=cf_code,
            recommended=recommended,
            reason=reason,
        )

    if _is_high_sensitivity(sens_detail.get("rain")):
        rain_recommended = crop.get("hum")
        if rain_recommended:
            _check_rain_reliability(
                result,
                cfs,
                recommended=rain_recommended,
                reason="High rain-reliability sensitivity: farm rainfall variability must satisfy crop reliability requirement.",
            )


def check_critical_parameters(crop_id: str, cfs: Dict[str, Any]) -> RuleResult:
    """
    Generic evaluator:
    - Identify parameters where crop sensitivity is High/Very High
    - Check those parameters against farm context values using crop recommended ranges
    """
    if not crop_id:
        raise ValueError("crop_id must not be empty")

    crop_id = crop_id.strip().upper()
    result = _empty_result(crop_id)
    _evaluate_generic_rules(crop_id, cfs or {}, result)

    # A crop may be valid, but no check can be produced when:
    # - none of its sensitivities are High/Very High, or
    # - high-sensitivity parameters don't yet have mapped rules, or
    # - required CF inputs are missing in payload.
    # This should not be treated as "no critical parameters defined".
    if not result["checks"]:
        result["warnings"].append(
            "No high-sensitivity critical checks could be evaluated from current farm CF inputs."
        )

    return _finalize_result(result)


if __name__ == "__main__":
    sample = check_critical_parameters(
        "CRP0001",
        {
            "CF5": {"val": 6.5, "slab": "Good"},
            "CF16": {"val": 30, "slab": "Good"},
            "CF9": {"val": 62, "slab": "Good"},
            "CF17": {"val": 3, "slab": "Good"},
            "CF19": {"val": 18, "slab": "Good"},
            "CF18": {"val": "Low", "slab": "Low"},
            "CF24": {"val": "Low", "slab": "Low"},
            "CF25": {"val": "High", "slab": "High"},
        },
    )
    print(sample)
