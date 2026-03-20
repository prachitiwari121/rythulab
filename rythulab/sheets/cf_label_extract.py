import csv
import re
from pathlib import Path


CF_FARM_FEATURES_PATH = (
    Path(__file__).resolve().parent
    / "cf_labels"
    / "crop suitability sheets - Farm context features.csv"
)

STATUS_COLUMNS = ["Very Weak", "Weak", "Moderate", "Good", "Ideal"]


def _extract_cf_number(cf_code):
    """Extract the numeric prefix from a CF code like 'CF1_N' or 'CF11_Drainage' -> 'CF1', 'CF11'."""
    match = re.match(r"(CF\d+)", str(cf_code).strip().upper())
    return match.group(1) if match else None


def build_cf_info_map(farm_features_path=CF_FARM_FEATURES_PATH):
    """
    Parses the Farm context features CSV and builds a map keyed by CF number.

    Returns:
        {
            "CF1": {
                "cf_number": "CF1",
                "label": "Available Nitrogen",
                "unit": "kg/ha",
                "status_ranges": {
                    "Very Weak": "<100",
                    "Weak": "100–150",
                    ...
                }
            },
            ...
        }
    """
    farm_features_path = Path(farm_features_path)
    cf_info_map = {}

    with farm_features_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            cf_number = str(row.get("CF No", "")).strip()
            if not cf_number:
                continue

            cf_info_map[cf_number.upper()] = {
                "cf_number": cf_number.upper(),
                "label": str(row.get("Context Feature", "")).strip(),
                "unit": str(row.get("Unit", "")).strip(),
                "status_ranges": {
                    status: str(row.get(status, "")).strip()
                    for status in STATUS_COLUMNS
                },
            }

    return cf_info_map


def build_cf_label_map(farm_features_path=CF_FARM_FEATURES_PATH):
    """
    Returns a map from CF number (e.g. 'CF1') to its human-readable label.
    e.g. { "CF1": "Available Nitrogen", "CF9": "Water Holding Capacity", ... }
    """
    return {
        cf_number: info["label"]
        for cf_number, info in build_cf_info_map(farm_features_path).items()
    }


def build_label_to_cf_number_map(farm_features_path=CF_FARM_FEATURES_PATH):
    """
    Returns a reverse map from label to CF number.
    e.g. { "Available Nitrogen": "CF1", "Water Holding Capacity": "CF9", ... }
    """
    return {
        info["label"]: cf_number
        for cf_number, info in build_cf_info_map(farm_features_path).items()
    }


def get_cf_label(cf_code, farm_features_path=CF_FARM_FEATURES_PATH):
    """
    Returns the human-readable label for a CF code like 'CF1_N' or 'CF1'.
    Falls back to the input code if no match is found.
    """
    cf_number = _extract_cf_number(cf_code)
    if not cf_number:
        return cf_code
    return build_cf_label_map(farm_features_path).get(cf_number, cf_code)


def resolve_cf_input(farm_cf_values, farm_features_path=CF_FARM_FEATURES_PATH):
    """
    Normalizes user-provided farm CF values so keys are always the full CF codes
    from the impact matrix (e.g. 'CF1_N'). Accepts any of:
      - Full CF code with suffix:  'CF1_N'
      - Bare CF number:            'CF1'
      - Human-readable label:      'Available Nitrogen'

    Returns:
        A dict keyed by the original cf_code as provided (unchanged), with
        an added 'cf_label' resolved from the Farm context features file.
    """
    label_to_cf_number = build_label_to_cf_number_map(farm_features_path)
    cf_label_map = build_cf_label_map(farm_features_path)

    resolved = {}
    for key, status in farm_cf_values.items():
        key_stripped = str(key).strip()

        # If it looks like a label (not starting with CF), try reversing via label map
        if not re.match(r"CF\d+", key_stripped, re.IGNORECASE):
            cf_number = label_to_cf_number.get(key_stripped)
            if cf_number:
                resolved[cf_number] = status
                continue
            # Unrecognized key — pass through as-is
            resolved[key_stripped] = status
        else:
            resolved[key_stripped.upper()] = status

    return resolved


def annotate_cf_code(cf_code, farm_features_path=CF_FARM_FEATURES_PATH):
    """Returns a dict with cf_code and its human-readable label."""
    return {
        "cf_code": cf_code,
        "cf_label": get_cf_label(cf_code, farm_features_path),
    }
