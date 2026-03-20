"""
phase_1_step_6.py

Evaluates critical agronomic parameters for a crop against supplied CF
(Crop Factor) values. Each crop's rules are written explicitly as Python
conditions translated from the critical-parameters sheet.

The public API returns both failed and passed checks. For CF-based inputs,
human-readable labels are resolved via sheets.cf_label_extract.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from rythulab.sheets.cf_label_extract import get_cf_label
except ModuleNotFoundError:
    from sheets.cf_label_extract import get_cf_label


RuleResult = Dict[str, Any]
RuleFunction = Callable[[Dict[str, Any], RuleResult], None]

_BIOINDEX_ORDER = ["Low", "Medium", "High", "Very High"]

_LABEL_OVERRIDES = {
    "TempC": "Temperature",
    "CF_TempC": "Temperature",
    "Water_Regime": "Water Regime",
    "CF_Water": "Water Regime",
    "Water": "Water Regime",
    "CF11_Drainage": "Drainage",
    "Drainage": "Drainage",
    "CF14_Irrigation": "Irrigation",
    "Irrigation": "Irrigation",
    "CF8_Depth": "Soil Depth",
    "Depth_cm": "Soil Depth",
    "Depth": "Soil Depth",
    "Soil_Depth": "Soil Depth",
    "CF25_DroughtRisk": "Drought Risk",
    "DroughtRisk": "Drought Risk",
    "CF13_GW": "Groundwater Depth",
    "GWDepth": "Groundwater Depth",
    "CF17_HeatDays": "Heat Stress Days",
    "HeatDays": "Heat Stress Days",
    "CF23_Slope": "Slope",
    "Slope_pct": "Slope",
    "Slope": "Slope",
    "CF18_FrostRisk": "Frost Risk",
    "FrostRisk": "Frost Risk",
    "CF24_FloodRisk": "Flood Risk",
    "FloodRisk": "Flood Risk",
    "CF7_Texture": "Soil Texture",
    "Texture": "Soil Texture",
    "CF5_pH": "Soil pH",
    "pH": "Soil pH",
    "CF20_BioIndex": "BioIndex",
    "BioIndex": "BioIndex",
    "CF21_DayLength": "Day Length",
    "DayLength": "Day Length",
    "CF4_N": "Available Nitrogen",
    "Fertility": "Available Nitrogen",
    "N": "Available Nitrogen",
    "Rainfall_mm": "Rainfall",
    "Rainfall": "Rainfall",
    "RH": "Relative Humidity",
    "WetDays": "Wet Days",
    "CF_Support": "Support",
    "Support": "Support",
    "CF_Light": "Light",
    "Light": "Light",
    "Sun": "Sunlight",
}


def _bioindex_gt(value: str, threshold: str) -> bool:
    try:
        return _BIOINDEX_ORDER.index(value) > _BIOINDEX_ORDER.index(threshold)
    except ValueError:
        return False


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


def _extract_numeric(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)

    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    return float(match.group(0))


def _resolve_input(cfs: Dict[str, Any], *keys: str) -> Tuple[Optional[str], Optional[Any]]:
    for key in keys:
        variants = [key]

        stripped_num = re.sub(r"^CF\d+_", "", key)
        if stripped_num != key:
            variants.append(stripped_num)

        stripped_cf = re.sub(r"^CF_", "", key)
        if stripped_cf != key:
            variants.append(stripped_cf)

        for variant in variants:
            if variant in cfs:
                return variant, cfs[variant]

            lower_variant = variant.lower()
            for supplied_key, supplied_value in cfs.items():
                if supplied_key.lower() == lower_variant:
                    return supplied_key, supplied_value

    return None, None


def _canonical_cf_keys(keys: List[str]) -> List[str]:
    return [key for key in keys if re.match(r"^CF\d+", key, re.IGNORECASE)]


def _resolve_parameter_label(keys: List[str], parameter_name: Optional[str] = None) -> str:
    if parameter_name:
        return parameter_name

    for key in keys:
        if key in _LABEL_OVERRIDES:
            return _LABEL_OVERRIDES[key]

        if re.match(r"^CF\d+", key, re.IGNORECASE):
            label = get_cf_label(key)
            if label != key:
                return label

    return keys[0].replace("_", " ")


def _build_check_entry(
    keys: List[str],
    actual_keys: List[str],
    actual_value: Any,
    expected: str,
    passed: bool,
    reason: str,
    severity: str,
    parameter_name: Optional[str] = None,
) -> Dict[str, Any]:
    cf_codes = _canonical_cf_keys(keys)
    parameter = _resolve_parameter_label(keys, parameter_name)
    cf_labels = [get_cf_label(code) for code in cf_codes]

    return {
        "parameter": parameter,
        "cf_codes": cf_codes,
        "cf_labels": cf_labels if cf_labels else [parameter],
        "input_keys": actual_keys,
        "actual_value": actual_value,
        "expected": expected,
        "passed": passed,
        "severity": severity,
        "message": f"{parameter}: expected {expected}, got {actual_value}. {reason}",
    }


def _store_check(result: RuleResult, entry: Dict[str, Any]) -> None:
    result["checks"].append(entry)

    if entry["passed"]:
        result["passed_checks"].append(entry)
        return

    result["failed_checks"].append(entry)
    result["warnings"].append(entry["message"])
    result["all_passed"] = False


def _check_in(
    result: RuleResult,
    cfs: Dict[str, Any],
    keys: List[str],
    allowed: Tuple[Any, ...],
    reason: str,
    severity: str = "warning",
    parameter_name: Optional[str] = None,
) -> None:
    actual_key, actual_value = _resolve_input(cfs, *keys)
    if actual_key is None:
        return

    entry = _build_check_entry(
        keys=keys,
        actual_keys=[actual_key],
        actual_value=actual_value,
        expected="one of " + ", ".join(repr(item) for item in allowed),
        passed=actual_value in allowed,
        reason=reason,
        severity=severity,
        parameter_name=parameter_name,
    )
    _store_check(result, entry)


def _check_equals(
    result: RuleResult,
    cfs: Dict[str, Any],
    keys: List[str],
    expected_value: Any,
    reason: str,
    severity: str = "warning",
    parameter_name: Optional[str] = None,
) -> None:
    actual_key, actual_value = _resolve_input(cfs, *keys)
    if actual_key is None:
        return

    entry = _build_check_entry(
        keys=keys,
        actual_keys=[actual_key],
        actual_value=actual_value,
        expected=repr(expected_value),
        passed=actual_value == expected_value,
        reason=reason,
        severity=severity,
        parameter_name=parameter_name,
    )
    _store_check(result, entry)


def _check_min(
    result: RuleResult,
    cfs: Dict[str, Any],
    keys: List[str],
    minimum: float,
    reason: str,
    severity: str = "warning",
    parameter_name: Optional[str] = None,
) -> None:
    actual_key, actual_value = _resolve_input(cfs, *keys)
    if actual_key is None:
        return

    numeric_value = _extract_numeric(actual_value)
    if numeric_value is None:
        return

    entry = _build_check_entry(
        keys=keys,
        actual_keys=[actual_key],
        actual_value=actual_value,
        expected=f">= {minimum}",
        passed=numeric_value >= minimum,
        reason=reason,
        severity=severity,
        parameter_name=parameter_name,
    )
    _store_check(result, entry)


def _check_max(
    result: RuleResult,
    cfs: Dict[str, Any],
    keys: List[str],
    maximum: float,
    reason: str,
    severity: str = "warning",
    parameter_name: Optional[str] = None,
) -> None:
    actual_key, actual_value = _resolve_input(cfs, *keys)
    if actual_key is None:
        return

    numeric_value = _extract_numeric(actual_value)
    if numeric_value is None:
        return

    entry = _build_check_entry(
        keys=keys,
        actual_keys=[actual_key],
        actual_value=actual_value,
        expected=f"<= {maximum}",
        passed=numeric_value <= maximum,
        reason=reason,
        severity=severity,
        parameter_name=parameter_name,
    )
    _store_check(result, entry)


def _check_between(
    result: RuleResult,
    cfs: Dict[str, Any],
    keys: List[str],
    minimum: float,
    maximum: float,
    reason: str,
    severity: str = "warning",
    parameter_name: Optional[str] = None,
) -> None:
    actual_key, actual_value = _resolve_input(cfs, *keys)
    if actual_key is None:
        return

    numeric_value = _extract_numeric(actual_value)
    if numeric_value is None:
        return

    entry = _build_check_entry(
        keys=keys,
        actual_keys=[actual_key],
        actual_value=actual_value,
        expected=f"between {minimum} and {maximum}",
        passed=minimum <= numeric_value <= maximum,
        reason=reason,
        severity=severity,
        parameter_name=parameter_name,
    )
    _store_check(result, entry)


def _check_bioindex_gt(
    result: RuleResult,
    cfs: Dict[str, Any],
    keys: List[str],
    threshold: str,
    reason: str,
    severity: str = "warning",
    parameter_name: Optional[str] = None,
) -> None:
    actual_key, actual_value = _resolve_input(cfs, *keys)
    if actual_key is None:
        return

    entry = _build_check_entry(
        keys=keys,
        actual_keys=[actual_key],
        actual_value=actual_value,
        expected=f"> {threshold}",
        passed=_bioindex_gt(str(actual_value), threshold),
        reason=reason,
        severity=severity,
        parameter_name=parameter_name,
    )
    _store_check(result, entry)


def _check_rh_or_wetdays(result: RuleResult, cfs: Dict[str, Any]) -> None:
    rh_key, rh_value = _resolve_input(cfs, "RH")
    wet_key, wet_value = _resolve_input(cfs, "WetDays")

    if rh_key is None and wet_key is None:
        return

    rh_numeric = _extract_numeric(rh_value) if rh_key is not None else None
    wet_numeric = _extract_numeric(wet_value) if wet_key is not None else None
    if rh_key is not None and rh_numeric is None:
        return
    if wet_key is not None and wet_numeric is None:
        return

    passed = False
    if rh_numeric is not None and rh_numeric < 70:
        passed = True
    if wet_numeric is not None and wet_numeric < 5:
        passed = True

    actual_keys = []
    actual_value = {}
    if rh_key is not None:
        actual_keys.append(rh_key)
        actual_value["RH"] = rh_value
    if wet_key is not None:
        actual_keys.append(wet_key)
        actual_value["WetDays"] = wet_value

    entry = _build_check_entry(
        keys=["RH", "WetDays"],
        actual_keys=actual_keys,
        actual_value=actual_value,
        expected="RH < 70 OR WetDays < 5",
        passed=passed,
        reason="Flowering humidity control; blossom drop risk.",
        severity="warning",
        parameter_name="Relative Humidity / Wet Days",
    )
    _store_check(result, entry)


def _rules_paddy(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_in(result, cfs, ["CF24_FloodRisk", "FloodRisk"], ("Medium", "High"), "Delta-adapted crop needs standing water; total failure without.")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Poor", "Puddled wetland required; root rot in aerobic soils.")
    _check_in(result, cfs, ["Water_Regime"], ("Copious-Irrigation", "Controlled-Irrigation"), "1500+ mm/season; yield below 20% under rainfed conditions.")


def _rules_maize(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 18, 32, "Required temperature range for optimal growth.", parameter_name="Temperature")
    _check_in(result, cfs, ["CF14_Irrigation", "Irrigation"], ("Protective", "Assured"), "Silking-stage moisture is required; 50-70% yield loss otherwise.")
    _check_min(result, cfs, ["CF8_Depth", "Depth_cm", "Depth"], 60, "Deep feeder roots need deeper soil; shallow soils increase lodging.")


def _rules_bajra(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_in(result, cfs, ["CF25_DroughtRisk", "DroughtRisk"], ("High", "Very High"), "Drought-escape crop; fails in irrigated areas.")
    _check_in(result, cfs, ["CF7_Texture", "Texture"], ("Sandy", "SandyLoam"), "Millet signature texture; smut risk in heavy soils.")
    _check_min(result, cfs, ["CF13_GW", "GWDepth"], 1.500001, "Avoid waterlogging; root rot risk.", parameter_name="Groundwater Depth")


def _rules_jowar(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_max(result, cfs, ["CF17_HeatDays", "HeatDays"], 25, "Heat tolerant but not extreme; grain shrivel after prolonged heat.")
    _check_in(result, cfs, ["CF11_Drainage", "Drainage"], ("Good", "Moderate"), "Sterile hybrids are sensitive; waterlogging kills.")


def _rules_red_gram(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_max(result, cfs, ["CF23_Slope", "Slope_pct", "Slope"], 8, "Rhizobium inoculation operations fail at high slope; nodulation failure above 10%.")
    _check_equals(result, cfs, ["CF14_Irrigation", "Irrigation"], "Protective", "Pod filling moisture required; around 60% pod drop otherwise.")
    _check_between(result, cfs, ["TempC", "CF_TempC"], 25, 35, "Flowering temperature sensitive; flower drop outside the range.", parameter_name="Temperature")


def _rules_bengal_gram(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_equals(result, cfs, ["CF18_FrostRisk", "FrostRisk"], "None", "Rabi frost causes total loss.")
    _check_in(result, cfs, ["Water_Regime"], ("Rain-Fed-High", "Controlled-Irrigation"), "Cool moist pod set required; shriveling risk otherwise.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.5, 8.0, "Rhizobium works best in this range; nitrogen-fixation failure outside it.")


def _rules_blackgram(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_in(result, cfs, ["CF14_Irrigation", "Irrigation"], ("Protective", "Assured"), "Podding-stage moisture required; pod shatter risk otherwise.")
    _check_max(result, cfs, ["CF23_Slope", "Slope_pct", "Slope"], 5, "Inoculation logistics degrade on higher slopes; poor nodulation risk.")
    _check_rh_or_wetdays(result, cfs)


def _rules_greengram(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_in(result, cfs, ["CF11_Drainage", "Drainage"], ("Good", "Moderate"), "Avoid water stagnation; root rot risk.")
    _check_between(result, cfs, ["TempC", "CF_TempC"], 22, 32, "Narrow temperature window; sterility outside the range.", parameter_name="Temperature")


def _rules_lentil(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_equals(result, cfs, ["CF18_FrostRisk", "FrostRisk"], "None", "Cool but frost-free flowering is required; pod abortion risk otherwise.")
    _check_between(result, cfs, ["TempC", "CF_TempC"], 15, 25, "Rabi cool-season crop; heat sterility above 28 C.", parameter_name="Temperature")
    _check_in(result, cfs, ["Water_Regime"], ("Rain-Fed-High", "Controlled-Irrigation"), "Moderate moisture required; drought increases wilt risk.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.0, 7.5, "Rhizobium activity drops outside the range; poor nodulation follows.")


def _rules_groundnut(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_in(result, cfs, ["CF7_Texture", "Texture"], ("SandyLoam", "Sandy"), "Peg development requires light texture; peg rot in clay soils.")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Avoid waterlogging; collar rot can cause major loss.")
    _check_in(result, cfs, ["CF25_DroughtRisk", "DroughtRisk"], ("High", "Very High"), "Pod setting suits drought-prone conditions; empty pod risk otherwise.")
    _check_min(result, cfs, ["CF13_GW", "GWDepth"], 1.500001, "Shallow water table is unsuitable; disease pressure rises.", parameter_name="Groundwater Depth")


def _rules_sesame(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 27, 38, "Capsule setting requires warm conditions; shriveled seeds outside the range.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Dry flowering condition required; capsule drop under poor drainage.")
    _check_in(result, cfs, ["Water_Regime"], ("Rain-Fed-Low", "Supplemental"), "Dry regime required; phyllody virus risk otherwise.")


def _rules_sunflower(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_bioindex_gt(result, cfs, ["CF20_BioIndex", "BioIndex"], "Medium", "Allelopathy management needs higher bioindex; soil sickness risk otherwise.")
    _check_equals(result, cfs, ["CF14_Irrigation", "Irrigation"], "Protective", "Button-stage moisture required; head deformity otherwise.")
    _check_max(result, cfs, ["CF23_Slope", "Slope_pct", "Slope"], 5, "Wind protection is needed; lodging risk on higher slope.")


def _rules_castor(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_in(result, cfs, ["CF11_Drainage", "Drainage"], ("Good", "Moderate"), "Deep taproot hates waterlogging; root rot risk.")
    _check_in(result, cfs, ["CF25_DroughtRisk", "DroughtRisk"], ("Medium", "High"), "Semi-arid adaptation fits these conditions; irrigated settings can increase capsule shatter.")
    _check_between(result, cfs, ["TempC", "CF_TempC"], 25, 38, "Capsule set requires heat; poor seed fill below 25 C.", parameter_name="Temperature")
    _check_min(result, cfs, ["CF8_Depth", "Depth", "Soil_Depth"], 60, "Taproot requires at least 60 cm soil depth; stunted growth otherwise.")
    _check_max(result, cfs, ["CF23_Slope", "Slope_pct", "Slope"], 10, "Tall stems need wind protection; mechanical damage risk on higher slope.")


def _rules_chilli(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 24, 32, "Flowering and fruit set require this range; flower drop above 35 C.", parameter_name="Temperature")
    _check_equals(result, cfs, ["Water_Regime"], "Irrigated-Moderate", "Moderate irrigation helps avoid blossom-end issues; fruit cracking risk otherwise.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.0, 7.0, "Nutrient uptake is best in this range; leaf curl risk rises outside it.")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Wet conditions increase thrips and virus pressure; total failure risk.")


def _rules_turmeric(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_max(result, cfs, ["TempC", "CF_TempC"], 32, "Rhizome bulking benefits from shade and cooler conditions; sunburn and yield loss otherwise.", parameter_name="Temperature")
    _check_between(result, cfs, ["Rainfall_mm", "Rainfall"], 1500, 2500, "Rhizome expansion needs this rainfall band; dry rot risk outside it.")
    _check_equals(result, cfs, ["CF7_Texture", "Texture"], "Loam", "Organic-matter-supporting loam is preferred; curcumin quality drops otherwise.")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Good drainage reduces rhizome rot and waterlogging loss.")


def _rules_coriander(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 15, 25, "Seed filling requires cool conditions; bolting increases in heat.", parameter_name="Temperature")
    _check_max(result, cfs, ["CF21_DayLength", "DayLength"], 12, "Vegetative growth requires short day length; stem gall risk otherwise.")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Good drainage reduces powdery mildew and seed mould risk.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.0, 8.0, "Oil content and yield are best in this pH range.")


def _rules_fenugreek(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 18, 25, "Leaf and seed set are best in this range; pod shatter in heat.", parameter_name="Temperature")
    _check_in(result, cfs, ["CF7_Texture", "Texture"], ("Loam", "SandyLoam"), "Preferred texture avoids root rot and supports nodulation.")
    _check_equals(result, cfs, ["CF14_Irrigation", "Irrigation"], "Protective", "Protective irrigation reduces wilt during dry spells.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.0, 7.0, "Rhizobium and protein outcomes are best in this range.")


def _rules_ginger(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_max(result, cfs, ["TempC", "CF_TempC"], 32, "Shade-driven cooling is needed; leaf scorch above the limit.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Good drainage prevents rhizome rot.")
    _check_equals(result, cfs, ["CF_Water", "Water_Regime", "Water"], "High", "High moisture regime is required; dry failure otherwise.", parameter_name="Water Regime")
    _check_max(result, cfs, ["CF23_Slope", "Slope_pct", "Slope"], 5, "Lower slope protects against erosion and washout.")


def _rules_cumin(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 15, 25, "Cool rabi temperature is required; bolting in heat.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Excellent", "Excellent drainage avoids mildew and seed loss.")
    _check_equals(result, cfs, ["CF25_DroughtRisk", "DroughtRisk"], "High", "Dry capsule condition is preferred; humid fungal risk otherwise.")
    _check_equals(result, cfs, ["CF7_Texture", "Texture"], "SandyLoam", "Light root zone required; waterlogging risk in clay.")


def _rules_mustard(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 10, 25, "Cool siliqua set is needed; shattering increases in heat.", parameter_name="Temperature")
    _check_min(result, cfs, ["CF13_GW", "GWDepth"], 2.000001, "Mustard needs dry feet; root rot risk with shallower groundwater.", parameter_name="Groundwater Depth")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Good drainage reduces blight and rot risk.")
    _check_max(result, cfs, ["CF23_Slope", "Slope_pct", "Slope"], 3, "Lower slope helps prevent wind lodging and yield loss.")


def _rules_curry_leaves(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_max(result, cfs, ["TempC", "CF_TempC"], 32, "Leaf quality declines with heat; burn risk above the limit.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF_Water", "Water_Regime", "Water"], "Moderate", "Moderate water regime helps oil retention and avoids wilt.", parameter_name="Water Regime")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.0, 7.5, "Nutrient uptake is best in this pH band; chlorosis risk otherwise.")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Perennial roots decline in poorly drained conditions.")


def _rules_mint(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_equals(result, cfs, ["CF14_Irrigation", "Irrigation"], "Frequent", "Frequent irrigation supports oil quality; low menthol otherwise.")
    _check_between(result, cfs, ["TempC", "CF_TempC"], 18, 28, "Cooler conditions support volatiles; bolting risk in heat.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Moderate", "Moderate drainage supports airflow; defoliation risk otherwise.")
    _check_equals(result, cfs, ["CF4_N", "Fertility", "N"], "High", "High nitrogen supports biomass; thin yield otherwise.", parameter_name="Available Nitrogen")


def _rules_garlic(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 10, 25, "Cool rabi temperature supports bulb formation; bolting risk in heat.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Excellent", "Excellent drainage prevents clove rot and wet loss.")
    _check_equals(result, cfs, ["CF25_DroughtRisk", "DroughtRisk"], "Low-Medium", "Moderate vernalization moisture is needed; bulbs stay small in dry conditions.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.0, 7.0, "Nutrient uptake and pink-rot control are best in this pH range.")


def _rules_fennel(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 15, 28, "Seed set is best in this range; sterility in extremes.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Good drainage reduces Fusarium wilt and seed drop risk.")
    _check_equals(result, cfs, ["CF_Water", "Water_Regime", "Water"], "Rain-Fed-Medium", "Dry flowering regime is preferred; poor fill otherwise.", parameter_name="Water Regime")
    _check_in(result, cfs, ["CF7_Texture", "Texture"], ("Loam", "SandyLoam", "Loam-SandyLoam"), "Taproot development is better in loam to sandy-loam textures.")


def _rules_ajwain(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 18, 30, "Seed oil and thymol quality are best in this range.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Excellent", "Excellent drainage prevents root rot and seedling death.")
    _check_equals(result, cfs, ["CF25_DroughtRisk", "DroughtRisk"], "Medium-High", "Dry-adapted crop; fungal risk under wetter conditions.")
    _check_max(result, cfs, ["CF23_Slope", "Slope_pct", "Slope"], 5, "Lower slope helps preserve airflow and reduce rust risk.")


def _rules_tomato(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 21, 30, "Fruit set requires this range; blossom drop outside it.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Good drainage reduces wilt and rot loss.")
    _check_equals(result, cfs, ["CF_Support", "Support"], "Stake", "Staking improves airflow and reduces gray mold risk.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.0, 6.8, "This pH range reduces blossom-end problems and catfacing.")


def _rules_brinjal(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 23, 32, "Fruit enlargement is best in this range; drop risk in heat.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF_Water", "Water_Regime", "Water"], "Regular", "Regular moisture supports fruit quality and reduces dry split.", parameter_name="Water Regime")
    _check_equals(result, cfs, ["CF_Light", "Light", "Sun"], "Full", "Full light is required for best yield; shade causes leggy growth.", parameter_name="Light")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Good drainage reduces shoot borer and root rot risk.")


def _rules_okra(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 25, 35, "Tender pods require this range; pods turn tough under heat stress.", parameter_name="Temperature")
    _check_equals(result, cfs, ["CF14_Irrigation", "Irrigation"], "Frequent", "Frequent irrigation supports pod quality; dry conditions increase fibrousness.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 6.0, 7.0, "This pH band reduces yellow-vein and mosaic risk.")
    _check_equals(result, cfs, ["CF7_Texture", "Texture"], "SandyLoam", "Deep root growth is best in sandy-loam soils.")


def _rules_onion(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 15, 25, "Bulb swell is best in cool rabi temperatures; bolting risk in heat.", parameter_name="Temperature")
    _check_min(result, cfs, ["CF21_DayLength", "DayLength"], 12.000001, "Bulbing needs day length above 12 hours.", parameter_name="Day Length")
    _check_equals(result, cfs, ["CF4_N", "Fertility", "N"], "High", "High nitrogen supports size; low N increases neck rot risk.", parameter_name="Available Nitrogen")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Excellent", "Excellent drainage reduces purple blotch and smudge.")


def _rules_potato(cfs: Dict[str, Any], result: RuleResult) -> None:
    _check_between(result, cfs, ["TempC", "CF_TempC"], 15, 25, "Tuber set requires cool conditions; heat promotes sprouting.", parameter_name="Temperature")
    _check_min(result, cfs, ["CF8_Depth", "Depth", "Soil_Depth"], 50, "Tuber development needs at least 50 cm soil depth.")
    _check_equals(result, cfs, ["CF11_Drainage", "Drainage"], "Good", "Good drainage reduces late blight and total rot risk.")
    _check_between(result, cfs, ["CF5_pH", "pH"], 5.5, 6.5, "This pH range limits scab and wart disease risk.")


_CROP_ID_RULES: Dict[str, RuleFunction] = {
    "CRP0001": _rules_paddy,
    "CRP0002": _rules_maize,
    "CRP0003": _rules_jowar,
    "CRP0004": _rules_bajra,
    "CRP0013": _rules_red_gram,
    "CRP0014": _rules_blackgram,
    "CRP0015": _rules_greengram,
    "CRP0019": _rules_bengal_gram,
    "CRP0020": _rules_lentil,
    "CRP0023": _rules_groundnut,
    "CRP0024": _rules_sunflower,
    "CRP0025": _rules_castor,
    "CRP0026": _rules_mustard,
    "CRP0028": _rules_sesame,
    "CRP0031": _rules_turmeric,
    "CRP0032": _rules_ginger,
    "CRP0033": _rules_garlic,
    "CRP0034": _rules_chilli,
    "CRP0040": _rules_fenugreek,
    "CRP0044": _rules_coriander,
    "CRP0045": _rules_curry_leaves,
    "CRP0058": _rules_tomato,
    "CRP0059": _rules_brinjal,
    "CRP0060": _rules_chilli,
    "CRP0061": _rules_potato,
    "CRP0062": _rules_okra,
    "CRP0063": _rules_onion,
}

_CROP_NAME_RULES: Dict[str, RuleFunction] = {
    "cumin": _rules_cumin,
    "mint": _rules_mint,
    "fennel": _rules_fennel,
    "ajwain": _rules_ajwain,
    "ajwain (carom seeds)": _rules_ajwain,
}


def check_critical_parameters(crop_id: str, cfs: Dict[str, Any]) -> RuleResult:
    """
    Evaluate critical parameters for a crop against the supplied CF values.

    Returns a structured payload containing:
      - warnings: failed-check messages
      - failed_checks: detailed failed checks
      - passed_checks: detailed checks that passed
      - all_passed / failed_count / passed_count
    """
    if not crop_id:
        raise ValueError("crop_id must not be empty")

    rule_fn = _CROP_ID_RULES.get(crop_id)
    if rule_fn is None:
        rule_fn = _CROP_NAME_RULES.get(crop_id.lower().strip())

    if rule_fn is None:
        raise ValueError(
            f"'{crop_id}' has no critical parameters defined. "
            f"Supported IDs: {sorted(_CROP_ID_RULES)} | "
            f"Supported names: {sorted(_CROP_NAME_RULES)}"
        )

    result = _empty_result(crop_id)
    rule_fn(cfs, result)
    return _finalize_result(result)


if __name__ == "__main__":
    sample = check_critical_parameters(
        "CRP0001",
        {
            "CF24_FloodRisk": "Low",
            "CF11_Drainage": "Poor",
            "Water_Regime": "Copious-Irrigation",
        },
    )
    print(sample)
