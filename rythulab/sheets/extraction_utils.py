from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

STEP1_DIR = Path(__file__).resolve().parent / "step1"
CROP_DETAILS_DIR = Path(__file__).resolve().parent / "crop_details"

STEP1_FILES = {
    "soil": "crop suitability sheets - soil type_texture.csv",
    "water": "crop suitability sheets - water supply regime_water texture.csv",
    "kharif": "crop suitability sheets - khariff agro-climatic zone.csv",
    "khariff": "crop suitability sheets - khariff agro-climatic zone.csv",
    "perennial": "crop suitability sheets - perennial.csv",
    "rabi": "crop suitability sheets - rabi.csv",
    "zaid": "crop suitability sheets - zaid.csv",
}

CROP_NAME_ALIASES = {
    "paddy": "Rice",
    "rice": "Rice",
    "paddy rice": "Rice",
    "chilli": "Chilli",
    "chillies": "Chilli",
    "bengalgram": "Bengal Gram",
    "bengal gram": "Bengal Gram",
    "blackgram": "Black Gram",
    "black gram": "Black Gram",
    "blackgram urd": "Black Gram",
    "greengram": "Green Gram",
    "green gram": "Green Gram",
    "greengram mung": "Green Gram",
    "redgram": "Red Gram",
    "red gram": "Red Gram",
    "redgram tur arhar": "Red Gram",
    "banmboo": "Bamboo",
    "eucaplyptus": "Eucalyptus",
}


