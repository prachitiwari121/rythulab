import csv
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
FARMS_DIR = BASE / "sheets" / "Farms"
LEGEND_PATH = FARMS_DIR / "AP_RealVillage_FarmProfiles - ranges legend.csv"
PROFILE_PATH = FARMS_DIR / "AP_RealVillage_FarmProfiles - AP_RealVillage_FarmProfiles.csv"

CLASS_ORDER = ["Very Weak", "Weak", "Moderate", "Good", "Ideal"]
CLASS_EVAL_ORDER = ["Ideal", "Good", "Moderate", "Weak", "Very Weak"]

MONTH_TO_NUM = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

PARAM_TO_COLUMN = {
    "pH": "pH",
    "N_Pct (%)": "Farm N%",
    "P_kgha (kg/ha)": "P_kgha",
    "K_kgha (kg/ha)": "K_kgha",
    "OC_Pct (%)": "OC_Pct",
    "EC_dSm (dS/m)": "EC_dSm",
    "Depth_cm (cm)": "Depth_cm",
    "WHC_Pct (%)": "WHC_Pct",
    "Compaction": "Compaction",
    "BulkDensity_gcc (g/cc)": "BulkDensity_gcc",
    "Drainage": "Drainage",
    "ErosionRisk": "ErosionRisk",
    "GWDepth_m (m)": "GWDepth_m",
    "Water_mm/ha (season)": "Water_mm/ha",
    "Water_Regime": "Water_Regime",
    "RainReliability": "RainReliability",
    "TempC (season mean)": "TempC",
    "HeatDays (>40°C)": "HeatDays",
    "FrostRisk": "FrostRisk",
    "Wind_kmph (max)": "Wind_kmph",
    "BioIndex": "BioIndex",
    "PestPressure": "PestPressure",
    "Earthworms": "Earthworms",
    "Slope_pct (%)": "Slope_pct",
    "FloodRisk": "FloodRisk",
    "DroughtRisk": "DroughtRisk",
    "Ca_meq (meq/100g)": "Ca_meq",
}


def norm_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def extract_numbers(value: str) -> list[float]:
    text = str(value or "").lower()
    for mon, num in MONTH_TO_NUM.items():
        text = re.sub(rf"\b{mon}\b", str(num), text)
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]


def parse_value_as_number(value: str):
    nums = extract_numbers(value)
    if not nums:
        return None
    if len(nums) >= 2 and "-" in str(value):
        return (nums[0] + nums[1]) / 2
    return nums[0]


def token_matches_numeric(token: str, num_value: float) -> bool:
    token = token.strip()
    if not token:
        return False

    token_norm = token.replace("–", "-").replace("—", "-")

    if token_norm.startswith("<"):
        nums = extract_numbers(token_norm)
        return bool(nums) and num_value < nums[0]
    if token_norm.startswith(">"):
        nums = extract_numbers(token_norm)
        return bool(nums) and num_value > nums[0]

    if "-" in token_norm:
        nums = extract_numbers(token_norm)
        if len(nums) >= 2:
            low, high = nums[0], nums[1]
            return low <= num_value <= high

    nums = extract_numbers(token_norm)
    if len(nums) == 1:
        return abs(num_value - nums[0]) < 1e-9

    return False


def token_matches_text(token: str, text_value: str) -> bool:
    token = token.strip()
    if not token:
        return False

    token_norm = norm_text(token)
    value_norm = norm_text(text_value)
    if not token_norm or not value_norm:
        return False

    if token_norm == value_norm:
        return True

    for part in re.split(r"/", token):
        p = norm_text(part)
        if p and (p == value_norm or p in value_norm or value_norm in p):
            return True

    return token_norm in value_norm or value_norm in token_norm


def matches_rule(cell_rule: str, raw_value: str) -> bool:
    tokens = [t.strip() for t in str(cell_rule or "").split(",") if t.strip()]
    if not tokens:
        return False

    numeric_value = parse_value_as_number(raw_value)
    for token in tokens:
        if numeric_value is not None and token_matches_numeric(token, numeric_value):
            return True
        if token_matches_text(token, raw_value):
            return True
    return False


def classify_value(rules_by_class: dict[str, str], raw_value: str) -> str:
    for cls in CLASS_EVAL_ORDER:
        if matches_rule(rules_by_class.get(cls, ""), raw_value):
            return cls
    return ""


def load_legend_rules(path: Path):
    rules = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            param = (row.get("Parameter") or "").strip()
            if not param:
                continue
            rules[param] = {cls: (row.get(cls) or "").strip() for cls in CLASS_ORDER}
    return rules


def main():
    legend_rules = load_legend_rules(LEGEND_PATH)

    with PROFILE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        original_fields = reader.fieldnames or []

    new_columns = []
    for param, profile_col in PARAM_TO_COLUMN.items():
        if param not in legend_rules:
            continue
        class_col = f"{profile_col}_Class"
        new_columns.append((param, profile_col, class_col))

    for row in rows:
        for param, profile_col, class_col in new_columns:
            raw_value = row.get(profile_col, "")
            row[class_col] = classify_value(legend_rules[param], raw_value)

    fieldnames = list(original_fields)
    for _, _, class_col in new_columns:
        if class_col not in fieldnames:
            fieldnames.append(class_col)

    output_path = PROFILE_PATH
    try:
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except PermissionError:
        output_path = PROFILE_PATH.with_name(
            PROFILE_PATH.stem + " - with classes" + PROFILE_PATH.suffix
        )
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Updated {output_path.name} with {len(new_columns)} class columns.")


if __name__ == "__main__":
    main()
