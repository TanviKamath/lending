# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The public front of the borrower portal: apply, and track what you applied for.

These are the only two endpoints a stranger can reach, which PORTAL_PLAN.md section 8
caps deliberately. Both are rate limited by IP because both are public and one of them
writes rows. Neither accepts a doctype or a fieldname from the browser: every field is
read by name from a fixed list, and Loan Lead is inserted with ignore_permissions
because the doctype grants create rights to System Manager only.

Tracking matches the reference number AND the mobile number before it answers, and
returns the same refusal whether the reference is wrong, the mobile is wrong, or the
application does not exist. A tracker that distinguishes those cases is a tool for
guessing other people's reference numbers.

No OTP step. The Loan Lead OTP fields were removed by patch
v16_0/remove_loan_lead_otp_fields.py, so verification is new work rather than reuse --
section 6.1 defers it, and mobile_verification_status stays Pending on a portal lead.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt

from lending.portal import brand_name, long_date, money

LEAD_SOURCE = "Portal"

# The only fields a visitor may fill. Anything else on Loan Lead is ours to set.
LEAD_FIELDS = ("applicant_name", "email", "mobile_number", "loan_product", "loan_amount")
OPTIONAL_LEAD_FIELDS = ("income", "proposed_tenure", "employment_type", "applicant_country")

EMPLOYMENT_TYPES = ("Salaried", "Self-employed")

# Loan Lead.mobile_number is a Phone field, which frappe rejects without a country
# code. A portal visitor should not have to know that, so a bare number gets the
# default prefix. PORTAL_PLAN.md section 9 puts portal settings on Lending Settings;
# this belongs there once those fields exist.
DEFAULT_COUNTRY_CODE = "+91"
NATIONAL_NUMBER_LENGTH = 10

# Loan Lead.applicant_type is Individual or Business; a portal visitor is a person.
APPLICANT_TYPE = "Individual"


@frappe.whitelist(allow_guest=True)
def get_apply_page() -> dict:
	"""Products a visitor can apply for, with the rate and ceiling for each."""
	products = frappe.get_all(
		"Loan Product",
		filters={"disabled": 0},
		fields=["name", "rate_of_interest", "maximum_loan_amount", "is_term_loan"],
		order_by="name asc",
	)

	return {
		"brand_name": brand_name(),
		"products": [
			{
				"label": row.name,
				"value": _("{0}% p.a.").format(flt(row.rate_of_interest, 2)),
				"detail": _("Up to {0}").format(money(row.maximum_loan_amount)),
			}
			for row in products
		],
		"products_note": _("{0} products available").format(len(products)),
		"options": [{"label": row.name, "value": row.name} for row in products],
		"heading": _("Apply for a loan"),
		"intro": _(
			"Tell us what you need and we will show you an indicative offer straight away. "
			"It costs you nothing and does not affect your credit score."
		),
	}


@frappe.whitelist(allow_guest=True)
def get_track_page() -> dict:
	"""Copy for the public tracker. It needs no records, only words.

	A data script runs under safe_exec, where _() is unavailable, so even a page whose
	content is entirely static reads its wording from here to stay translatable.
	"""
	return {
		"brand_name": brand_name(),
		"heading": _("Track your application"),
		"intro": _("Enter your reference number and the mobile number you applied with."),
	}


def clean(value) -> str:
	return frappe.utils.strip_html(str(value or "")).strip()


def with_country_code(number: str) -> str:
	"""A Phone field needs a country code; a visitor types the number they know."""
	digits = "".join(character for character in number if character.isdigit() or character == "+")

	if digits.startswith("+"):
		return digits

	bare = digits.lstrip("0")
	if len(bare) != NATIONAL_NUMBER_LENGTH:
		frappe.throw(_("Please give a valid mobile number."), frappe.ValidationError)

	return f"{DEFAULT_COUNTRY_CODE}{bare}"


