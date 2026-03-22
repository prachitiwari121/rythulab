from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR.parent
MICRO_FEATURES_DIR = SHEETS_DIR / "Crop Micro Features"
MF_LEGEND_PATH = BASE_DIR / "AP-Crops-Micro-Features.xlsx - MF Legend.csv"
MF_LIST_COLUMNS = (
    "Produces (MF List)",
    "Requires (MF List)",
    "Suppresses (MF List)",
)


def normalize_mf_code(mf_code: object) -> str:
    return str(mf_code or "").strip().upper()


def _normalize_legend_path(legend_path: Path | str = MF_LEGEND_PATH) -> Path:
    return Path(legend_path).resolve()


@lru_cache(maxsize=None)
def _build_mf_label_map_cached(legend_path_str: str) -> dict[str, str]:
    legend_path = Path(legend_path_str)
    mf_label_map: dict[str, str] = {}

    with legend_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            mf_code = normalize_mf_code(row.get("MF Code", ""))
            feature_name = str(row.get("Feature Name", "")).strip()
            if not mf_code:
                continue

            mf_label_map[mf_code] = feature_name or mf_code

    return mf_label_map


def build_mf_label_map(legend_path: Path | str = MF_LEGEND_PATH) -> dict[str, str]:
    return dict(_build_mf_label_map_cached(str(_normalize_legend_path(legend_path))))


def parse_mf_codes(mf_codes: object) -> List[str]:
    if mf_codes is None:
        return []

    if isinstance(mf_codes, str):
        values = mf_codes.split(",")
    elif isinstance(mf_codes, Iterable):
        values = list(mf_codes)
    else:
        values = [mf_codes]

    parsed: List[str] = []
    for value in values:
        normalized = normalize_mf_code(value)
        if normalized:
            parsed.append(normalized)
    return parsed


def get_mf_label(mf_code: object, legend_path: Path | str = MF_LEGEND_PATH) -> str:
    normalized = normalize_mf_code(mf_code)
    if not normalized:
        return ""
    return build_mf_label_map(legend_path).get(normalized, normalized)


def annotate_mf_codes(mf_codes: Iterable[object], legend_path: Path | str = MF_LEGEND_PATH):
    mf_label_map = build_mf_label_map(legend_path)
    normalized_codes = sorted(set(parse_mf_codes(mf_codes)))
    return [
        {
            "mf_code": mf_code,
            "mf_label": mf_label_map.get(mf_code, mf_code),
        }
        for mf_code in normalized_codes
    ]


def iter_micro_feature_sheet_paths(micro_features_dir: Path | str = MICRO_FEATURES_DIR) -> List[Path]:
    micro_features_path = Path(micro_features_dir)
    if not micro_features_path.exists():
        return []
    return sorted(micro_features_path.glob("*.csv"))


def extract_mf_codes_from_sheet(sheet_path: Path | str) -> List[str]:
    sheet_path = Path(sheet_path)
    discovered_codes: set[str] = set()

    with sheet_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            for column in MF_LIST_COLUMNS:
                discovered_codes.update(parse_mf_codes(row.get(column, "")))

    return sorted(discovered_codes)


def extract_all_mf_codes(micro_features_dir: Path | str = MICRO_FEATURES_DIR) -> List[str]:
    discovered_codes: set[str] = set()
    for sheet_path in iter_micro_feature_sheet_paths(micro_features_dir):
        discovered_codes.update(extract_mf_codes_from_sheet(sheet_path))
    return sorted(discovered_codes)


def annotate_all_mf_codes(
    micro_features_dir: Path | str = MICRO_FEATURES_DIR,
    legend_path: Path | str = MF_LEGEND_PATH,
):
    return annotate_mf_codes(extract_all_mf_codes(micro_features_dir), legend_path)
