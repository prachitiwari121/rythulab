import frappe
from frappe import _
import csv
import re

# ---------------- FARMER REGISTER ---------------- #

@frappe.whitelist(allow_guest=True)
def register_farmer(
    full_name: str = None,
    email: str = None,
    phone: str = None,
    land_name: str = None,
    land_area: str = None,
    password: str = None
):
    required = {
        "full_name": full_name,
        "email":     email,
        "phone":     phone,
        "password":  password,
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        frappe.throw(_("Missing required fields: {0}").format(", ".join(missing)))

    email     = email.strip().lower()
    full_name = full_name.strip()
    phone     = phone.strip()

    land_name     = land_name.strip() if land_name else ""
    land_area_val = 0.0
    if land_area:
        try:
            land_area_val = float(land_area)
        except Exception:
            land_area_val = 0.0

    if not phone.isdigit() or len(phone) != 10:
        frappe.throw(_("Phone number must be exactly 10 digits."))

    if frappe.db.exists("User", email):
        frappe.throw(_("An account with this email already exists. Please login."))

    role_name = "Farmer Scientist"
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name
        }).insert(ignore_permissions=True)

    try:
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "enabled": 1,
            "new_password": password,
            "send_welcome_email": 0,
            "user_type": "Website User"
        })
        user.append("roles", {"role": role_name})
        user.insert(ignore_permissions=True)

    except frappe.ValidationError as e:
        frappe.throw(_("Unable to create user: {0}").format(str(e)))

    except Exception:
        frappe.log_error(
            title="User Creation Failed",
            message=frappe.get_traceback()
        )
        frappe.throw(_("Something went wrong while creating user."))

    if frappe.db.exists("DocType", "Farmer Profile"):
        meta    = frappe.get_meta("Farmer Profile")
        allowed = {df.fieldname for df in meta.fields}
        profile_data = {"doctype": "Farmer Profile"}
        if "user"      in allowed: profile_data["user"]      = user.name
        if "phone"     in allowed: profile_data["phone"]     = phone
        if "land_name" in allowed: profile_data["land_name"] = land_name
        if "land_area" in allowed: profile_data["land_area"] = land_area_val
        if not frappe.db.exists("Farmer Profile", {"user": user.name}):
            frappe.get_doc(profile_data).insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "ok": True,
        "message": "Farmer registered successfully",
        "user": user.name
    }


# ---------------- LOGIN REDIRECT ---------------- #

@frappe.whitelist()
def login_redirect():
    user = frappe.session.user

    if user == "Administrator":
        return "admin"

    if frappe.db.exists("Has Role", {
        "parent": user, "role": "System Manager", "parenttype": "User"
    }):
        return "admin"

    if frappe.db.exists("Has Role", {
        "parent": user, "role": "Farmer Scientist", "parenttype": "User"
    }):
        return "farmer"

    return "admin"


# ---------------- GET CROPS ---------------- #

@frappe.whitelist()
def get_crops():
    crops = frappe.get_all(
        "Crop",
        fields=[
            "name", "crop_name", "crop_type", "crop_image", "crop_symbol",
            "season", "min_spacing", "max_spacing",
            "row_spacing", "description", "water_needs", "growth_duration"
        ]
    )
    # Make sure image URL is absolute
    for crop in crops:
        if crop.get("crop_image") and not crop["crop_image"].startswith("http"):
            crop["crop_image"] = frappe.utils.get_url(crop["crop_image"])
    return crops


# ---------------- GET MY MODELS ---------------- #

@frappe.whitelist()
def get_my_models():
    user = frappe.session.user
    is_admin = "System Manager" in frappe.get_roles(user) or user == "Administrator"
    filters = {} if is_admin else {"farmer": user}
    models = frappe.get_all(
        "Crop Model",
        filters=filters,
        fields=[
            "name", "model_name", "version", "season", "date",
            "comment", "model_data", "main_crop_reason",
            "associated_crop_reason", "trap_crop_reason", "spacing_reason", "farmer"
        ],
        order_by="modified desc"
    )
    return models


# ---------------- SAVE CROP MODEL ---------------- #

