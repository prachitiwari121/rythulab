# Copyright (c) 2026, Prachi Tiwari and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Crop(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		crop_image: DF.AttachImage | None
		crop_name: DF.Data
		crop_symbol: DF.Literal["", "Diamond", "Hourglass", "Arrow Down", "Circle", "Square", "Cross", "Star", "Heart Drop"]
		crop_type: DF.Literal["Main Crop", "Associated Crop", "Trap Crop", "Creeper Crop"]
		description: DF.TextEditor | None
		growth_duration: DF.Int
		max_spacing: DF.Float
		min_spacing: DF.Float
		row_spacing: DF.Float
		season: DF.Literal["Kharif", "Rabi", "Zaid", "All Season"]
		water_needs: DF.Literal["Low", "Medium", "High"]
	# end: auto-generated types

	pass
