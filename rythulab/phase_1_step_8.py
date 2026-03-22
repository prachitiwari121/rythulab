from __future__ import annotations

import csv
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
	from rythulab.sheets.cf_label_extract import get_cf_label
	from rythulab.sheets.mf_labels.mf_label_extract import get_mf_label
except ModuleNotFoundError:
	import sys

	sheets_dir = Path(__file__).resolve().parent / "sheets"
	mf_labels_dir = sheets_dir / "mf_labels"
	sys.path.append(str(sheets_dir))
	sys.path.append(str(mf_labels_dir))

	from cf_label_extract import get_cf_label
	from mf_label_extract import get_mf_label


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
MICRO_FEATURES_DIR = SHEETS_DIR / "Crop Micro Features"
CF_MF_IMPACT_PATH = SHEETS_DIR / "CFvsMF" / "CF_MF_Impact_Matrix - Select CF_MF interactions.csv"
CROP_LIST_PATH = SHEETS_DIR / "crop_details" / "0.List of All crops - Sheet1.csv"
CROP_DETAILS_DIR = SHEETS_DIR / "crop_details"

MF_CODE_RE = re.compile(r"MF\d+(?:-[A-Z]+|[A-Z]*)", re.IGNORECASE)
CF_CODE_RE = re.compile(r"^(CF\d+)", re.IGNORECASE)


def _normalize_text(value: Any) -> str:
	return str(value or "").strip().lower()


def _normalize_mf_code(value: Any) -> str:
	text = str(value or "").strip().upper()
	return re.sub(r"[^A-Z0-9]+", "", text)


def _extract_mf_code_from_header(header: str) -> Optional[str]:
	match = MF_CODE_RE.search(str(header or "").upper())
	if not match:
		return None
	return _normalize_mf_code(match.group(0))


def _extract_cf_number(value: Any) -> Optional[str]:
	match = CF_CODE_RE.match(str(value or "").strip().upper())
	return match.group(1) if match else None


def _safe_float(value: Any) -> Optional[float]:
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


def _extract_status_value(raw_value: Any) -> Any:
	if isinstance(raw_value, dict):
		for key in ("slab", "status", "s", "val", "value"):
			candidate = raw_value.get(key)
			if candidate not in (None, ""):
				return candidate
	return raw_value


def _is_weak_or_very_weak(value: Any) -> bool:
	if value is None:
		return False

	normalized = _normalize_text(value)
	return normalized in {"weak", "very weak"}


def _build_produced_mf_by_cropid(micro_features_dir: Path = MICRO_FEATURES_DIR) -> Dict[str, List[str]]:
	produced_by_cropid: Dict[str, set[str]] = {}

	for csv_path in sorted(Path(micro_features_dir).glob("*.csv")):
		with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
			reader = csv.DictReader(handle)
			for row in reader:
				crop_id = str(row.get("CropID") or "").strip().upper()
				if not crop_id:
					continue

				raw_produced = str(row.get("Produces (MF List)") or "")
				matches = MF_CODE_RE.findall(raw_produced.upper())
				normalized_codes = {_normalize_mf_code(code) for code in matches if code}

				if not normalized_codes:
					continue

				produced_by_cropid.setdefault(crop_id, set()).update(normalized_codes)

	return {crop_id: sorted(values) for crop_id, values in produced_by_cropid.items()}


def _build_negative_cf_mf_links(matrix_path: Path = CF_MF_IMPACT_PATH) -> Dict[str, set[str]]:
	if not Path(matrix_path).exists():
		raise FileNotFoundError(f"CFvsMF sheet not found: {matrix_path}")

	negative_links: Dict[str, set[str]] = {}

	with Path(matrix_path).open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.DictReader(handle)
		fieldnames = reader.fieldnames or []
		if not fieldnames:
			return negative_links

		cf_col = fieldnames[0]
		mf_columns = [name for name in fieldnames[1:] if _extract_mf_code_from_header(name)]

		for row in reader:
			cf_number = _extract_cf_number(row.get(cf_col))
			if not cf_number:
				continue

			for mf_header in mf_columns:
				mf_code = _extract_mf_code_from_header(mf_header)
				if not mf_code:
					continue

				impact_value = _safe_float(row.get(mf_header))
				if impact_value is None or impact_value >= 0:
					continue

				negative_links.setdefault(cf_number, set()).add(mf_code)

	return negative_links


def _build_cropid_to_label_map(crop_list_path: Path = CROP_LIST_PATH) -> Dict[str, str]:
	if not Path(crop_list_path).exists():
		return {}

	mapping: Dict[str, str] = {}
	with Path(crop_list_path).open("r", encoding="utf-8-sig", newline="") as handle:
		reader = csv.DictReader(handle)
		for row in reader:
			crop_id = str(row.get("CropID") or "").strip().upper()
			crop_name = str(row.get("Crop Name") or "").strip()
			if crop_id and crop_name:
				mapping[crop_id] = crop_name

	return mapping


