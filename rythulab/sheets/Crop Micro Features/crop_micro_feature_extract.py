import csv
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CROP_MICRO_FEATURES_DIR = BASE_DIR


def _normalize_mf_codes(mf_codes):
    return sorted(set(mf_codes))


def _extract_mf_codes(raw_value):
    return re.findall(r"MF\d+[A-Z]*", str(raw_value).upper())


def _build_crop_mf_map(column_name, micro_features_dir=CROP_MICRO_FEATURES_DIR):
    micro_features_dir = Path(micro_features_dir)
    crop_mf_map = {}

    for csv_path in sorted(micro_features_dir.glob("*.csv")):
        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                crop_id = str(row.get("CropID", "")).strip()
                if not crop_id:
                    continue

                mf_codes = _extract_mf_codes(row.get(column_name, ""))
                existing = crop_mf_map.get(crop_id, [])
                crop_mf_map[crop_id] = _normalize_mf_codes(existing + mf_codes)

    return crop_mf_map


def get_produced_micro_features_by_cropid(micro_features_dir=CROP_MICRO_FEATURES_DIR):
    return _build_crop_mf_map("Produces (MF List)", micro_features_dir)


def get_required_micro_features_by_cropid(micro_features_dir=CROP_MICRO_FEATURES_DIR):
    return _build_crop_mf_map("Requires (MF List)", micro_features_dir)


def get_suppressed_micro_features_by_cropid(micro_features_dir=CROP_MICRO_FEATURES_DIR):
    return _build_crop_mf_map("Suppresses (MF List)", micro_features_dir)


def get_produced_micro_features_by_crop(micro_features_dir=CROP_MICRO_FEATURES_DIR):
    return get_produced_micro_features_by_cropid(micro_features_dir)


def get_required_micro_features_by_crop(micro_features_dir=CROP_MICRO_FEATURES_DIR):
    return get_required_micro_features_by_cropid(micro_features_dir)


def get_suppressed_micro_features_by_crop(micro_features_dir=CROP_MICRO_FEATURES_DIR):
    return get_suppressed_micro_features_by_cropid(micro_features_dir)