@frappe.whitelist()
def save_crop_model(
    model_name: str = None,
    season: str = None,
    date: str = None,
    comment: str = None,
    version: str = None,
    model_data: str = None,
    main_crop_reason: str = None,
    associated_crop_reason: str = None,
    trap_crop_reason: str = None,
    spacing_reason: str = None,
    existing_name: str = None
):
    user = frappe.session.user

    if not model_name:
        frappe.throw(_("Model name is required."))
    if not season:
        frappe.throw(_("Season is required."))
    if not date:
        frappe.throw(_("Date is required."))

    version_int = int(version) if version else 1

    doc = frappe.get_doc({
        "doctype":                "Crop Model",
        "model_name":             model_name,
        "farmer":                 user,
        "version":                version_int,
        "season":                 season,
        "date":                   date,
        "comment":                comment or "",
        "model_data":             model_data or "{}",
        "main_crop_reason":       main_crop_reason or "",
        "associated_crop_reason": associated_crop_reason or "",
        "trap_crop_reason":       trap_crop_reason or "",
        "spacing_reason":         spacing_reason or "",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"ok": True, "name": doc.name}

@frappe.whitelist()
def delete_crop_model(model_name: str = None):
    if not model_name:
        frappe.throw("Model name required.")
    doc = frappe.get_doc("Crop Model", model_name)
    if doc.farmer != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw("Not authorized.")
    frappe.delete_doc("Crop Model", model_name, ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}


# ---------------- PHASE 1 FEASIBLE CROPS ---------------- #

def _norm_crop_name(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _crop_id_from_name(name: str) -> str:
    clean = re.sub(r"\([^)]*\)", "", (name or "").strip().lower())
    clean = clean.replace("&", " and ").replace("/", " ")
    clean = re.sub(r"[^a-z0-9]+", "_", clean).strip("_")
    return clean or "crop"


def _to_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _build_crop_type_map():
    crop_docs = frappe.get_all("Crop", fields=["crop_name", "crop_type"])
    by_norm = {}
    aliases = {
        "rice": "paddy rice",
        "paddy": "paddy rice",
        "jowar": "jowar sorghum",
        "sorghum": "jowar sorghum",
        "bengal gram": "chickpeas garbanzo beans cicer arietinum",
        "chilli": "chilli commercial",
        "chillies": "chilli commercial",
        "brinjal": "brinjal eggplant",
    }

    for doc in crop_docs:
        crop_name = doc.get("crop_name") or ""
        crop_type = doc.get("crop_type") or "Main Crop"
        norm_name = _norm_crop_name(crop_name)
        if norm_name:
            by_norm[norm_name] = crop_type

    for key, mapped in aliases.items():
        norm_target = _norm_crop_name(mapped)
        if norm_target in by_norm:
            by_norm[_norm_crop_name(key)] = by_norm[norm_target]

    return by_norm


def _build_cropid_map_from_sheet():
    cropid_map = {}
    crop_details_dir = frappe.get_app_path("rythulab", "sheets", "crop_details")

    candidate_names = [
        "0.list of all crops - sheet1.csv",
        "0.list_of_all_crops___sheet1.csv",
        "0_list_of_all_crops_sheet1.csv",
    ]

    list_path = None
    try:
        import os

        files = os.listdir(crop_details_dir)
        lower_to_real = {name.lower(): name for name in files}

        for candidate in candidate_names:
            if candidate in lower_to_real:
                list_path = os.path.join(crop_details_dir, lower_to_real[candidate])
                break

        if not list_path:
            for name in files:
                low = name.lower()
                if low.endswith(".csv") and "list" in low and "crop" in low and "sheet1" in low:
                    list_path = os.path.join(crop_details_dir, name)
                    break
    except Exception:
        list_path = None

    if not list_path:
        list_path = frappe.get_app_path(
            "rythulab",
            "sheets",
            "crop_details",
            "0.List of All crops - Sheet1.csv",
        )

    aliases = {
        "rice": "paddy rice",
        "paddy": "paddy rice",
        "jowar": "jowar sorghum",
        "sorghum": "jowar sorghum",
        "bengal gram": "chickpeas garbanzo beans cicer arietinum",
        "chilli": "chilli commercial",
        "chillies": "chilli commercial",
        "brinjal": "brinjal eggplant",
    }

    with open(list_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            crop_name = (row.get("Crop Name") or "").strip()
            crop_id = (row.get("CropID") or "").strip()
            if not crop_name or not crop_id:
                continue

            norm_name = _norm_crop_name(crop_name)
            if norm_name:
                cropid_map[norm_name] = crop_id

    for key, mapped in aliases.items():
        norm_target = _norm_crop_name(mapped)
        if norm_target in cropid_map:
            cropid_map[_norm_crop_name(key)] = cropid_map[norm_target]

    return cropid_map


@frappe.whitelist()
def get_feasible_crops(
    area: int = None,
    zone: str = None,
    season: str = None,
    soil: str = None,
    waterAvail: str = None,
    waterSupply: str = None,
    wind: str = None,
    minTemp: str = None,
    maxTemp: str = None,
    season_weight: str = None,
    water_weight: str = None,
    soil_weight: str = None,
    temperature_weight: str = None,
):
    from rythulab.phase_1_step_1 import get_suitable_crops_by_conditions
    from rythulab.phase_1_step_3 import get_crop_water_demand_min

    # Support JSON body as well as form/query params
    frappe.logger().info("Enter")
    payload = frappe.request.get_json(silent=True) or {}
    area = area or payload.get("area")
    zone = zone or payload.get("zone")
    season = season or payload.get("season")
    soil = soil or payload.get("soil")
    waterAvail = waterAvail or payload.get("waterAvail")
    waterSupply = waterSupply or payload.get("water_supply")
    wind = wind or payload.get("wind")
    minTemp = minTemp if minTemp is not None else payload.get("minTemp")
    maxTemp = maxTemp if maxTemp is not None else payload.get("maxTemp")
    season_weight = season_weight if season_weight is not None else payload.get("season_weight")
    water_weight = water_weight if water_weight is not None else payload.get("water_weight")
    soil_weight = soil_weight if soil_weight is not None else payload.get("soil_weight")
    temperature_weight = temperature_weight if temperature_weight is not None else payload.get("temperature_weight")

    missing = []
    if not zone:
        missing.append("zone")
    if not season:
        missing.append("season")
    if not soil:
        missing.append("soil")
    if not waterAvail:
        missing.append("waterAvail")
    if not waterSupply:
        missing.append("waterSupply")
    if missing:
        frappe.throw(_("Missing required fields: {0}").format(", ".join(missing)))

    min_temp_val = _to_float(minTemp, default=None)
    max_temp_val = _to_float(maxTemp, default=None)
    season_weight_val = _to_float(season_weight, default=1.0)
    water_weight_val = _to_float(water_weight, default=1.0)
    soil_weight_val = _to_float(soil_weight, default=1.0)
    temperature_weight_val = _to_float(temperature_weight, default=1.0)

    feasible = get_suitable_crops_by_conditions(
        soil_texture=soil,
        water_supply_regime=waterSupply,
        season=season,
        agro_climatic_zone=zone,
        season_weight=season_weight_val,
        water_weight=water_weight_val,
        soil_weight=soil_weight_val,
        min_temperature=min_temp_val,
        max_temperature=max_temp_val,
        temperature_weight=temperature_weight_val,
    )

    crop_type_map = _build_crop_type_map()
    cropid_map = _build_cropid_map_from_sheet()
    crops = []
    for item in feasible:
        crop_name = item.get("crop")
        weighted = float(item.get("weighted_score") or 0.0)
        sc = int(round(max(0.0, min(5.0, weighted)) * 20))
        season_score = float(item.get("season_score") or 0)
        water_score = float(item.get("water_score") or 0)
        soil_score = float(item.get("soil_score") or 0)
        temp_score = item.get("temperature_score")

        norm_name = _norm_crop_name(crop_name)
        crop_type = crop_type_map.get(norm_name, "Main Crop")
        crop_id = cropid_map.get(norm_name) or _crop_id_from_name(crop_name)
        try:
            wr = get_crop_water_demand_min(crop_id)
        except Exception:
            wr = None

        crops.append({
            "id": crop_id,
            "cropid": crop_id,
            "name": crop_name,
            "type": crop_type,
            "wr": wr,
            "sc": sc,
            "sm": season_score > 0,
            "zm": season_score > 0,
            "wm": water_score > 0,
            "som": soil_score > 0,
            "tm": (temp_score is None) or (float(temp_score) > 0),
            "season_score": season_score,
            "water_score": water_score,
            "soil_score": soil_score,
            "temperature_score": temp_score,
            "weighted_score": weighted,
        })

    return {
        "ok": True,
        "farm_context": {
            "area": area,
            "zone": zone,
            "season": season,
            "soil": soil,
            "waterAvail": waterAvail,
            "wind": wind,
            "minTemp": min_temp_val,
            "maxTemp": max_temp_val,
        },
        "crops": crops,
    }


@frappe.whitelist()
def get_phase1_crops(**kwargs):
    # Backward-compatible alias for frontend code already calling this endpoint.
    return get_feasible_crops(**kwargs)