def _is_true_like(value: Any) -> bool:
	normalized = _normalize_text(value)
	return normalized in {"yes", "true", "1", "y"}


def _build_cropid_to_standing_water_requirement_map(
	crop_details_dir: Path = CROP_DETAILS_DIR,
) -> Dict[str, bool]:
	mapping: Dict[str, bool] = {}

	for csv_path in sorted(Path(crop_details_dir).glob("*.csv")):
		if csv_path.name.startswith("0.List"):
			continue

		with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
			reader = csv.reader(handle)
			rows = list(reader)

		if not rows:
			continue

		cropid_row = next(
			(row for row in rows if row and _normalize_text(row[0]) == "cropid"),
			None,
		)
		standing_row = next(
			(
				row
				for row in rows
				if row and "standing water requirement" in _normalize_text(row[0])
			),
			None,
		)

		if not cropid_row or not standing_row:
			continue

		max_len = max(len(cropid_row), len(standing_row))
		for idx in range(1, max_len):
			crop_id = str(cropid_row[idx] if idx < len(cropid_row) else "").strip().upper()
			standing_value = standing_row[idx] if idx < len(standing_row) else ""
			if crop_id:
				mapping[crop_id] = _is_true_like(standing_value)

	return mapping


def _normalize_farm_cfs(farm_cfs: Dict[str, Any]) -> Dict[str, Any]:
	if not isinstance(farm_cfs, dict):
		raise ValueError("farm_cfs must be a JSON object like {'CF1': 'Weak', 'CF2': 'Very Weak'}")

	normalized: Dict[str, Any] = {}

	for key, value in (farm_cfs or {}).items():
		cf_number = _extract_cf_number(key)
		if not cf_number:
			continue
		normalized[cf_number] = _extract_status_value(value)

	return normalized


def check_produced_mf_deterioration_warning(crop_id: str, farm_cfs: Dict[str, Any]) -> Dict[str, Any]:
	crop_id = str(crop_id or "").strip().upper()
	if not crop_id:
		raise ValueError("crop_id must not be empty")

	crop_label = _build_cropid_to_label_map().get(crop_id, crop_id)
	standing_water_required = _build_cropid_to_standing_water_requirement_map().get(crop_id, False)

	produced_by_cropid = _build_produced_mf_by_cropid()
	produced_mfs = produced_by_cropid.get(crop_id, [])

	if not produced_mfs:
		return {
			"crop_id": crop_id,
			"crop_label": crop_label,
			"has_warning": False,
			"warning_count": 0,
			"warnings": [],
			"produced_mfs": [],
			"message": f"No produced microfeatures found for crop '{crop_label}'.",
		}

	negative_cf_mf_links = _build_negative_cf_mf_links()
	normalized_farm_cfs = _normalize_farm_cfs(farm_cfs)

	warnings: List[Dict[str, Any]] = []
	seen = set()

	for cf_code, negative_mfs in negative_cf_mf_links.items():
		if standing_water_required and cf_code == "CF11":
			continue

		farm_value = normalized_farm_cfs.get(cf_code)
		if not _is_weak_or_very_weak(farm_value):
			continue

		for mf_code in produced_mfs:
			if mf_code not in negative_mfs:
				continue

			dedupe_key = (cf_code, mf_code)
			if dedupe_key in seen:
				continue
			seen.add(dedupe_key)

			cf_label = get_cf_label(cf_code)
			mf_label = get_mf_label(mf_code)

			warnings.append(
				{
					"cf_code": cf_code,
					"cf_label": cf_label,
					"farm_cf_value": farm_value,
					"mf_code": mf_code,
					"mf_label": mf_label,
					"message": (
						f"{crop_label}: produced microfeature {mf_code} ({mf_label}) has negative impact "
						f"on {cf_code} ({cf_label}), while farm CF is already "
						f"{farm_value} (Weak/Very Weak)."
					),
				}
			)

	return {
		"crop_id": crop_id,
		"crop_label": crop_label,
		"produced_mfs": produced_mfs,
		"warning_count": len(warnings),
		"warnings": warnings,
		"has_warning": len(warnings) > 0,
	}


if __name__ == "__main__":
	sample_crop_id = "CRP0001"
	sample_farm_cfs = {
		"CF1": "Very Weak",
		"CF4": "Weak",
		"CF9": "Very Weak",
		"CF12": "Very Weak",
		"CF20": "Moderate",
		"CF22": "Very Weak",
	}

	result = check_produced_mf_deterioration_warning(sample_crop_id, sample_farm_cfs)
	print(json.dumps(result, indent=2, ensure_ascii=False))

