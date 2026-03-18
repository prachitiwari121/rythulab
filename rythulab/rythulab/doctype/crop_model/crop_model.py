# Copyright (c) 2026, Prachi Tiwari and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CropModel(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		associated_crop_reason: DF.SmallText | None
		comment: DF.SmallText | None
		date: DF.Date
		farmer: DF.Link
		main_crop_reason: DF.SmallText | None
		model_data: DF.LongText | None
		model_name: DF.Data
		season: DF.Literal["Kharif", "Rabi", "Zaid", "All Season"]
		spacing_reason: DF.SmallText | None
		trap_crop_reason: DF.SmallText | None
		version: DF.Int
	# end: auto-generated types

	pass
