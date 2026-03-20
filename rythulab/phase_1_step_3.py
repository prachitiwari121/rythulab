try:
    from rythulab.sheets.extraction_utils import get_crop_water_demand_min_by_crop_id
except ModuleNotFoundError:
    from sheets.extraction_utils import get_crop_water_demand_min_by_crop_id


def get_crop_water_demand_min(crop_id: str):
    return get_crop_water_demand_min_by_crop_id(crop_id)


if __name__ == "__main__":
    sample_crop_id = "CRP0001"
    print({
        "crop_id": sample_crop_id,
        "water_demand_min_mm_per_season_per_hectare": get_crop_water_demand_min(sample_crop_id),
    })
