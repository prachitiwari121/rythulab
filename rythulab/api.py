import frappe
from frappe import _

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
