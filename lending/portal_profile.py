# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Read-only data for the borrower's personal information page.

One login can hold several Customer records -- PORTAL_PLAN.md section 7 -- so this
page shows a section per record rather than pretending there is one identity.

Section 6.3 divides the fields in two. Contact details and address are the borrower's
to correct. Identity is not: the name on the record and the tax id behind it belong to
the verified file, and a borrower editing those would be editing the result of a KYC
check. Everything here is read-only for now; the fields that will accept an edit are
marked, so the write endpoint has an obvious shape when it arrives.
"""

import frappe
from frappe import _

from lending.portal import get_loans, get_portal_customers, shell_payload

CUSTOMER_FIELDS = (
	"name",
	"customer_name",
	"customer_type",
	"tax_id",
	"mobile_no",
	"email_id",
	"customer_primary_contact",
	"customer_primary_address",
)

# What section 6.3 lets a borrower correct. Anything absent from this set is shown but
# never accepted from the browser.
EDITABLE = ("email", "mobile", "phone", "address")


@frappe.whitelist()
def get_profile_page() -> dict:
	"""Every customer record behind this login, with its contact details and address."""
	customers = get_portal_customers()
	loans = get_loans(customers) if customers else []

	records = []
	for name in customers:
		customer = frappe.db.get_value("Customer", name, CUSTOMER_FIELDS, as_dict=True)
		records.extend(identity_rows(customer))
		records.extend(contact_rows(customer))
		records.extend(address_rows(customer))

	payload = shell_payload(_("Personal details"), _("Contact us"), customers, loans)
	payload.update(
		{
			"records": records,
			"records_note": (
				_("Across {0} customer records").format(len(customers))
				if len(customers) > 1
				else _("Your record")
			),
			# Said plainly on the page, so nobody hunts for an edit button that is not
			# there yet and nobody expects to correct a verified field here.
			"edit_note": _(
				"Contact details and address can be corrected. Name and tax id come from "
				"your verified records -- write to us to change those."
			),
		}
	)

	return payload


def row(label: str, value: str, detail: str = "") -> dict:
	return {"label": label, "value": value or _("Not on record"), "detail": detail}


def identity_rows(customer: dict) -> list[dict]:
	return [
		row(_("Name"), customer.customer_name, customer.name),
		row(_("Record type"), customer.customer_type),
		# tax_id is where an Indian install keeps the PAN or GSTIN. Read-only: it is the
		# outcome of a KYC check, not a preference.
		row(_("Tax id"), customer.tax_id),
	]


def primary_contact(customer: dict) -> str | None:
	"""The contact on the customer, or whichever contact links back to it.

	Customer.email_id and mobile_no are fetched from the primary contact rather than
	stored, so the contact is the record to read -- and later, to write.
	"""
	if customer.customer_primary_contact:
		return customer.customer_primary_contact

	links = frappe.get_all(
		"Contact",
		filters=[["Dynamic Link", "link_doctype", "=", "Customer"], ["Dynamic Link", "link_name", "=", customer.name]],
		pluck="name",
		limit=1,
	)

	return links[0] if links else None


def contact_rows(customer: dict) -> list[dict]:
	name = primary_contact(customer)
	if not name:
		return [row(_("Email"), customer.email_id), row(_("Mobile"), customer.mobile_no)]

	contact = frappe.db.get_value(
		"Contact", name, ["email_id", "mobile_no", "phone"], as_dict=True
	)

	return [
		row(_("Email"), contact.email_id or customer.email_id),
		row(_("Mobile"), contact.mobile_no or customer.mobile_no),
		row(_("Phone"), contact.phone),
	]


def primary_address(customer: dict) -> str | None:
	if customer.customer_primary_address:
		return customer.customer_primary_address

	links = frappe.get_all(
		"Address",
		filters=[["Dynamic Link", "link_doctype", "=", "Customer"], ["Dynamic Link", "link_name", "=", customer.name]],
		pluck="name",
		limit=1,
	)

	return links[0] if links else None


def address_rows(customer: dict) -> list[dict]:
	name = primary_address(customer)
	if not name:
		return [row(_("Address"), "")]

	address = frappe.db.get_value(
		"Address",
		name,
		["address_line1", "address_line2", "city", "state", "pincode", "country"],
		as_dict=True,
	)
	parts = [
		address.address_line1,
		address.address_line2,
		address.city,
		address.state,
		address.pincode,
		address.country,
	]

	return [row(_("Address"), ", ".join(part for part in parts if part))]