def read_submission() -> dict:
	"""Pull the known fields out of the request and refuse anything short of complete."""
	data = {field: clean(frappe.form_dict.get(field)) for field in LEAD_FIELDS}

	missing = [field for field, value in data.items() if not value]
	if missing:
		frappe.throw(_("Please fill in every field."), frappe.ValidationError)

	if not frappe.utils.validate_email_address(data["email"]):
		frappe.throw(_("Please give a valid email address."), frappe.ValidationError)

	data["mobile_number"] = with_country_code(data["mobile_number"])

	amount = flt(data["loan_amount"])
	if amount <= 0:
		frappe.throw(_("Please give the amount you need."), frappe.ValidationError)

	# A Link field is a name, so it is checked against the table rather than trusted.
	product = frappe.db.get_value(
		"Loan Product", {"name": data["loan_product"], "disabled": 0}, ["name", "maximum_loan_amount"], as_dict=True
	)
	if not product:
		frappe.throw(_("Please choose a product from the list."), frappe.ValidationError)

	if product.maximum_loan_amount and amount > flt(product.maximum_loan_amount):
		frappe.throw(
			_("The most you can apply for on this product is {0}.").format(
				money(product.maximum_loan_amount)
			),
			frappe.ValidationError,
		)

	data["loan_amount"] = amount
	employment = clean(frappe.form_dict.get("employment_type"))
	data["employment_type"] = employment if employment in EMPLOYMENT_TYPES else None
	data["income"] = flt(frappe.form_dict.get("income")) or None
	data["proposed_tenure"] = cint(frappe.form_dict.get("proposed_tenure")) or None

	return data


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60, ip_based=True)
def submit_lead() -> dict:
	"""Create and submit a Loan Lead, then hand back whatever the rules decided.

	Submitting is what runs the decision engine, so the indicative offer is read back
	off the saved document rather than computed here. The portal owns no credit policy.
	"""
	data = read_submission()

	lead = frappe.new_doc("Loan Lead")
	lead.update(
		{
			"applicant_name": data["applicant_name"],
			"email": data["email"],
			"mobile_number": data["mobile_number"],
			"loan_product": data["loan_product"],
			"loan_amount": data["loan_amount"],
			"applicant_type": APPLICANT_TYPE,
			"lead_source": LEAD_SOURCE,
			"income": data["income"],
			"proposed_tenure": data["proposed_tenure"],
			"employment_type": data["employment_type"],
		}
	)
	lead.insert(ignore_permissions=True)

	try:
		lead.submit()
	except Exception:
		# The decision engine declining to run must not lose the enquiry. The lead is
		# saved; staff can pick it up even if no indicative offer was produced.
		frappe.log_error(f"Portal lead {lead.name} could not be submitted")
		frappe.clear_last_message()

	lead.reload()
	frappe.db.commit()

	return present_offer(lead)


def present_offer(lead) -> dict:
	"""The offer, the decline or the holding message -- whichever the rules produced."""
	status = lead.prequalification_status or ""
	offer = []

	if lead.indicative_amount:
		offer.append({"label": _("Indicative amount"), "value": money(lead.indicative_amount)})
	if lead.indicative_roi:
		offer.append({"label": _("Indicative rate"), "value": _("{0}% p.a.").format(flt(lead.indicative_roi, 2))})
	if lead.indicative_tenure:
		offer.append({"label": _("Indicative tenure"), "value": _("{0} months").format(cint(lead.indicative_tenure))})

	if status == "Pre-Qualified" and offer:
		headline = _("Good news, you are pre-qualified")
		message = _("Create an account to continue your application.")
	elif status == "Not Pre-Qualified":
		headline = _("We cannot offer you a loan just now")
		# No reason codes: they are internal decision output, not a borrower message.
		message = _("Thank you for asking. You are welcome to apply again later.")
	else:
		headline = _("Thank you, we have your enquiry")
		message = _("Our team will come back to you shortly.")

	return {
		"reference": lead.name,
		"headline": headline,
		"message": message,
		"offer": offer,
		"reference_note": _("Keep {0} to track your application.").format(lead.name),
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60, ip_based=True)
def track_application() -> dict:
	"""Status by reference number and mobile number, both of which must match."""
	reference = clean(frappe.form_dict.get("reference"))
	mobile = clean(frappe.form_dict.get("mobile_number"))

	if not reference or not mobile:
		frappe.throw(_("Please give both your reference number and your mobile number."), frappe.ValidationError)

	# Stored with a country code, but nobody types their own that way.
	mobile = with_country_code(mobile)

	lead = frappe.db.get_value(
		"Loan Lead",
		{"name": reference, "mobile_number": mobile},
		["name", "applicant_name", "loan_product", "loan_amount", "status", "prequalification_status", "creation"],
		as_dict=True,
	)

	# One refusal for a wrong reference, a wrong mobile, and a reference that was never
	# ours. Distinguishing them would turn this into a reference-number oracle.
	if not lead:
		frappe.throw(_("We could not find an application with those details."), frappe.ValidationError)

	return {
		"reference": lead.name,
		"headline": _("Application {0}").format(lead.name),
		"message": _("Raised on {0}").format(long_date(lead.creation)),
		"offer": [
			{"label": _("Product"), "value": lead.loan_product},
			{"label": _("Amount sought"), "value": money(lead.loan_amount)},
			{"label": _("Stage"), "value": tracker_stage(lead)},
		],
		"reference_note": _("Log in to see more once your account is open."),
	}


def tracker_stage(lead: dict) -> str:
	"""Three stages, because Loan Lead status carries no more than that today."""
	if lead.prequalification_status == "Not Pre-Qualified":
		return _("Not taken forward")

	if lead.prequalification_status == "Pre-Qualified":
		return _("Pre-qualified, awaiting your application")

	return _("With our team")
