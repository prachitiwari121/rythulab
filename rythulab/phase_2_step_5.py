import json
from pathlib import Path

try:
	from crop_micro_feature_extract import get_produced_micro_features_by_crop
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
	from crop_micro_feature_extract import get_produced_micro_features_by_crop

try:
	from rythulab.sheets.mf_labels.mf_label_extract import get_mf_label
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "mf_labels"))
	from mf_label_extract import get_mf_label


MICRO_FEATURES_DIR = Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"
WIND_BARRIER_MF_CODE = "MF11"


def get_crops_producing_wind_barrier(micro_features_dir=MICRO_FEATURES_DIR):
	produced_by_crop = get_produced_micro_features_by_crop(micro_features_dir)
	wind_barrier_label = get_mf_label(WIND_BARRIER_MF_CODE)

	crops = [
		{
			"crop": crop_name,
			"reason": f"Produces {wind_barrier_label}",
		}
		for crop_name, produced_mfs in produced_by_crop.items()
		if WIND_BARRIER_MF_CODE in produced_mfs
	]

	crops.sort(key=lambda item: item["crop"])
	return crops


if __name__ == "__main__":
	print(json.dumps(get_crops_producing_wind_barrier(), indent=2))