def _safe_str(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def canonicalize_crop_name(name: object) -> Optional[str]:
    raw = _safe_str(name)
    if not raw:
        return None

    alias_key = re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()
    return CROP_NAME_ALIASES.get(alias_key, raw)


def _sheet_path(file_name: str, folder: Path) -> Path:
    path = folder / file_name
    if not path.exists():
        raise FileNotFoundError(f"Sheet not found: {path}")
    return path


def _normalize_score(value: object) -> str:
    score = _safe_str(value).upper()
    return score if score in {"P", "H", "M", "S", "U", "T"} else ""


def _extract_scores_from_crop_rows(
    df: pd.DataFrame,
    category: str,
    ordered_crops: List[str],
    score_map: Dict[str, int],
) -> Dict[str, int]:
    if "Crop" not in df.columns:
        raise ValueError("Expected 'Crop' column in row-oriented sheet")
    if category not in df.columns:
        raise ValueError(f"Category '{category}' not found in sheet")

    canonical_rows = {
        canonicalize_crop_name(crop): index
        for index, crop in enumerate(df["Crop"].tolist())
        if canonicalize_crop_name(crop)
    }

    scores: Dict[str, int] = {}
    for crop in ordered_crops:
        idx = canonical_rows.get(crop)
        if idx is None:
            continue

        suitability = _normalize_score(df.iloc[idx][category])
        if not suitability or suitability == "T":
            continue
        scores[crop] = score_map[suitability]

    return scores


def _extract_scores_from_category_row(
    df: pd.DataFrame,
    selector_column: str,
    selector_value: str,
    ordered_crops: List[str],
    score_map: Dict[str, int],
) -> Dict[str, int]:
    first_col = df.columns[0]
    if first_col != selector_column:
        raise ValueError(f"Expected selector column '{selector_column}', found '{first_col}'")

    row = df[df[first_col].astype(str).str.lower() == selector_value.lower()]
    if row.empty:
        raise ValueError(f"Value '{selector_value}' not found in '{selector_column}'")

    row = row.iloc[0]
    canonical_columns = {
        canonicalize_crop_name(col): col
        for col in df.columns[1:]
        if canonicalize_crop_name(col)
    }

    scores: Dict[str, int] = {}
    for crop in ordered_crops:
        src_col = canonical_columns.get(crop)
        if not src_col:
            continue

        suitability = _normalize_score(row[src_col])
        if not suitability or suitability == "T":
            continue
        scores[crop] = score_map[suitability]

    return scores


def build_all_crops(step1_dir: Path = STEP1_DIR) -> List[str]:
    all_crops: List[str] = []
    seen = set()

    for file_name in {
        STEP1_FILES["soil"],
        STEP1_FILES["water"],
        STEP1_FILES["kharif"],
        STEP1_FILES["perennial"],
        STEP1_FILES["rabi"],
        STEP1_FILES["zaid"],
    }:
        df = pd.read_csv(_sheet_path(file_name, step1_dir))
        if "Crop" in df.columns:
            source = df["Crop"].tolist()
        else:
            source = list(df.columns[1:])

        for crop in source:
            canonical = canonicalize_crop_name(crop)
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            all_crops.append(canonical)

    return all_crops


def get_scores_from_step1_season(
    season_key: str,
    agro_climatic_zone: str,
    ordered_crops: List[str],
    score_map: Dict[str, int],
    step1_dir: Path = STEP1_DIR,
) -> Dict[str, int]:
    key = season_key.strip().lower()
    if key not in STEP1_FILES:
        raise ValueError(f"Unknown season key: {season_key}")

    file_path = _sheet_path(STEP1_FILES[key], step1_dir)
    df = pd.read_csv(file_path)
    return _extract_scores_from_crop_rows(df, agro_climatic_zone, ordered_crops, score_map)


def get_scores_from_step1_category(
    kind: str,
    category_value: str,
    ordered_crops: List[str],
    score_map: Dict[str, int],
    step1_dir: Path = STEP1_DIR,
) -> Dict[str, int]:
    kind_key = kind.strip().lower()
    if kind_key == "soil":
        file_name = STEP1_FILES["soil"]
        selector_column = "Soil_Type_Texture"
    elif kind_key == "water":
        file_name = STEP1_FILES["water"]
        selector_column = "WaterSupplyRegime"
    else:
        raise ValueError("kind must be either 'soil' or 'water'")

    df = pd.read_csv(_sheet_path(file_name, step1_dir))

    if "Crop" in df.columns and category_value in df.columns:
        return _extract_scores_from_crop_rows(df, category_value, ordered_crops, score_map)

    return _extract_scores_from_category_row(
        df,
        selector_column,
        category_value,
        ordered_crops,
        score_map,
    )


def normalize_temperature_bounds(min_temperature: float, max_temperature: float) -> Tuple[float, float]:
    low = float(min_temperature)
    high = float(max_temperature)
    if low > high:
        low, high = high, low
    return low, high


def extract_temperature_range(value: object) -> Optional[Tuple[float, float]]:
    matches = re.findall(r"\d+(?:\.\d+)?", _safe_str(value))
    if len(matches) < 2:
        return None
    return normalize_temperature_bounds(float(matches[0]), float(matches[1]))


def calculate_temperature_deviation(
    given_range: Tuple[float, float], recommended_range: Tuple[float, float]
) -> float:
    given_min, given_max = given_range
    rec_min, rec_max = recommended_range

    lower_deviation = given_min - rec_min
    upper_deviation = given_max - rec_max
    return max(lower_deviation, upper_deviation)


def temperature_score_from_deviation(deviation: float) -> int:
    if deviation < 0:
        return 5
    if deviation < 3:
        return 4
    if deviation < 6:
        return 3
    if deviation < 9:
        return 2
    if deviation < 12:
        return 1
    return 0


def get_temperature_scores_from_crop_details(
    min_temperature: float,
    max_temperature: float,
    ordered_crops: List[str],
    crop_details_dir: Path = CROP_DETAILS_DIR,
) -> Dict[str, float]:
    requested_range = normalize_temperature_bounds(min_temperature, max_temperature)
    scores: Dict[str, float] = {}

    for csv_path in sorted(crop_details_dir.glob("*.csv")):
        if csv_path.name.startswith("0.List"):
            continue

        df = pd.read_csv(csv_path)
        if df.empty or len(df.columns) < 2:
            continue

        parameter_col = df.columns[0]
        temp_rows = df[df[parameter_col].astype(str).str.lower().str.contains("temp", na=False)]
        if temp_rows.empty:
            continue

        canonical_columns = {
            canonicalize_crop_name(col): col
            for col in df.columns[1:]
            if canonicalize_crop_name(col)
        }

        for _, row in temp_rows.iterrows():
            for crop in ordered_crops:
                src_col = canonical_columns.get(crop)
                if not src_col:
                    continue

                crop_range = extract_temperature_range(row[src_col])
                if not crop_range:
                    continue

                deviation = calculate_temperature_deviation(requested_range, crop_range)
                score = temperature_score_from_deviation(deviation)
                scores[crop] = max(scores.get(crop, 0), score)

    return scores


def _extract_first_numeric(value: object) -> Optional[float]:
    matches = re.findall(r"\d+(?:\.\d+)?", _safe_str(value))
    if not matches:
        return None
    return float(matches[0])


def get_cropid_to_name_map(crop_details_dir: Path = CROP_DETAILS_DIR) -> Dict[str, str]:
    list_file = crop_details_dir / "0.List of All crops - Sheet1.csv"
    if not list_file.exists():
        raise FileNotFoundError(f"Sheet not found: {list_file}")

    df = pd.read_csv(list_file)
    required = {"CropID", "Crop Name"}
    if not required.issubset(set(df.columns)):
        raise ValueError("0.List sheet must contain 'CropID' and 'Crop Name' columns")

    mapping: Dict[str, str] = {}
    for _, row in df.iterrows():
        crop_id = _safe_str(row.get("CropID"))
        crop_name = _safe_str(row.get("Crop Name"))
        if crop_id and crop_name:
            mapping[crop_id] = crop_name
    return mapping


def get_crop_water_demand_min_by_crop_id(
    crop_id: str,
    crop_details_dir: Path = CROP_DETAILS_DIR,
) -> Optional[float]:
    if not crop_id:
        raise ValueError("crop_id is required")

    cropid_to_name = get_cropid_to_name_map(crop_details_dir)
    target_name = cropid_to_name.get(crop_id)
    if not target_name:
        raise ValueError(f"CropID '{crop_id}' not found in crop_details list sheet")

    target_canonical = canonicalize_crop_name(target_name)
    if not target_canonical:
        raise ValueError(f"Unable to canonicalize crop name for CropID '{crop_id}'")

    for csv_path in sorted(crop_details_dir.glob("*.csv")):
        if csv_path.name.startswith("0.List"):
            continue

        df = pd.read_csv(csv_path)
        if df.empty or len(df.columns) < 2:
            continue

        parameter_col = df.columns[0]
        water_rows = df[
            df[parameter_col]
            .astype(str)
            .str.lower()
            .str.contains("water demand value", na=False)
        ]
        if water_rows.empty:
            continue

        canonical_columns = {
            canonicalize_crop_name(col): col
            for col in df.columns[1:]
            if canonicalize_crop_name(col)
        }
        src_col = canonical_columns.get(target_canonical)
        if not src_col:
            continue

        for _, row in water_rows.iterrows():
            min_value = _extract_first_numeric(row.get(src_col))
            if min_value is not None:
                return min_value

    return None
