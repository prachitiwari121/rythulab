try:
    from rythulab.sheets.extraction_utils import (
        build_all_crops,
        get_scores_from_step1_category,
        get_scores_from_step1_season,
        get_temperature_scores_from_crop_details,
    )
except ModuleNotFoundError:
    from sheets.extraction_utils import (
        build_all_crops,
        get_scores_from_step1_category,
        get_scores_from_step1_season,
        get_temperature_scores_from_crop_details,
    )

SOIL_SCORE_MAP = {
    "P": 5,
    "H": 4,
    "M": 3,
    "S": 2,
    "U": 1,
    "T": 0,
}

WATER_SCORE_MAP = {
    "P": 5,
    "H": 4,
    "M": 3,
    "S": 2,
    "U": 1,
    "T": 0,
}

SEASON_SCORE_MAP = {
    "P": 5,
    "H": 4,
    "M": 3,
    "S": 2,
    "U": 1,
    "T": 0,
}

ALL_CROPS = build_all_crops()


def _sort_crops_by_score(suitable_crops, ordered_crops, n):
    crop_positions = {crop: index for index, crop in enumerate(ordered_crops)}
    suitable_crops.sort(key=lambda item: (-item[1], crop_positions[item[0]]))
    return [crop for crop, _ in suitable_crops[:n]]


def _sort_scored_crops(suitable_crops, ordered_crops, n):
    crop_positions = {crop: index for index, crop in enumerate(ordered_crops)}
    suitable_crops.sort(
        key=lambda item: (-item["weighted_score"], crop_positions[item["crop"]])
    )
    return suitable_crops[:n]


def _get_suitable_crops_from_crop_rows(season, category, n, ordered_crops):
    crop_scores = get_scores_from_step1_season(
        season_key=season,
        agro_climatic_zone=category,
        ordered_crops=ordered_crops,
        score_map=SEASON_SCORE_MAP,
    )
    return _sort_crops_by_score(list(crop_scores.items()), ordered_crops, n)


def get_suitable_crops(soil_texture, n, ordered_crops):
    soil_scores = get_scores_from_step1_category(
        kind="soil",
        category_value=soil_texture,
        ordered_crops=ordered_crops,
        score_map=SOIL_SCORE_MAP,
    )
    return _sort_crops_by_score(list(soil_scores.items()), ordered_crops, n)


def get_suitable_crops_by_water_supply(water_supply_regime, n, ordered_crops):
    water_scores = get_scores_from_step1_category(
        kind="water",
        category_value=water_supply_regime,
        ordered_crops=ordered_crops,
        score_map=WATER_SCORE_MAP,
    )
    return _sort_crops_by_score(list(water_scores.items()), ordered_crops, n)


def get_suitable_crops_by_khariff_zone(agro_climatic_zone, n, ordered_crops):
    return _get_suitable_crops_from_crop_rows(
        season="khariff", category=agro_climatic_zone, n=n, ordered_crops=ordered_crops
    )


def get_suitable_crops_by_perennial_zone(agro_climatic_zone, n, ordered_crops):
    return _get_suitable_crops_from_crop_rows(
        season="perennial", category=agro_climatic_zone, n=n, ordered_crops=ordered_crops
    )


def get_suitable_crops_by_rabi_zone(agro_climatic_zone, n, ordered_crops):
    return _get_suitable_crops_from_crop_rows(
        season="rabi", category=agro_climatic_zone, n=n, ordered_crops=ordered_crops
    )


def get_suitable_crops_by_zaid_zone(agro_climatic_zone, n, ordered_crops):
    return _get_suitable_crops_from_crop_rows(
        season="zaid", category=agro_climatic_zone, n=n, ordered_crops=ordered_crops
    )


def get_suitable_crops_by_conditions(
    soil_texture,
    water_supply_regime,
    season,
    agro_climatic_zone,
    season_weight=1.0,
    water_weight=1.0,
    soil_weight=1.0,
    min_temperature=None,
    max_temperature=None,
    temperature_weight=1.0,
):
    season_methods = {
        "kharif": get_suitable_crops_by_khariff_zone,
        "khariff": get_suitable_crops_by_khariff_zone,
        "perennial": get_suitable_crops_by_perennial_zone,
        "rabi": get_suitable_crops_by_rabi_zone,
        "zaid": get_suitable_crops_by_zaid_zone,
    }

    season_key = season.strip().lower()
    if season_key not in season_methods:
        raise ValueError("Season must be one of: kharif, khariff, perennial, rabi, zaid")

    use_temperature = min_temperature is not None and max_temperature is not None
    total_weight = season_weight + water_weight + soil_weight
    if use_temperature:
        total_weight += temperature_weight
    if total_weight <= 0:
        raise ValueError("The sum of weights must be greater than 0")

    season_scores = get_scores_from_step1_season(
        season_key=season_key,
        agro_climatic_zone=agro_climatic_zone,
        ordered_crops=ALL_CROPS,
        score_map=SEASON_SCORE_MAP,
    )
    water_scores = get_scores_from_step1_category(
        kind="water",
        category_value=water_supply_regime,
        ordered_crops=ALL_CROPS,
        score_map=WATER_SCORE_MAP,
    )
    soil_scores = get_scores_from_step1_category(
        kind="soil",
        category_value=soil_texture,
        ordered_crops=ALL_CROPS,
        score_map=SOIL_SCORE_MAP,
    )
    temperature_scores = (
        get_temperature_scores_from_crop_details(
            min_temperature=min_temperature,
            max_temperature=max_temperature,
            ordered_crops=ALL_CROPS,
        )
        if use_temperature
        else {}
    )

    filtered_crops = []
    for crop in ALL_CROPS:
        if crop not in season_scores or crop not in water_scores or crop not in soil_scores:
            continue
        if use_temperature and crop not in temperature_scores:
            continue

        weighted_average = (
            (season_scores[crop] * season_weight)
            + (water_scores[crop] * water_weight)
            + (soil_scores[crop] * soil_weight)
        ) / total_weight

        if use_temperature:
            weighted_average = (
                (season_scores[crop] * season_weight)
                + (water_scores[crop] * water_weight)
                + (soil_scores[crop] * soil_weight)
                + (temperature_scores[crop] * temperature_weight)
            ) / total_weight

        filtered_crops.append(
            {
                "crop": crop,
                "season_score": season_scores[crop],
                "water_score": water_scores[crop],
                "soil_score": soil_scores[crop],
                "temperature_score": temperature_scores.get(crop),
                "weighted_score": weighted_average,
            }
        )

    return _sort_scored_crops(filtered_crops, ALL_CROPS, len(ALL_CROPS))


if __name__ == "__main__":
    print(
        get_suitable_crops_by_conditions(
            soil_texture="Alluvial/Loam",
            water_supply_regime="Copious-Irrigation",
            season="Kharif",
            agro_climatic_zone="North Coastal",
            min_temperature=24,
            max_temperature=32,
        )
    )
