import json
from pathlib import Path

try:
	from crop_micro_feature_extract import get_produced_micro_features_by_cropid
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
	from crop_micro_feature_extract import get_produced_micro_features_by_cropid

try:
	from rythulab.sheets.mf_labels.mf_label_extract import get_mf_label
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "mf_labels"))
	from mf_label_extract import get_mf_label

try:
	from rythulab.sheets.extraction_utils import get_cropid_to_name_map
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets"))
	from extraction_utils import get_cropid_to_name_map

try:
	from rythulab.phase_1_step_1 import load_step1_results
except ModuleNotFoundError:
	from phase_1_step_1 import load_step1_results


MICRO_FEATURES_DIR = Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"
WIND_BARRIER_MF_CODE = "MF11"


def get_crops_producing_wind_barrier(micro_features_dir=MICRO_FEATURES_DIR):
	produced_by_cropid = get_produced_micro_features_by_cropid(micro_features_dir)
	cropid_to_name = get_cropid_to_name_map()
	step1_scores = load_step1_results()
	wind_barrier_label = get_mf_label(WIND_BARRIER_MF_CODE)

	crops = [
		{
			"crop_id": crop_id,
			"crop": cropid_to_name.get(crop_id, crop_id),
			"step1_score": step1_scores.get(crop_id),
			"reason": f"Produces {wind_barrier_label}",
		}
		for crop_id, produced_mfs in produced_by_cropid.items()
		if WIND_BARRIER_MF_CODE in produced_mfs
		and (not step1_scores or crop_id in step1_scores)
	]

	crops.sort(key=lambda item: item["crop"])
	return crops


if __name__ == "__main__":
	print(json.dumps(get_crops_producing_wind_barrier(), indent=2))
