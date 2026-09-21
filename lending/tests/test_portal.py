# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Who may see what on the borrower portal, and who may write what.

PORTAL_PLAN.md section 8 says to treat every security rule as a test rather than as a
comment. These are those tests. They are about who may see what, not about arithmetic:
each one puts a real borrower in the session and asks the portal for a record that
belongs to somebody else.

Two of them are worth more than the rest.

test_a_missing_loan_and_another_borrowers_loan_are_indistinguishable is the one that
stops the portal becoming a lookup service. If "not yours" and "no such loan" read
differently, anyone can walk the loan numbering and learn which ones exist.

test_one_login_can_hold_several_customers guards the opposite mistake. Real data on
this bench has one email against three Customer records, so a helper that returns a
single customer would silently hide a borrower's own loans from them.

The later classes cover the writes: the public apply funnel, which creates rows with
no login at all, and the two borrower writes, which must reach the borrower's own
records and nothing beside them.
"""

import inspect
import json
import random
import re
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_years, getdate, nowdate

from lending.loan_management.doctype.lending_settings.lending_settings import (
	PORTAL_SCRIPT_MARKER,
	sync_portal_pages,
)
from lending.portal.accounts import customer_for_email
from lending.portal.applications import (
	get_application_detail,
	get_applications_page,
	get_document_choices,
	upload_document,
)
from lending.portal.apply import (
	confirm_mobile_code,
	create_account,
	get_apply_page,
	get_track_page,
	read_product,
	send_mobile_code,
	submit_lead,
	track_application,
)
from lending.portal.build import overview_page, theme
from lending.portal.build.overview_page import content, summary_block
from lending.portal.build.script import CLIENT_SCRIPT
from lending.portal.build.shell import SEARCH_ROUTE, tree
from lending.portal.build.theme import (
	ACTION_TONE_CSS,
	ACTIVITY_CSS,
	NEUTRALS,
	PORTAL_TOKENS,
	SCALE_TOKENS,
	SHIPPED,
	STATES,
	activity_list,
	apca,
	brand_overrides,
	channels,
	from_hsl,
	hue_shift,
	ink_for,
	luminance,
	palette_overrides,
	relight,
	tint,
	to_hsl,
	upsert_tokens,
)
from lending.portal.core import (
	DEFAULT_BRAND_NAME,
	PORTAL_ROUTE_PREFIX,
	REPAYMENTS_ROUTE,
	account_status,
	application_lead,
	assert_owns,
	brand_name,
	brand_payload,
	build_summary,
	copyright_note,
	days_ago,
	empty_dashboard,
	footer_links,
	get_portal_customers,
	leads_for_login,
	money,
	name_once,
	nav_items,
	next_action,
	shell_payload,
	standing_line,
	waiting_on_borrower,
)
from lending.portal.loans import get_loan_detail, get_loans_page
from lending.portal.notifications import (
	ATTENTION_LIMIT,
	READ_KEY,
	activity_rows,
	attention_rows,
	get_notifications,
	mark_all_as_read,
	read_keys,
	row_key,
)
from lending.portal.profile import get_profile_page, save_profile
from lending.portal.search import DIALOG_LIMIT, RESULT_LIMIT, find, get_search_page, results_note
from lending.tests.test_utils import (
	create_loan,
	create_loan_accounts,
	create_loan_product,
	set_loan_accrual_frequency,
	set_loan_settings_in_company,
	setup_loan_demand_offset_order,
)
from lending.tests.utils import LendingTestSuite

ALPHA_USER = "portal-alpha@example.com"
BETA_USER = "portal-beta@example.com"

# Alpha holds two customer records on purpose. One login to many customers is the
# real shape of the data, not an edge case.
ALPHA_CUSTOMER = "_Test Portal Alpha"
ALPHA_OTHER_CUSTOMER = "_Test Portal Alpha Second"
BETA_CUSTOMER = "_Test Portal Beta"

# Used only by the shared-record test, which pins a Contact onto its customer. That
# is a lasting change, and this database is not rolled back between runs, so it gets
# a customer of its own rather than disturbing the one every other test edits.
SHARED_CUSTOMER = "_Test Portal Alpha Shared"

PRODUCT = "Personal Loan"

# National number only. The portal adds the country code a Phone field needs, and a
# visitor typing their own is exactly what the code under test has to cope with.
MOBILE = "9812345678"

# Fresh emails for the sign-up tests, which create real Users and delete them again.
PERSON_EMAIL = "_test-portal-person@example.com"
COMPANY_EMAIL = "_test-portal-company@example.com"


def set_portal_switches(portal: int, public_apply: int):
	"""Drive the two Lending Settings switches, the way saving the form would.

	sync_portal_pages is what Lending Settings.on_update runs, and it is half of what
	the switch does: the data layer refuses, and the pages stop being routed. Setting
	the values without it would test only the half that raises.
	"""
	frappe.db.set_single_value(
		"Lending Settings",
		{"enable_borrower_portal": portal, "enable_public_apply": public_apply},
	)
	sync_portal_pages()


def published_portal_routes() -> set[str]:
	return set(
		frappe.get_all(
			"Builder Page",
			filters={"page_data_script": ("like", f"%{PORTAL_SCRIPT_MARKER}%"), "published": 1},
			pluck="route",
		)
	)


def show_product_on_portal(product: str, shown: int):
	frappe.db.set_value("Loan Product", product, "show_on_portal", shown)


# Everything a lender may set about how the portal looks. Cleared between tests, so
# one test's red portal is not the next test's starting point.
BRAND_FIELDS = (
	"portal_brand_name",
	"portal_logo",
	"portal_support_email",
	"portal_brand_color",
	"portal_accent_color",
)


def set_branding(**values):
	"""Fill in the Borrower Portal section, the way saving the desk form would.

	The save is what matters for the colours: Lending Settings.on_update is where the
	Builder Tokens are written, and setting the values underneath it would test the
	half of the mechanism that does not reach the page.
	"""
	settings = frappe.get_doc("Lending Settings")
	settings.update({field: values.get(field) for field in BRAND_FIELDS})
	settings.save()


def set_footer(notice=None, links=(), support=None):
	"""Fill in the Portal Footer section, links and all.

	Separate from set_branding because the links are a child table: update() would
	take a list of dicts, but appending row by row is what the desk grid does, and the
	idx these come out in is half of what the footer tests are about.
	"""
	settings = frappe.get_doc("Lending Settings")
	settings.portal_copyright = notice
	settings.portal_support_email = support
	settings.portal_footer_links = []
	for label, url in links:
		settings.append("portal_footer_links", {"link_label": label, "url": url})
	settings.save()


def token_value(token_name: str) -> str:
	return frappe.db.get_value("Builder Token", token_name, "value")


def theme_source() -> str:
	"""theme.py as text, for the two tests that read the styles rather than run them."""
	return Path(inspect.getsourcefile(theme)).read_text()


def contrast(one: str, other: str) -> float:
	"""The WCAG contrast ratio between two colours, lighter over darker."""
	first, second = luminance(channels(one)) + 0.05, luminance(channels(other)) + 0.05

	return max(first, second) / min(first, second)


def setUpModule():
	"""Switch the portal on for the whole file.

	Both switches default to off, which is right for a real site: a portal is a public
	surface and should not appear because somebody ran an upgrade. Left off here it
	would turn every test in this file into a 404.
	"""
	set_portal_switches(1, 1)


def make_website_user(email: str) -> str:
	"""A borrower is a Website User with the Customer role, per PORTAL_PLAN.md 10."""
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		)
		user.flags.ignore_permissions = True
		user.insert()

	# add_roles skips a role the user already holds, so this is safe to repeat.
	frappe.get_doc("User", email).add_roles("Customer")

	return email


def make_portal_customer(name: str, user: str) -> str:
	"""A Customer joined to a login through the Portal Users table.

	This join is what get_portal_customers reads. Creating the Customer without it
	is the bug PORTAL_STATUS.md section 5.1 describes, so the fixture makes the row
	explicitly rather than relying on anything to add it.
	"""
	if not frappe.db.exists("Customer", name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_type": "Individual",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		).insert(ignore_permissions=True)

	customer = frappe.get_doc("Customer", name)
	if not any(row.user == user for row in customer.portal_users):
		customer.append("portal_users", {"user": user})
		customer.save(ignore_permissions=True)

	return name


def make_submitted_loan(applicant: str):
	"""A submitted loan, because the portal's list filters on docstatus 1."""
	loan = create_loan(applicant, PRODUCT, 100000, "Repay Over Number of Periods", repayment_periods=12)
	loan.submit()

	return loan


def make_application(applicant: str) -> str:
	application = frappe.get_doc(
		{
			"doctype": "Loan Application",
			"applicant_type": "Customer",
			"applicant": applicant,
			"company": "_Test Company",
			"loan_product": PRODUCT,
			"loan_amount": 100000,
			"repayment_method": "Repay Over Number of Periods",
			"repayment_periods": 12,
			"applicant_email_address": "lending@example.com",
			"applicant_phone_number": "+91-9108273645",
		}
	)
	application.insert(ignore_permissions=True)

	return application.name


class TestPortalOwnership(LendingTestSuite):
	def setUp(self):
		set_loan_settings_in_company()
		create_loan_accounts()
		setup_loan_demand_offset_order()
		set_loan_accrual_frequency("Monthly")
		create_loan_product(
			PRODUCT,
			PRODUCT,
			500000,
			8.4,
			repayment_schedule_type="Monthly as per repayment start date",
		)
		show_product_on_portal(PRODUCT, 1)

		make_website_user(ALPHA_USER)
		make_website_user(BETA_USER)
		make_portal_customer(ALPHA_CUSTOMER, ALPHA_USER)
		make_portal_customer(ALPHA_OTHER_CUSTOMER, ALPHA_USER)
		make_portal_customer(BETA_CUSTOMER, BETA_USER)

		self.alpha_loan = make_submitted_loan(ALPHA_CUSTOMER).name
		self.beta_loan = make_submitted_loan(BETA_CUSTOMER).name
		self.beta_application = make_application(BETA_CUSTOMER)

		frappe.db.commit()  # nosemgrep

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.form_dict.pop("name", None)

	def as_alpha(self):
		frappe.set_user(ALPHA_USER)

	# --- who am I -------------------------------------------------------------------

	def test_portal_customers_are_scoped_to_the_login(self):
		self.as_alpha()
		customers = get_portal_customers()

		self.assertIn(ALPHA_CUSTOMER, customers)
		self.assertNotIn(BETA_CUSTOMER, customers)

	def test_one_login_can_hold_several_customers(self):
		self.as_alpha()
		customers = get_portal_customers()

		self.assertIn(ALPHA_CUSTOMER, customers)
		self.assertIn(ALPHA_OTHER_CUSTOMER, customers)

	def test_a_guest_cannot_reach_the_portal(self):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			get_portal_customers()

	# --- lists ----------------------------------------------------------------------

	def test_a_borrower_sees_only_their_own_loans(self):
		self.as_alpha()
		names = [row["name"] for row in get_loans_page()["accounts"]]

		self.assertIn(self.alpha_loan, names)
		self.assertNotIn(self.beta_loan, names)

	def test_a_borrower_sees_only_their_own_applications(self):
		self.as_alpha()
		payload = get_applications_page()
		names = [row.get("name") for row in payload.get("applications", [])]

		self.assertNotIn(self.beta_application, names)

	# --- the guard itself -----------------------------------------------------------

	def test_assert_owns_returns_the_applicant_for_your_own_record(self):
		self.as_alpha()

		self.assertEqual(assert_owns("Loan", self.alpha_loan), ALPHA_CUSTOMER)

	def test_assert_owns_refuses_another_borrowers_record(self):
		self.as_alpha()

		with self.assertRaises(frappe.PermissionError):
			assert_owns("Loan", self.beta_loan)

	# --- detail pages ---------------------------------------------------------------

	def test_another_borrowers_loan_is_refused(self):
		self.as_alpha()
		frappe.form_dict["name"] = self.beta_loan

		with self.assertRaises(frappe.PermissionError):
			get_loan_detail()

	def test_your_own_loan_is_allowed(self):
		self.as_alpha()
		frappe.form_dict["name"] = self.alpha_loan

		self.assertEqual(get_loan_detail()["crumb"], PRODUCT)

	def test_another_borrowers_application_is_refused(self):
		self.as_alpha()
		frappe.form_dict["name"] = self.beta_application

		with self.assertRaises(frappe.PermissionError):
			get_application_detail()

	def test_a_loan_detail_with_no_name_is_refused(self):
		self.as_alpha()
		frappe.form_dict.pop("name", None)

		with self.assertRaises(frappe.PermissionError):
			get_loan_detail()

	def test_a_missing_loan_and_another_borrowers_loan_are_indistinguishable(self):
		"""The refusal must not tell a stranger which loan numbers exist."""
		self.as_alpha()

		frappe.form_dict["name"] = self.beta_loan
		with self.assertRaises(frappe.PermissionError) as theirs:
			get_loan_detail()

		frappe.form_dict["name"] = "LOAN-DOES-NOT-EXIST"
		with self.assertRaises(frappe.PermissionError) as missing:
			get_loan_detail()

		self.assertEqual(str(theirs.exception), str(missing.exception))


class TestPortalGuestEndpoints(LendingTestSuite):
	"""The public front: what a stranger may do, and where they are stopped.

	These endpoints write rows without a login, so the tests are mostly about refusal.
	The rate limits that guard them in production are inert here -- frappe's decorator
	returns early when there is no HTTP request -- so nothing below is throttled.
	"""

	def setUp(self):
		set_loan_settings_in_company()
		create_loan_accounts()
		setup_loan_demand_offset_order()
		create_loan_product(
			PRODUCT,
			PRODUCT,
			500000,
			8.4,
			repayment_schedule_type="Monthly as per repayment start date",
		)
		show_product_on_portal(PRODUCT, 1)
		frappe.set_user("Guest")
		frappe.local.form_dict = frappe._dict()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict()

	def submission(self, **overrides):
		frappe.local.form_dict = frappe._dict(
			{
				"applicant_name": "Test Applicant",
				"email": "applicant@example.com",
				"loan_product": PRODUCT,
				"loan_amount": 100000,
				**overrides,
			}
		)

	def mint_token(self, mobile=MOBILE):
		"""Walk step 2 with the SMS provider stubbed, and keep the token it returns."""
		frappe.local.form_dict = frappe._dict({"mobile_number": mobile, "otp": "123456"})
		with patch("lending.portal.apply.telephony_otp") as telephony:
			telephony.return_value.verify_otp.return_value = {"verified": True}
			result = confirm_mobile_code()

		return result["token"]

	# --- browsing -------------------------------------------------------------------

	def test_a_guest_can_read_the_apply_page(self):
		payload = get_apply_page()

		self.assertTrue(payload["products"])
		self.assertIn(PRODUCT, [row["value"] for row in payload["products"]])

	# --- verifying the number -------------------------------------------------------

	def test_a_code_is_sent_to_the_number_given(self):
		frappe.local.form_dict = frappe._dict({"mobile_number": MOBILE})
		with patch("lending.portal.apply.telephony_otp") as telephony:
			result = send_mobile_code()
			telephony.return_value.send_otp.assert_called_once()

		# Only the last two digits come back, so the page can confirm which number
		# it used without printing it.
		self.assertNotIn(MOBILE, result["message"])
		self.assertIn(MOBILE[-2:], result["message"])

	def test_a_number_that_is_not_a_number_is_refused(self):
		frappe.local.form_dict = frappe._dict({"mobile_number": "12"})

		with self.assertRaises(frappe.ValidationError):
			send_mobile_code()

	def test_a_wrong_code_hands_back_no_token(self):
		frappe.local.form_dict = frappe._dict({"mobile_number": MOBILE, "otp": "000000"})
		with patch("lending.portal.apply.telephony_otp") as telephony:
			telephony.return_value.verify_otp.return_value = {"verified": False}
			result = confirm_mobile_code()

		self.assertFalse(result["verified"])
		self.assertNotIn("token", result)

	# --- creating the lead ----------------------------------------------------------

	def test_a_lead_cannot_be_created_without_verifying_a_number(self):
		self.submission()

		with self.assertRaises(frappe.ValidationError):
			submit_lead()

	def test_a_token_we_never_issued_is_refused(self):
		self.submission(token="not-a-token-we-issued")

		with self.assertRaises(frappe.ValidationError):
			submit_lead()

	def test_a_verified_number_creates_a_submitted_and_verified_lead(self):
		token = self.mint_token()
		self.submission(token=token, income=60000, pan="ABCDE1234F")
		result = submit_lead()

		lead = frappe.db.get_value(
			"Loan Lead",
			result["reference"],
			["mobile_number", "mobile_verification_status", "lead_source", "docstatus", "pan"],
			as_dict=True,
		)

		self.assertEqual(lead.mobile_number, f"+91{MOBILE}")
		# The status survives validate, which resets it on every save. If this fails,
		# mark_mobile_verified is writing too early again.
		self.assertEqual(lead.mobile_verification_status, "Verified")
		self.assertEqual(lead.lead_source, "Portal")
		self.assertEqual(lead.pan, "ABCDE1234F")
		self.assertEqual(lead.docstatus, 1)

	def test_a_token_works_once(self):
		token = self.mint_token()
		self.submission(token=token)
		submit_lead()

		self.submission(token=token)
		with self.assertRaises(frappe.ValidationError):
			submit_lead()

	def test_more_than_the_product_allows_is_refused(self):
		token = self.mint_token()
		self.submission(token=token, loan_amount=99999999)

		with self.assertRaises(frappe.ValidationError):
			submit_lead()

	def test_a_product_that_is_not_offered_is_refused(self):
		token = self.mint_token()
		self.submission(token=token, loan_product="No Such Product")

		with self.assertRaises(frappe.ValidationError):
			submit_lead()

	def test_an_applicant_who_is_too_young_is_refused(self):
		token = self.mint_token()
		self.submission(token=token, date_of_birth=add_years(nowdate(), -10))

		with self.assertRaises(frappe.ValidationError):
			submit_lead()

	# --- tracking -------------------------------------------------------------------

	def test_tracking_needs_both_the_reference_and_the_mobile(self):
		frappe.local.form_dict = frappe._dict({"reference": "LN-LEAD-00001"})

		with self.assertRaises(frappe.ValidationError):
			track_application()

	def test_tracking_a_lead_returns_its_steps(self):
		token = self.mint_token()
		self.submission(token=token)
		reference = submit_lead()["reference"]

		frappe.local.form_dict = frappe._dict({"reference": reference, "mobile_number": MOBILE})
		payload = track_application()

		self.assertEqual(payload["reference"], reference)
		self.assertTrue(payload["steps"])

	def test_a_wrong_reference_and_a_wrong_mobile_give_the_same_refusal(self):
		"""Otherwise the tracker becomes a way to guess other people's references."""
		token = self.mint_token()
		self.submission(token=token)
		reference = submit_lead()["reference"]

		frappe.local.form_dict = frappe._dict({"reference": "LN-LEAD-99999", "mobile_number": MOBILE})
		with self.assertRaises(frappe.ValidationError) as unknown:
			track_application()

		frappe.local.form_dict = frappe._dict({"reference": reference, "mobile_number": "9000000001"})
		with self.assertRaises(frappe.ValidationError) as wrong_mobile:
			track_application()

		self.assertEqual(str(unknown.exception), str(wrong_mobile.exception))


class PortalPeople(LendingTestSuite):
	"""Two borrowers with customer records, and no loans. The writes need neither."""

	def setUp(self):
		set_loan_settings_in_company()
		create_loan_accounts()
		setup_loan_demand_offset_order()
		create_loan_product(
			PRODUCT,
			PRODUCT,
			500000,
			8.4,
			repayment_schedule_type="Monthly as per repayment start date",
		)
		show_product_on_portal(PRODUCT, 1)

		make_website_user(ALPHA_USER)
		make_website_user(BETA_USER)
		make_portal_customer(ALPHA_CUSTOMER, ALPHA_USER)
		make_portal_customer(ALPHA_OTHER_CUSTOMER, ALPHA_USER)
		make_portal_customer(SHARED_CUSTOMER, ALPHA_USER)
		make_portal_customer(BETA_CUSTOMER, BETA_USER)
		frappe.db.commit()  # nosemgrep

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict()

	def as_alpha(self):
		frappe.set_user(ALPHA_USER)


class TestPortalProfileWrite(PortalPeople):
	def post(self, **fields):
		frappe.local.form_dict = frappe._dict({"customer": ALPHA_CUSTOMER, **fields})

	def test_correcting_another_borrowers_record_is_refused(self):
		self.as_alpha()
		self.post(customer=BETA_CUSTOMER, email="thief@example.com")

		with self.assertRaises(frappe.PermissionError):
			save_profile()

	def test_a_customer_that_does_not_exist_is_refused(self):
		self.as_alpha()
		self.post(customer="No Such Customer", email="someone@example.com")

		with self.assertRaises(frappe.PermissionError):
			save_profile()

	def test_contact_details_and_address_are_saved(self):
		self.as_alpha()
		self.post(
			email="alpha.saved@example.com",
			mobile="9812340001",
			address_line1="12 Hill Road",
			city="Mumbai",
			state="Maharashtra",
			pincode="400050",
		)
		save_profile()

		frappe.local.form_dict = frappe._dict({"customer": ALPHA_CUSTOMER})
		form = get_profile_page()

		self.assertEqual(form["form_email"], "alpha.saved@example.com")
		self.assertEqual(form["form_mobile"], "9812340001")
		self.assertEqual(form["form_city"], "Mumbai")

	def test_a_landline_does_not_overwrite_the_mobile(self):
		"""Both live in phone_nos under different flags, so the write must not
		fall back to whichever row happens to be first."""
		self.as_alpha()
		self.post(email="alpha.saved@example.com", mobile="9812340002", phone="02212345678")
		save_profile()

		frappe.local.form_dict = frappe._dict({"customer": ALPHA_CUSTOMER})
		form = get_profile_page()

		self.assertEqual(form["form_mobile"], "9812340002")
		self.assertEqual(form["form_phone"], "02212345678")

	def test_an_invalid_email_is_refused(self):
		self.as_alpha()
		self.post(email="not-an-email")

		with self.assertRaises(frappe.ValidationError):
			save_profile()

	def test_a_record_shared_with_another_borrower_is_left_alone(self):
		"""A Contact linked to somebody else's customer must not be edited in place.

		Frappe makes one Contact per login and erpnext links it to each customer that
		login serves, so a shared record is ordinary. Editing one that also serves a
		stranger would change what that stranger sees.
		"""
		shared = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "_Test Shared Contact",
				"links": [
					{"link_doctype": "Customer", "link_name": SHARED_CUSTOMER},
					{"link_doctype": "Customer", "link_name": BETA_CUSTOMER},
				],
			}
		)
		shared.add_email("shared@example.com", is_primary=1)
		shared.insert(ignore_permissions=True)
		frappe.db.set_value("Customer", SHARED_CUSTOMER, "customer_primary_contact", shared.name)
		frappe.db.commit()  # nosemgrep

		self.as_alpha()
		self.post(customer=SHARED_CUSTOMER, email="alpha.private@example.com", mobile="9812340003")
		save_profile()

		self.assertEqual(
			frappe.db.get_value("Contact", shared.name, "email_id"), "shared@example.com"
		)

	def test_an_address_with_no_country_still_saves(self):
		"""Address.country is mandatory and india_compliance has its own rule about it,
		so a blank box must resolve to something rather than quoting either at the
		borrower."""
		self.as_alpha()
		self.post(
			email="alpha.saved@example.com",
			address_line1="9 Marine Drive",
			city="Mumbai",
			state="Maharashtra",
		)
		save_profile()

		frappe.local.form_dict = frappe._dict({"customer": ALPHA_CUSTOMER})

		self.assertTrue(get_profile_page()["form_country"])

	def test_a_country_we_do_not_recognise_is_refused(self):
		self.as_alpha()
		self.post(
			email="alpha.saved@example.com",
			address_line1="1 Nowhere",
			city="Nowhere",
			state="Nowhere",
			country="Freedonia",
		)

		with self.assertRaises(frappe.ValidationError):
			save_profile()

	def test_half_an_address_is_refused_in_our_own_words(self):
		self.as_alpha()
		self.post(email="alpha.saved@example.com", pincode="400050")

		with self.assertRaises(frappe.ValidationError) as refusal:
			save_profile()

		self.assertIn("city", str(refusal.exception).lower())

class TestPortalDocumentUpload(PortalPeople):
	def setUp(self):
		super().setUp()
		self.alpha_draft = make_application(ALPHA_CUSTOMER)
		self.beta_draft = make_application(BETA_CUSTOMER)
		if not frappe.db.exists("Loan Document Type", "_Test Payslip"):
			frappe.get_doc(
				{"doctype": "Loan Document Type", "loan_document_type": "_Test Payslip"}
			).insert(ignore_permissions=True)
		frappe.db.commit()  # nosemgrep

	def post(self, **fields):
		frappe.local.form_dict = frappe._dict(
			{"application": self.alpha_draft, "document_type": "_Test Payslip", **fields}
		)

	def test_uploading_to_another_borrowers_application_is_refused(self):
		self.as_alpha()
		self.post(application=self.beta_draft)

		with self.assertRaises(frappe.PermissionError):
			upload_document()

	def test_uploading_without_naming_an_application_is_refused(self):
		self.as_alpha()
		self.post(application="")

		with self.assertRaises(frappe.PermissionError):
			upload_document()

	def test_an_unknown_document_type_is_refused(self):
		self.as_alpha()
		self.post(document_type="Not A Document Type")

		with self.assertRaises(frappe.ValidationError):
			upload_document()

	def test_uploading_to_a_submitted_application_is_refused(self):
		"""A submitted application is with our team; section 6.2 keeps the borrower out."""
		application = frappe.get_doc("Loan Application", self.alpha_draft)
		application.status = "Approved"
		application.submit()
		frappe.db.commit()  # nosemgrep

		self.as_alpha()
		self.post()

		with self.assertRaises(frappe.ValidationError):
			upload_document()

	def test_a_draft_of_your_own_gets_as_far_as_the_file(self):
		"""Everything ahead of the file passes, and the missing file is what stops it.

		There is no multipart request in a test, so this proves the guards let an owned
		draft through rather than proving a file lands.
		"""
		self.as_alpha()
		self.post()

		with self.assertRaises(frappe.ValidationError) as refusal:
			upload_document()

		self.assertIn("file", str(refusal.exception).lower())

	def test_only_draft_applications_are_offered(self):
		self.as_alpha()
		frappe.local.form_dict = frappe._dict()
		choices = get_document_choices()
		offered = [row["value"] for row in choices["application_options"]]

		self.assertIn(self.alpha_draft, offered)
		self.assertNotIn(self.beta_draft, offered)


class TestPortalSignUp(LendingTestSuite):
	"""Opening an account at the end of an application, and what it is joined to.

	This is the chain that used to be broken: a borrower could apply, but nothing
	created a login, nothing created a Customer they could be joined to, and nothing
	wrote the Customer.portal_users row every page reads. Each test below holds one
	link of it in place.
	"""

	def setUp(self):
		set_loan_settings_in_company()
		create_loan_accounts()
		setup_loan_demand_offset_order()
		create_loan_product(
			PRODUCT,
			PRODUCT,
			500000,
			8.4,
			repayment_schedule_type="Monthly as per repayment start date",
		)
		show_product_on_portal(PRODUCT, 1)
		for email in (PERSON_EMAIL, COMPANY_EMAIL):
			if frappe.db.exists("User", email):
				frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		frappe.db.commit()  # nosemgrep

		frappe.set_user("Guest")
		frappe.local.form_dict = frappe._dict()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict()

	def apply_as(self, email, mobile, **overrides):
		"""Walk steps 2 and 3 with the SMS provider stubbed, and return the offer."""
		frappe.local.form_dict = frappe._dict({"mobile_number": mobile, "otp": "123456"})
		with patch("lending.portal.apply.telephony_otp") as telephony:
			telephony.return_value.verify_otp.return_value = {"verified": True}
			token = confirm_mobile_code()["token"]

		frappe.local.form_dict = frappe._dict(
			{
				"token": token,
				"applicant_name": "Test Applicant",
				"email": email,
				"loan_product": PRODUCT,
				"loan_amount": 100000,
				**overrides,
			}
		)

		return submit_lead()

	def open_account(self, offer, password="Kh8!zQr2wLp5"):
		frappe.local.form_dict = frappe._dict(
			{"token": offer["account_token"], "password": password}
		)

		return create_account()

	# --- person or company ----------------------------------------------------------

	def test_a_company_is_recorded_as_one(self):
		offer = self.apply_as(
			COMPANY_EMAIL,
			"9812340101",
			applicant_type="Business",
			company_name="Test Traders Pvt Ltd",
			# Sent, and dropped, because neither belongs to a company.
			date_of_birth="1990-01-01",
			employment_type="Salaried",
		)
		lead = frappe.db.get_value(
			"Loan Lead",
			offer["reference"],
			["applicant_type", "company_name", "date_of_birth", "employment_type"],
			as_dict=True,
		)

		self.assertEqual(lead.applicant_type, "Business")
		self.assertEqual(lead.company_name, "Test Traders Pvt Ltd")
		self.assertIsNone(lead.date_of_birth)
		# Empty rather than None: frappe fills a None Select with its first option,
		# which would record every company as Salaried.
		self.assertEqual(lead.employment_type, "")

	def test_a_company_must_give_its_name(self):
		with self.assertRaises(frappe.ValidationError):
			self.apply_as(COMPANY_EMAIL, "9812340102", applicant_type="Business")

	def test_a_company_account_is_a_company_customer(self):
		offer = self.apply_as(
			COMPANY_EMAIL, "9812340103", applicant_type="Business", company_name="Test Traders Pvt Ltd"
		)
		self.open_account(offer)

		customer = frappe.db.get_value(
			"Customer",
			customer_for_email(COMPANY_EMAIL),
			["customer_name", "customer_type"],
			as_dict=True,
		)

		self.assertEqual(customer.customer_name, "Test Traders Pvt Ltd")
		self.assertEqual(customer.customer_type, "Company")

	# --- the account ----------------------------------------------------------------

	def test_an_account_is_opened_and_joined_to_a_customer(self):
		offer = self.apply_as(PERSON_EMAIL, "9812340104")
		self.open_account(offer)

		self.assertTrue(frappe.db.exists("User", PERSON_EMAIL))
		self.assertIn("Customer", frappe.get_roles(PERSON_EMAIL))

		customer = customer_for_email(PERSON_EMAIL)
		self.assertTrue(customer)

		# The row every borrower page reads. Without it the portal is silently empty.
		joined = [row.user for row in frappe.get_doc("Customer", customer).portal_users]
		self.assertIn(PERSON_EMAIL, joined)

	def test_the_new_borrower_sees_their_own_enquiry(self):
		offer = self.apply_as(PERSON_EMAIL, "9812340105")
		self.open_account(offer)

		frappe.set_user(PERSON_EMAIL)
		frappe.local.form_dict = frappe._dict()

		self.assertIn(offer["reference"], [row.name for row in leads_for_login()])
		self.assertTrue(get_applications_page()["enquiries"])

	def test_an_account_needs_a_token(self):
		self.apply_as(PERSON_EMAIL, "9812340106")
		frappe.local.form_dict = frappe._dict({"password": "Kh8!zQr2wLp5"})

		with self.assertRaises(frappe.ValidationError):
			create_account()

	def test_an_account_token_works_once(self):
		offer = self.apply_as(PERSON_EMAIL, "9812340107")
		self.open_account(offer)

		with self.assertRaises(frappe.ValidationError):
			self.open_account(offer)

	def test_a_second_account_for_the_same_email_is_refused(self):
		self.open_account(self.apply_as(PERSON_EMAIL, "9812340108"))
		second = self.apply_as(PERSON_EMAIL, "9812340109")

		with self.assertRaises(frappe.ValidationError):
			self.open_account(second)

	def test_a_one_character_password_is_refused(self):
		"""The site's own password policy let this through, so the endpoint has a
		floor of its own rather than trusting a setting."""
		offer = self.apply_as(PERSON_EMAIL, "9812340110")

		with self.assertRaises(frappe.ValidationError):
			self.open_account(offer, password="a")

		self.assertFalse(frappe.db.exists("User", PERSON_EMAIL))

	# --- the join survives conversion -----------------------------------------------

	def test_converting_a_lead_reuses_the_borrowers_customer(self):
		"""Otherwise the borrower ends up with two Customer records, their login
		joined to the first, and the loan on the second one invisible to them."""
		self.open_account(self.apply_as(PERSON_EMAIL, "9812340111"))
		customer = customer_for_email(PERSON_EMAIL)

		frappe.set_user("Administrator")
		before = frappe.db.count("Customer")
		application = frappe.get_doc(
			{
				"doctype": "Loan Application",
				"applicant_type": "Customer",
				"company": "_Test Company",
				"loan_product": PRODUCT,
				"loan_amount": 100000,
				"repayment_method": "Repay Over Number of Periods",
				"repayment_periods": 12,
				"applicant_name": "Test Applicant",
				"applicant_email_address": PERSON_EMAIL,
				"applicant_phone_number": "+919812340111",
			}
		)
		application.insert(ignore_permissions=True)

		self.assertEqual(application.applicant, customer)
		self.assertEqual(frappe.db.count("Customer"), before)


class TestPortalSwitches(LendingTestSuite):
	"""The three switches a lender uses to decide what the portal serves.

	Every refusal here has to be frappe.PageDoesNotExistError and not PermissionError.
	website/serve.py renders the first as 404 and the second as "not permitted", and a
	lender who switched the portal off wants it gone rather than hidden behind a refusal
	that confirms it is there.

	The signed-in checks run as Administrator on purpose. The switch is read before the
	guest check, so a real borrower is not needed to prove it fires, and using one would
	tie these tests to the fixtures of another class.
	"""

	def setUp(self):
		set_loan_settings_in_company()
		create_loan_accounts()
		setup_loan_demand_offset_order()
		create_loan_product(
			PRODUCT,
			PRODUCT,
			500000,
			8.4,
			repayment_schedule_type="Monthly as per repayment start date",
		)
		show_product_on_portal(PRODUCT, 1)
		frappe.local.form_dict = frappe._dict()

	def tearDown(self):
		set_portal_switches(1, 1)
		show_product_on_portal(PRODUCT, 1)
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict()

	def test_portal_off_hides_every_signed_in_page(self):
		set_portal_switches(0, 0)

		self.assertRaises(frappe.PageDoesNotExistError, get_portal_customers)

	def test_portal_off_hides_the_public_pages(self):
		set_portal_switches(0, 0)

		self.assertRaises(frappe.PageDoesNotExistError, get_apply_page)
		self.assertRaises(frappe.PageDoesNotExistError, get_track_page)

	def test_portal_off_closes_the_endpoints_that_write(self):
		"""The switch has to stop the writes, not only the pages that lead to them."""
		set_portal_switches(0, 0)
		frappe.set_user("Guest")

		self.assertRaises(frappe.PageDoesNotExistError, send_mobile_code)
		self.assertRaises(frappe.PageDoesNotExistError, submit_lead)
		self.assertRaises(frappe.PageDoesNotExistError, create_account)

	def test_public_apply_off_leaves_the_signed_in_portal_serving(self):
		"""A lender whose sales team keys leads in the desk wants exactly this."""
		set_portal_switches(1, 0)

		self.assertRaises(frappe.PageDoesNotExistError, get_apply_page)
		self.assertRaises(frappe.PageDoesNotExistError, submit_lead)

		# The tracker follows the portal switch alone: a lead raised by a sales rep
		# still deserves a tracker.
		self.assertTrue(get_track_page()["heading"])

		# And a borrower who already has a login is untouched.
		self.assertIsInstance(get_portal_customers(), list)

	def test_a_product_not_shown_on_the_portal_is_not_offered(self):
		show_product_on_portal(PRODUCT, 0)

		offered = [row["value"] for row in get_apply_page()["products"]]

		self.assertNotIn(PRODUCT, offered)

	def test_a_product_not_shown_on_the_portal_cannot_be_applied_for(self):
		"""Filtering the list alone would leave it one guessed name away."""
		show_product_on_portal(PRODUCT, 0)

		self.assertRaises(frappe.ValidationError, read_product, PRODUCT, 100000)

	def test_a_product_shown_on_the_portal_is_offered_and_accepted(self):
		offered = [row["value"] for row in get_apply_page()["products"]]

		self.assertIn(PRODUCT, offered)
		self.assertEqual(read_product(PRODUCT, 100000)["name"], PRODUCT)

	def test_portal_off_takes_every_page_out_of_the_route_table(self):
		"""The data layer refusing is not enough on its own.

		A refusal raised while a page renders comes back as the 404 page with a 200
		status. Only an unresolved route gives a real 404, and Builder resolves a route
		by looking for a published page.
		"""
		set_portal_switches(0, 0)

		self.assertEqual(published_portal_routes(), set())

	def test_public_apply_off_takes_only_the_apply_page_out(self):
		set_portal_switches(1, 0)
		routes = published_portal_routes()

		self.assertNotIn("apply", routes)
		self.assertIn("track", routes)
		self.assertIn("borrower/overview", routes)

	def test_switching_the_portal_back_on_restores_every_page(self):
		"""A switch a lender cannot reverse is worse than no switch."""
		before = published_portal_routes()
		set_portal_switches(0, 0)
		set_portal_switches(1, 1)

		self.assertEqual(published_portal_routes(), before)


class TestPortalBranding(LendingTestSuite):
	"""What a lender sets on one desk form, and where it comes out.

	The goal these serve is in PORTAL_CUSTOMIZATION_PLAN.md part B: a borrower of the
	bank that runs this portal should not be able to tell which app built it. So the
	tests are about two things. That nothing a lender leaves blank changes anything,
	because that is what makes these settings safe to add to a site already running.
	And that everything a lender does fill in reaches the page, the tokens and the
	PDFs, rather than only the one place it was first wired to.
	"""

	def tearDown(self):
		set_branding()
		frappe.local.form_dict = frappe._dict()

	def test_an_unnamed_portal_falls_back_to_ours(self):
		set_branding()

		self.assertEqual(brand_name(), DEFAULT_BRAND_NAME)

	def test_a_named_portal_is_called_what_the_lender_called_it(self):
		set_branding(portal_brand_name="Ganges Finance")

		self.assertEqual(brand_name(), "Ganges Finance")
		self.assertEqual(shell_payload("Loans", "Apply", [], [])["brand_name"], "Ganges Finance")

	def test_without_a_logo_the_frame_shows_the_name(self):
		set_branding(portal_brand_name="Ganges Finance")
		payload = brand_payload()

		self.assertEqual(payload["brand_logo"], "")
		self.assertEqual(payload["show_wordmark"], 1)

	def test_with_a_logo_the_frame_shows_the_logo_instead_of_the_name(self):
		"""Both are written into the page, so exactly one of them has to be dropped."""
		set_branding(portal_brand_name="Ganges Finance", portal_logo="/files/ganges.png")
		payload = brand_payload()

		self.assertEqual(payload["brand_logo"], "/files/ganges.png")
		self.assertEqual(payload["show_wordmark"], 0)
		# The name still travels, because it is the logo's alt text and the PDFs' fallback.
		self.assertEqual(payload["brand_name"], "Ganges Finance")

	def test_the_shell_draws_both_the_logo_and_the_name(self):
		"""The switch above only works if the frame carries the pair to switch between.

		Wired the other way -- one block, bound to whichever the lender set -- this
		would pass on the data and still show nothing on the page.
		"""
		conditions = set()

		def walk(node):
			if node.get("visibilityCondition"):
				conditions.add(node["visibilityCondition"])
			for child in node.get("children") or []:
				walk(child)

		walk(tree())

		self.assertIn("brand_logo", conditions)
		self.assertIn("show_wordmark", conditions)

	def test_the_public_pages_carry_the_brand_too(self):
		"""/apply and /track wear no borrower shell, so they answer for it themselves."""
		set_branding(portal_brand_name="Ganges Finance", portal_logo="/files/ganges.png")

		for payload in (get_apply_page(), get_track_page()):
			self.assertEqual(payload["brand_name"], "Ganges Finance")
			self.assertEqual(payload["brand_logo"], "/files/ganges.png")

	def test_a_support_address_becomes_something_to_press(self):
		set_branding(portal_support_email="grievance@ganges.example.com")
		payload = brand_payload()

		self.assertEqual(payload["support_email"], "grievance@ganges.example.com")
		self.assertEqual(payload["support_href"], "mailto:grievance@ganges.example.com")

	def test_no_support_address_leaves_the_footer_nothing_to_show(self):
		set_branding()

		self.assertEqual(brand_payload()["support_email"], "")

	def test_a_blank_section_overrides_nothing(self):
		"""The whole reason this is safe to add to a site that is already running."""
		set_branding()

		self.assertEqual(brand_overrides(), {})
		for token in PORTAL_TOKENS:
			self.assertEqual(token_value(token["token_name"]), token["value"])

	def test_a_brand_colour_reaches_the_token_the_pages_read(self):
		set_branding(portal_brand_color="#8b1d3f")

		self.assertEqual(token_value("brand-primary"), "#8b1d3f")

	def test_the_text_on_a_button_is_worked_out_rather_than_asked_for(self):
		"""A lender picks one colour. Whether its label is white is our problem."""
		set_branding(portal_brand_color="#0b1d51")
		dark_ink = token_value("brand-primary-ink")

		set_branding(portal_brand_color="#ffd400")
		light_ink = token_value("brand-primary-ink")

		self.assertGreater(contrast(dark_ink, "#0b1d51"), 4.5)
		self.assertGreater(contrast(light_ink, "#ffd400"), 4.5)
		self.assertNotEqual(dark_ink, light_ink)

	def test_the_accent_brings_its_own_tint_and_its_own_ink(self):
		"""The avatar chip and the opening card are washes of the accent.

		Left as literals they stayed Frappe green on an otherwise red portal, which is
		exactly the tell this part of the plan exists to remove.
		"""
		set_branding(portal_accent_color="#8b1d3f")

		soft = token_value("brand-mark-soft")
		deep = token_value("brand-mark-deep")

		self.assertEqual(token_value("brand-mark"), "#8b1d3f")
		self.assertGreater(luminance(channels(soft)), 0.7)
		self.assertGreater(contrast(deep, soft), 4.5)

	def test_clearing_a_colour_gives_the_shipped_one_back(self):
		"""A lender who changes their mind has to be able to change it back."""
		set_branding(portal_brand_color="#8b1d3f")
		set_branding()

		defaults = {token["token_name"]: token["value"] for token in PORTAL_TOKENS}
		self.assertEqual(token_value("brand-primary"), defaults["brand-primary"])

	def test_nonsense_in_a_colour_field_is_ignored_rather_than_written_out(self):
		"""A Color field holds whatever was typed into it, including nothing useful."""
		set_branding(portal_brand_color="rebeccapurple")

		self.assertNotIn("brand-primary", brand_overrides())

	def test_deepening_a_colour_keeps_it_the_colour_it_was(self):
		"""The derived ink has to read as the lender's accent, not as a grey."""
		red, green, blue = channels(relight(channels("#2bb24c"), 0.12))

		self.assertGreater(green, red)
		self.assertGreater(green, blue)

	def test_a_tint_is_the_colour_laid_over_white(self):
		self.assertGreater(luminance(channels(tint(channels("#8b1d3f")))), 0.75)

	def test_white_or_near_black_whichever_can_be_read(self):
		self.assertEqual(ink_for(channels("#000000")), "#ffffff")
		self.assertEqual(ink_for(channels("#ffffff")), "#171717")

	def test_migrating_puts_the_lender_colours_back(self):
		"""The exported tokens carry what the app ships, and migrate re-imports them.

		Part C hit the same trap with the published pages. The after_migrate hook runs
		this, so a lender's portal does not quietly turn Frappe-coloured overnight.
		"""
		set_branding(portal_brand_color="#8b1d3f")
		frappe.db.set_value("Builder Token", "brand-primary", "value", "#171717")

		upsert_tokens()

		self.assertEqual(token_value("brand-primary"), "#8b1d3f")


class TestPortalFooter(LendingTestSuite):
	"""The line at the foot of every page, which is the lender's and not ours.

	A borrower reading the bottom of a bank's site expects the copyright notice on one
	side and the policies on the other, and a regulator expects the grievance address
	among them. None of it can be written into the blocks: the notice names a company
	we do not know and the policies are a list whose length we do not know, so both
	are settings read per request. These hold that open -- that the frame repeats one
	link rather than holding a fixed few, because that is what lets a lender add a
	policy without a rebuild of ten pages.
	"""

	def tearDown(self):
		set_footer()
		set_branding()

	def test_an_unwritten_notice_names_the_lender_and_the_year(self):
		set_branding(portal_brand_name="Ganges Finance")
		set_footer()

		self.assertEqual(
			copyright_note(), f"Copyright © {getdate(nowdate()).year} Ganges Finance. All rights reserved."
		)

	def test_an_unnamed_portal_puts_our_name_in_its_own_notice(self):
		set_footer()

		self.assertIn(DEFAULT_BRAND_NAME, copyright_note())

	def test_a_company_that_ends_in_a_stop_does_not_get_two(self):
		"""Most of them do, being an Ltd. The sentence supplies the stop, not the name."""
		set_branding(portal_brand_name="Ganges Finance Ltd.")
		set_footer()

		self.assertIn("Ganges Finance Ltd. All rights reserved.", copyright_note())

	def test_a_lender_writes_its_own_notice(self):
		set_footer(notice="© Ganges Finance. A Ganges Group company.")

		self.assertEqual(copyright_note(), "© Ganges Finance. A Ganges Group company.")

	def test_a_written_notice_still_gets_this_year(self):
		"""A notice with the year typed into it is wrong every January, and nobody edits
		settings to fix that."""
		set_footer(notice="© {year} Ganges Finance.")

		self.assertEqual(copyright_note(), f"© {getdate(nowdate()).year} Ganges Finance.")

	def test_a_notice_carrying_a_stray_brace_is_text_and_not_an_error(self):
		"""The substitution is a replace and not a format, so this renders rather than
		raising on every page of the portal."""
		set_footer(notice="© Ganges Finance {a division of Ganges Group}")

		self.assertEqual(copyright_note(), "© Ganges Finance {a division of Ganges Group}")

	def test_the_links_are_the_lenders_own_in_the_lenders_order(self):
		set_footer(
			links=(
				("User Agreement", "/borrower/user-agreement"),
				("Privacy Policy", "/borrower/privacy-policy"),
				("Disclaimer", "https://ganges.example.com/disclaimer"),
			)
		)

		self.assertEqual(
			footer_links(),
			[
				{"footer_label": "User Agreement", "footer_href": "/borrower/user-agreement"},
				{"footer_label": "Privacy Policy", "footer_href": "/borrower/privacy-policy"},
				{"footer_label": "Disclaimer", "footer_href": "https://ganges.example.com/disclaimer"},
			],
		)

	def test_contact_us_follows_them_without_being_typed(self):
		"""A lender is required to publish a grievance address. Leaving it to a row
		someone remembers to add would mean the sites that need it most are the ones
		without it.

		The link reads Contact us and carries the address underneath, because the
		address is what it does and not what it is for.
		"""
		set_footer(links=(("Privacy Policy", "/borrower/privacy-policy"),), support="care@ganges.example.com")

		self.assertEqual(
			footer_links()[-1],
			{"footer_label": "Contact us", "footer_href": "mailto:care@ganges.example.com"},
		)

	def test_no_address_means_no_contact_us(self):
		"""Rather than a Contact us that opens an empty mail window."""
		set_footer(links=(("Privacy Policy", "/borrower/privacy-policy"),))

		self.assertEqual([link["footer_label"] for link in footer_links()], ["Privacy Policy"])

	def test_no_links_and_no_address_leaves_the_row_empty_rather_than_broken(self):
		"""What a site that upgrades into this and sets nothing gets: a bare notice."""
		set_footer()

		self.assertEqual(footer_links(), [])
		self.assertEqual(shell_payload("Loans", "Apply", [], [])["footer_links"], [])

	def test_a_row_missing_its_destination_is_not_a_link(self):
		"""Both columns are required on the grid, so this is the row saved before the
		field was, and a link to nowhere is worse than no link."""
		set_footer(links=(("Privacy Policy", "/borrower/privacy-policy"),))
		frappe.db.set_value(
			"Portal Footer Link",
			frappe.get_all("Portal Footer Link", pluck="name")[0],
			"url",
			"",
			update_modified=False,
		)

		self.assertEqual(footer_links(), [])

	def test_the_footer_reaches_the_frame_every_page_wears(self):
		set_branding(portal_brand_name="Ganges Finance")
		set_footer(links=(("Privacy Policy", "/borrower/privacy-policy"),))
		payload = shell_payload("Loans", "Apply", [], [])

		self.assertIn("Ganges Finance", payload["copyright_note"])
		self.assertEqual(payload["footer_links"][0]["footer_label"], "Privacy Policy")

	def test_the_frame_repeats_one_link_rather_than_holding_a_fixed_few(self):
		"""The whole reason the links are a setting at all.

		Written as a block each, the count would be frozen at build time: a lender
		adding a policy would need every page rebuilt, and Builder discards the canvas
		layout when a page is rebuilt. Same trap the sidebar was pulled out of.
		"""
		found = []

		def walk(node):
			if node.get("path") == "shell/main/footer/links":
				found.append(node)
			for child in node.get("children") or []:
				walk(child)

		walk(tree())

		self.assertEqual(len(found), 1)
		links = found[0]
		self.assertTrue(links.get("isRepeaterBlock"))
		self.assertEqual(links["dataKey"]["key"], "footer_links")
		self.assertEqual(len(links["children"]), 1)

	def test_no_policy_is_named_in_the_blocks(self):
		"""The old footer spelt three of them out, which made them ours and not the
		lender's, and wrong for any lender that publishes a different set."""
		labels = []

		def walk(node):
			if (node.get("path") or "").startswith("shell/main/footer"):
				labels.append(node.get("innerHTML") or "")
			for child in node.get("children") or []:
				walk(child)

		walk(tree())

		self.assertEqual([label for label in labels if label], [])


class TestPortalMenu(LendingTestSuite):
	"""The sidebar, which is a list read per request rather than seven blocks per page.

	The rows live in lending.hooks.portal_menu_items and reach the page through
	Frappe's own portal menu. That is what these hold open: that the frame stays a
	single repeated row, and that the list it repeats is this portal's own.
	"""

	def setUp(self):
		self.request = getattr(frappe.local, "request", None)

	def tearDown(self):
		frappe.local.request = self.request
		super().tearDown()

	def declared(self) -> list[dict]:
		return [
			item
			for item in frappe.get_hooks("portal_menu_items")
			if item["route"].startswith(PORTAL_ROUTE_PREFIX)
		]

	def serving(self, route: str) -> dict[str, str]:
		"""The menu as it comes out while `route` is the page being served."""
		frappe.local.request = frappe._dict(path=route)

		return {row["nav_title"]: row["nav_current"] for row in nav_items()}

	def test_the_menu_is_the_one_declared_in_hooks(self):
		"""In the order declared, with nothing dropped on the way to the page."""
		rows = nav_items()

		self.assertEqual(
			[(row["nav_title"], row["nav_route"]) for row in rows],
			[(item["title"], item["route"]) for item in self.declared()],
		)

	def test_another_portals_rows_are_left_to_it(self):
		"""get_portal_sidebar_items answers for the whole site, ERPNext's portal included."""
		routes = {row["nav_route"] for row in nav_items()}

		self.assertNotIn("/orders", routes)
		self.assertNotIn("/invoices", routes)

	def test_the_page_being_served_is_the_row_that_lights(self):
		marks = self.serving("/borrower/statement")

		self.assertEqual(marks["Statement of account"], "page")
		self.assertEqual(marks["Account overview"], "false")
		self.assertEqual([*marks.values()].count("page"), 1)

	def test_a_detail_page_lights_the_list_it_belongs_to(self):
		"""A loan has no row of its own, and a page with nothing lit reads as lost."""
		self.assertEqual(self.serving("/borrower/loan/LOAN-0001")["Loan accounts"], "page")
		self.assertEqual(self.serving("/borrower/application/LN-APP-0001")["Applications"], "page")

	def test_a_list_is_not_swallowed_by_the_section_beside_it(self):
		"""/borrower/applications starts with /borrower/application, and is not one."""
		marks = self.serving("/borrower/applications")

		self.assertEqual(marks["Applications"], "page")
		self.assertEqual([*marks.values()].count("page"), 1)

	def test_off_a_request_the_menu_still_comes_out(self):
		"""An /api call on one of these endpoints is serving no page at all."""
		frappe.local.request = None
		marks = {row["nav_title"]: row["nav_current"] for row in nav_items()}

		self.assertEqual(len(marks), len(self.declared()))
		self.assertNotIn("page", marks.values())

	def test_the_frame_holds_one_row_and_not_a_copy_per_link(self):
		"""The whole point of the change: a route is written in hooks.py and nowhere else.

		A block carrying its own /borrower href would be a second copy of the menu,
		frozen into the component and into every page that mirrors it.
		"""
		repeaters = []
		hrefs = []

		def walk(node):
			if node.get("isRepeaterBlock"):
				repeaters.append(node)
			href = (node.get("attributes") or {}).get("href") or ""
			if href.startswith("/borrower"):
				hrefs.append(href)
			for child in node.get("children") or []:
				walk(child)

		walk(tree())

		# The rail's own two links are borrower routes and are meant to be written in
		# the frame; they are not menu rows. What must not appear is a menu route.
		menu_routes = {item["route"] for item in self.declared()}
		self.assertEqual([href for href in hrefs if href in menu_routes], [])
		# The footer's policy links are a repeater too, and for the same reason -- see
		# TestPortalFooter. The menu's is the one this test is about.
		nav = [node for node in repeaters if node["dataKey"]["key"] == "nav_items"]
		self.assertEqual(len(nav), 1)
		row = nav[0]["children"][0]
		self.assertEqual(
			{value["key"] for value in row["dynamicValues"]},
			{"nav_title", "nav_route", "nav_current"},
		)


class TestPortalRail(LendingTestSuite):
	"""The two icons in the rail, and the pages behind them.

	Both were links to "#" until these existed, so the first thing held open here is
	that they go somewhere. The rest is what they answer with: a search that can only
	return what this login already owns, and a notification list that separates what
	the borrower has to do from what has merely happened.
	"""

	def setUp(self):
		set_loan_settings_in_company()
		create_loan_accounts()
		setup_loan_demand_offset_order()
		set_loan_accrual_frequency("Monthly")
		create_loan_product(
			PRODUCT,
			PRODUCT,
			500000,
			8.4,
			repayment_schedule_type="Monthly as per repayment start date",
		)

		make_website_user(ALPHA_USER)
		make_website_user(BETA_USER)
		make_portal_customer(ALPHA_CUSTOMER, ALPHA_USER)
		make_portal_customer(BETA_CUSTOMER, BETA_USER)

		self.alpha_loan = make_submitted_loan(ALPHA_CUSTOMER).name
		self.beta_loan = make_submitted_loan(BETA_CUSTOMER).name
		self.alpha_application = make_application(ALPHA_CUSTOMER)

		frappe.db.commit()  # nosemgrep

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.form_dict = frappe._dict()
		super().tearDown()

	def search(self, query: str) -> dict:
		frappe.set_user(ALPHA_USER)
		frappe.local.form_dict = frappe._dict({"q": query})

		return get_search_page()

	def search_dialog(self, query: str) -> dict:
		frappe.set_user(ALPHA_USER)
		frappe.local.form_dict = frappe._dict({"q": query})

		return find()

	# --- the rail -------------------------------------------------------------------

	def marked(self, attribute: str) -> list[dict]:
		"""Every block in the frame carrying `attribute`, wherever it sits in the tree."""
		found = []

		def walk(node):
			if attribute in (node.get("attributes") or {}):
				found.append(node)
			for child in node.get("children") or []:
				walk(child)

		walk(tree())

		return found

	def test_the_frame_carries_the_dialog_and_the_panel_on_every_page(self):
		"""Both live in the shared component, so no page can be missing one."""
		for attribute in ("data-search-overlay", "data-alerts-panel"):
			blocks = self.marked(attribute)

			self.assertEqual(len(blocks), 1, attribute)
			# Built shut. The rail's links are what a borrower gets with no script.
			self.assertEqual(blocks[0]["attributes"].get("hidden"), "hidden", attribute)

	def test_the_magnifier_leads_somewhere_and_the_bell_does_not_pretend_to(self):
		"""The complaint the first half answers: an icon whose href is "#" does nothing.

		The magnifier is one block carrying both: the script takes the click and opens
		the dialog over the page, and the href is what happens where no script runs.
		Found by the attribute the script looks for rather than by the label, because
		the dialog is announced as "Search" too.

		The bell has no page behind it any more, so it is a button. A link would be an
		invitation to a route that would 404.
		"""
		magnifier = self.marked("data-search-open")

		self.assertEqual(len(magnifier), 1)
		self.assertEqual(magnifier[0]["attributes"]["href"], f"/{SEARCH_ROUTE}")

		bell = self.marked("data-alerts-open")

		self.assertEqual(len(bell), 1)
		self.assertEqual(bell[0]["element"], "button")
		self.assertNotIn("href", bell[0]["attributes"])

	def test_each_list_carries_one_row_for_the_script_to_copy(self):
		"""A hidden row in the markup is the template; theme keeps every style on it."""
		for attribute in ("data-search-row", "data-alerts-row"):
			rows = self.marked(attribute)

			self.assertEqual(len(rows), 1, attribute)
			self.assertEqual(rows[0]["attributes"].get("hidden"), "hidden", attribute)

	def test_the_script_the_pages_ship_wires_both(self):
		"""The blocks are inert markup until the shared script finds them."""
		for hook in ("wireSearch", "wireAlerts", "data-search-overlay", "data-alerts-panel"):
			self.assertIn(hook, CLIENT_SCRIPT)

	def test_the_page_the_rail_opens_is_published(self):
		self.assertIn(SEARCH_ROUTE, published_portal_routes())

	def test_the_notifications_page_is_gone(self):
		"""The panel says everything the page said, and a bell with two answers is one
		answer too many. Asserted on the served routes rather than on the source,
		because a Builder Page left published outlives the module that built it."""
		self.assertNotIn("borrower/notifications", published_portal_routes())

	# --- search ---------------------------------------------------------------------

	def test_a_product_finds_loans_and_nothing_that_is_not_one(self):
		"""Asserted on the answer rather than on the fixture: this database is not rolled
		back between runs, so the borrower holds hundreds of loans by now and the one
		this test made need not be among the first page of them."""
		results = self.search(PRODUCT)["results"]

		self.assertTrue(results)
		for row in results:
			self.assertIn(PRODUCT.lower(), " ".join(row.values()).lower())

	def test_a_loan_is_found_by_its_number(self):
		results = self.search(self.alpha_loan)["results"]

		self.assertEqual([row["url"] for row in results], [f"/borrower/loan/{self.alpha_loan}"])

	def test_an_application_is_found_and_opens_its_own_page(self):
		results = self.search(self.alpha_application)["results"]

		self.assertEqual(
			[(row["kind"], row["url"]) for row in results],
			[("Application", f"/borrower/application/{self.alpha_application}")],
		)

	def test_a_search_cannot_reach_another_borrowers_loan(self):
		"""The one that matters. Search reads the same scoped lists every page reads."""
		results = self.search(self.beta_loan)["results"]

		self.assertEqual(results, [])

	def test_every_word_has_to_match(self):
		"""Two words narrow the answer; they do not widen it."""
		self.assertTrue(self.search(PRODUCT)["results"])
		self.assertEqual(self.search(f"{PRODUCT} nothing-matches-this")["results"], [])

	def test_an_empty_box_opens_holding_somewhere_to_go(self):
		"""The desk's command bar offers the places you can go before you type, and a
		borrower with no loans yet has nothing else worth offering."""
		payload = self.search("")

		self.assertEqual(payload["query"], "")
		self.assertEqual(
			[row["url"] for row in payload["results"]],
			[item["route"] for item in frappe.get_hooks("portal_menu_items")],
		)
		self.assertEqual({row["kind"] for row in payload["results"]}, {"Page"})
		self.assertIn("Type to search", payload["results_note"])

	def test_a_page_is_findable_by_name_like_anything_else(self):
		"""The pages are in the same list the records are, so one query searches both."""
		results = self.search("interest certificate")["results"]

		self.assertEqual(
			[(row["kind"], row["url"]) for row in results], [("Page", "/borrower/certificate")]
		)

	def test_a_search_that_matches_everything_is_cut_down(self):
		"""Held open without the hundreds of records it would take to cause it."""
		self.assertIn(str(RESULT_LIMIT), results_note("loan", RESULT_LIMIT + 10))
		self.assertIn(str(RESULT_LIMIT + 10), results_note("loan", RESULT_LIMIT + 10))

	def test_the_dialog_shows_five_where_the_page_shows_them_all(self):
		"""The dialog is a peek over the page behind it; the page is the list. The menu
		is longer than five, so an empty box is enough to tell the two apart."""
		self.assertGreater(len(frappe.get_hooks("portal_menu_items")), DIALOG_LIMIT)

		self.assertEqual(len(self.search_dialog("")["results"]), DIALOG_LIMIT)
		self.assertGreater(len(self.search("")["results"]), DIALOG_LIMIT)

	# --- notifications --------------------------------------------------------------

	def test_a_draft_application_is_work_waiting_on_the_borrower(self):
		"""A draft is the borrower's to submit, so it belongs on the list that asks."""
		rows = attention_rows(
			[
				{"name": "APP-1", "url": "/borrower/application/APP-1", "product": PRODUCT,
					"note": "Submit to start the review", "stage": "Action required",
					"needs_borrower": True},
				{"name": "APP-2", "url": "/borrower/application/APP-2", "product": PRODUCT,
					"note": "", "stage": "Under review", "needs_borrower": False},
			],
			[],
		)

		self.assertEqual([row["url"] for row in rows], ["/borrower/application/APP-1"])

	def test_an_instalment_coming_due_is_on_the_list_too(self):
		instalment = {
			"product": PRODUCT,
			"detail": "Principal 900 · interest 100",
			"date": "12 Oct 2026",
			"amount": "1,000",
		}
		rows = attention_rows([], [dict(instalment, url="/borrower/loan/LOAN-0001")])

		self.assertEqual(rows[0]["when"], "Due 12 Oct 2026 · 1,000")
		self.assertEqual(rows[0]["url"], "/borrower/loan/LOAN-0001")

	def test_an_instalment_whose_loan_is_unknown_still_leads_somewhere(self):
		"""A row that looks like a link has to act like one, even with no loan to name."""
		rows = attention_rows([], [{"product": PRODUCT, "detail": "", "date": "z", "amount": "1"}])

		self.assertEqual(rows[0]["url"], "/borrower/loans")

	def test_the_borrowers_own_list_is_capped_and_says_how_long_it_really_is(self):
		frappe.set_user(ALPHA_USER)
		payload = get_notifications()

		self.assertLessEqual(len(payload["attention"]), ATTENTION_LIMIT)
		for row in payload["attention"]:
			self.assertTrue(row["url"].startswith("/borrower/"))
		self.assertTrue(
			payload["attention_note"] == "Nothing to do" or "waiting on you" in payload["attention_note"]
		)

	def test_another_borrowers_work_is_not_on_this_ones_list(self):
		frappe.set_user(BETA_USER)
		urls = [row["url"] for row in get_notifications()["attention"]]

		self.assertNotIn(f"/borrower/application/{self.alpha_application}", urls)

	def test_what_has_happened_comes_out_in_the_same_shape_as_what_is_waiting(self):
		"""One shape is what lets the two tabs share a single row block."""
		rows = activity_rows(
			[{"title": "Repayment received", "sub": PRODUCT, "date": "12 Sep 2026", "amount": "1,000"}]
		)

		self.assertEqual(
			rows,
			[
				{
					"title": "Repayment received",
					"note": PRODUCT,
					"when": "1,000 · 12 Sep 2026",
					# A record of a repayment is still worth opening: it is a line of
					# the statement. No row in either list is a dead end.
					"url": "/borrower/statement",
				}
			],
		)
		self.assertEqual(
			set(rows[0]),
			set(attention_rows([], [{"product": "x", "detail": "y", "date": "z", "amount": "1"}])[0]),
		)

	# --- the double tick -------------------------------------------------------------

	def test_every_row_says_whether_it_has_been_read(self):
		"""The dot on the row is drawn from this and nothing else."""
		frappe.set_user(ALPHA_USER)
		payload = get_notifications()

		for row in payload["attention"] + payload["activity"]:
			self.assertIn("read", row)
			self.assertIsInstance(row["read"], bool)

	def test_the_double_tick_marks_everything_on_the_panel(self):
		frappe.set_user(ALPHA_USER)
		frappe.defaults.clear_user_default(READ_KEY)

		before = get_notifications()
		self.assertTrue(any(not row["read"] for row in before["attention"] + before["activity"]))

		mark_all_as_read()
		after = get_notifications()

		self.assertTrue(all(row["read"] for row in after["attention"] + after["activity"]))

	def test_a_row_that_changes_what_it_says_comes_back_unread(self):
		"""A notification is only the same notification while it says the same thing:
		an instalment whose amount moves is news again, and has to look like it."""
		frappe.set_user(ALPHA_USER)
		mark_all_as_read()
		seen = read_keys()

		row = {"title": PRODUCT, "note": "Principal 900", "when": "Due 12 Oct 2026 · 1,000", "url": "/borrower/loans"}
		moved = dict(row, when="Due 12 Oct 2026 · 1,200")

		self.assertNotEqual(row_key(row), row_key(moved))
		self.assertNotIn(row_key(moved), seen)

	def test_one_borrowers_double_tick_does_not_clear_anothers(self):
		frappe.set_user(BETA_USER)
		frappe.defaults.clear_user_default(READ_KEY)

		frappe.set_user(ALPHA_USER)
		mark_all_as_read()
		self.assertTrue(read_keys())

		frappe.set_user(BETA_USER)
		self.assertEqual(read_keys(), set())

	def test_the_double_tick_writes_only_what_the_server_can_see(self):
		"""Nothing arrives from the browser, so there is nothing to forge: the keys are
		recomputed from this borrower's own rows. It is also what prunes the list --
		a key for a row that has dropped off the panel is simply not rewritten."""
		frappe.set_user(ALPHA_USER)
		frappe.defaults.set_user_default(READ_KEY, json.dumps(["stale-key-from-before"]))
		mark_all_as_read()

		self.assertNotIn("stale-key-from-before", read_keys())

	def test_a_borrower_whose_marks_are_unreadable_is_not_an_error(self):
		"""A hand-edited DefaultValue should cost a borrower their dots, not their page."""
		frappe.set_user(ALPHA_USER)
		frappe.defaults.set_user_default(READ_KEY, "not json")

		self.assertEqual(read_keys(), set())
		self.assertTrue(get_notifications()["activity_note"])


class TestPortalScale(LendingTestSuite):
	"""Stage 1 of PORTAL_DESIGN_PLAN.md: the size scale.

	The point of the stage is that no size in theme.py is a number any more, so
	there is one place to change them all. The source tests at the end are what hold
	that open.
	"""

	def test_the_shipped_scale_is_what_the_pages_read(self):
		upsert_tokens()

		for token in SCALE_TOKENS:
			self.assertEqual(token_value(token["token_name"]), token["value"])

	def test_every_step_of_the_scale_is_larger_than_the_one_below_it(self):
		"""A scale that repeats a size is not a scale. Six steps have to be six sizes."""
		steps = [int(token["value"].removesuffix("px")) for token in SCALE_TOKENS[:6]]

		self.assertEqual(steps, sorted(set(steps)))

	def test_body_and_sub_headings_are_set_where_the_desk_sets_them(self):
		"""The whole reason for the scale being the desk's rather than its own.

		A borrower who has also seen the desk reads the two at one size, so the portal
		sets body in --text-sm and a sub-heading in --text-base, which is where the
		desk sets a row and a section heading. Asserted on the two steps that carry
		text a page is actually read in; the rest of the scale is free to move.
		"""
		body = SCALE_TOKENS[2]["value"]
		sub_heading = SCALE_TOKENS[3]["value"]

		self.assertEqual((body, sub_heading), ("13px", "14px"))

	def test_no_style_carries_a_text_size_as_a_number(self):
		"""The guard on the next person who adds a style.

		A literal size is invisible: the page still renders, and the one block that
		ignores the scale is the one nobody looks at. Six are allowed. Three are a
		glyph centred in a circle of a fixed width, which cannot grow with the text.
		Two are the notifications panel, which is a copy of the desk's own dropdown
		down to its type: the desk sets that at 14px over a 12px timestamp. Those are
		the scale's own values now that the scale is the desk's, but they stay written
		out because a row of the panel is body text and the name the portal gives 14px
		is the one it gives a sub-heading.

		The sixth is the badge, and it is the same argument: .es-badge is a 20px pill
		with 12px type on one line, and a badge whose text grew with the page's scale
		while its height did not would burst the shape the desk made recognisable. It
		is pinned to the desk for the same reason the panel is.

		Both spellings count: a size written into a style, and a size held in a name
		that styles then point at. A constant is the honest way to say the panel is
		measured against the desk rather than against the page, but it must not also
		be the way around this test.
		"""
		literals = re.findall(r'(?:"fontSize": "|^[A-Z][A-Z_]* = ")(\d+px)"', theme_source(), re.M)

		self.assertEqual(sorted(literals), ["10px", "10px", "11px", "12px", "12px", "14px"])

	def test_no_style_is_named_twice_in_the_file(self):
		"""The guard on a file long enough to forget what is already in it.

		A redefinition is not an error. Python keeps the last one, the page still
		renders, and the block that named the earlier style silently wears the later
		one. The notifications panel spent a while wearing the apply wizard's card
		because both families called themselves PANEL_STYLES: the panel lost its fixed
		position and its width, its header turned into a column, and every test here
		still passed.
		"""
		names = re.findall(r"^([A-Z][A-Z0-9_]*) = ", theme_source(), re.M)

		self.assertEqual(sorted({name for name in names if names.count(name) > 1}), [])

	def test_the_fallback_beside_a_token_is_the_value_that_token_holds(self):
		"""A fallback is what renders wherever the tokens have not been written yet.

		One that has drifted from the token beside it is a second scale hiding in the
		source, and it shows up only on a site that has never saved Lending Settings.
		"""
		shipped = {token["token_name"]: token["value"] for token in SCALE_TOKENS}
		drifted = {
			name: fallback
			for name, fallback in re.findall(r"var\(--(portal-[a-z0-9-]+),([^)]+)\)", theme_source())
			if name in shipped and fallback != shipped[name]
		}

		self.assertEqual(drifted, {})

	def test_every_token_a_style_names_is_a_token_that_exists(self):
		"""A misspelt custom property falls back and says nothing about it."""
		named = set(re.findall(r"var\(--([a-z0-9-]+),", theme_source()))
		defined = {token["token_name"] for token in PORTAL_TOKENS}

		self.assertEqual(named - defined, set())


class TestPortalPalette(LendingTestSuite):
	"""Stage 2 of PORTAL_DESIGN_PLAN.md: the neutrals, the states, and the ink maths.

	Two claims are worth testing rather than believing. That a lender's colour reaches
	the greys without costing the page any contrast, and that the ink on a button is
	readable for a colour nobody thought to try.
	"""

	def tearDown(self):
		set_branding()

	def test_a_blank_brand_colour_leaves_the_shipped_neutrals_alone(self):
		set_branding()

		self.assertEqual(palette_overrides(), {})
		for name in NEUTRALS:
			self.assertEqual(token_value(f"portal-{name}"), SHIPPED[name])

	def test_a_brand_colour_reaches_the_greys(self):
		"""The half of white labelling the colour fields alone do not reach.

		Grey is the largest surface on the page. A portal whose button is HDFC blue and
		whose greys are still Frappe's is a Frappe portal with a blue button.
		"""
		set_branding(portal_brand_color="#8b1d3f")

		self.assertNotEqual(token_value("portal-surface-sunken"), SHIPPED["surface-sunken"])
		self.assertNotEqual(token_value("portal-ink-muted"), SHIPPED["ink-muted"])

	def test_the_page_under_the_cards_stays_white(self):
		"""What the six bank sites do: colour in the band, white under it."""
		set_branding(portal_brand_color="#8b1d3f")

		self.assertEqual(token_value("portal-surface-page"), SHIPPED["surface-page"])

	def test_no_brand_colour_can_move_a_state_colour(self):
		"""A lender whose brand is red still tells a borrower in green that nothing is owed."""
		set_branding(portal_brand_color="#8b1d3f", portal_accent_color="#8b1d3f")

		for name in STATES:
			self.assertEqual(token_value(f"portal-{name}"), SHIPPED[name])

	def test_a_grey_brand_colour_tints_nothing(self):
		"""There is no hue to take off a grey, so taking one would give channel rounding."""
		set_branding(portal_brand_color="#4a4a4a")

		self.assertEqual(palette_overrides(), {})

	def test_tinting_the_greys_costs_no_contrast(self):
		"""The reason hue_shift puts the luminance back.

		Contrast is a ratio of luminances, so holding each neutral at the luminance it
		ships with holds every ratio on the page at the value it was designed and tested
		at. One percent is the room 8-bit rounding needs and nothing else.

		Written at a fixed lightness first, this test failed at hue 60 -- a yellow grey
		reads brighter than a blue grey of the same lightness, and the body text lost
		five percent. That failure is what the second step in hue_shift is for.
		"""
		marks = ("ink", "ink-muted", "ink-subtle", "ink-faint", "border", "border-strong")
		surfaces = (
			"surface-page",
			"surface-card",
			"surface-sunken",
			"surface-hover",
			"surface-hover-strong",
		)

		for step in range(36):
			shifted = {name: hue_shift(SHIPPED[name], step / 36) for name in NEUTRALS}
			for mark in marks:
				for surface in surfaces:
					before = contrast(SHIPPED[mark], SHIPPED[surface])
					after = contrast(shifted[mark], shifted[surface])
					self.assertGreater(after, before * 0.99, f"{mark} on {surface} at hue {step}")

	def test_the_ink_on_a_button_is_readable_for_any_brand_colour(self):
		"""The colour that breaks a portal is the one nobody demos.

		Lc 45 is APCA's floor for a large or bold label, which is what a button carries.
		A thousand colours rather than a handful, because the failures are a narrow band
		of mid tones and a hand-picked list walks straight past them.
		"""
		generator = random.Random(20260918)

		for _ in range(1000):
			brand = tuple(generator.randrange(256) for _ in range(3))
			ink = ink_for(brand)
			self.assertGreaterEqual(apca(channels(ink), brand), 45, f"{brand} took {ink}")

	def test_apca_agrees_with_the_published_reference_values(self):
		"""Borrowed maths, checked against the source it was borrowed from."""
		pairs = (("#888888", "#ffffff", 63.1), ("#000000", "#ffffff", 106.0), ("#ffffff", "#000000", 107.9))

		for text, background, expected in pairs:
			self.assertAlmostEqual(apca(channels(text), channels(background)), expected, delta=0.1)

	def test_a_colour_survives_the_trip_through_hue_saturation_lightness(self):
		for colour in ("#ffffff", "#f8f8f8", "#ededed", "#999999", "#171717", "#ce2c2c", "#0b1d51"):
			self.assertEqual(from_hsl(*to_hsl(channels(colour))), colour)

	def test_no_style_carries_a_colour_as_a_hex(self):
		"""The guard on the next person who adds a style.

		The same reason as the sizes: a literal renders, so the one block that ignores
		the lender's palette is the one nobody looks at. Two places are allowed to hold
		a raw colour, and both are the values themselves rather than a use of them.
		"""
		source = theme_source()
		source = re.sub(r"SHIPPED = \{.*?\n\}\n", "", source, flags=re.S)
		source = re.sub(r"BRAND_TOKENS = \[.*?\n\]\n", "", source, flags=re.S)
		source = re.sub(r"var\([^)]*\)", "", source)

		self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}\b", source), [])


class TestPortalSummaryStrip(LendingTestSuite):
	"""The three cards the overview opens with, and which of them leads.

	A borrower opens the portal to learn three things: where their application has got
	to, what they pay next, and what they still owe. The application leads because it
	is the only one of the three with an answer on the first day -- the two figures
	read "Nothing due" and "No live accounts" until a loan is booked, and a borrower
	who is still applying was meeting a page of blanks.
	"""

	def blocks(self, node) -> list[dict]:
		"""Every block of a page's tree, the node itself included."""
		found = [node]
		for child in node.get("children") or []:
			found.extend(self.blocks(child))

		return found

	def summary_blocks(self) -> list[dict]:
		return self.blocks(summary_block())

	def test_the_strip_leads_with_the_application_then_the_two_figures(self):
		"""The order is the point, so it is read off the cards rather than counted.

		Each card's title is the first bound thing in its head, and the three titles in
		order are the strip's whole argument: the application, the payment, the debt.
		"""
		cards = summary_block()["children"]
		titles = [card["children"][0]["children"][0]["dynamicValues"][0]["key"] for card in cards]

		self.assertEqual(titles, ["label_application", "label_next", "label_outstanding"])

	def test_the_application_card_takes_its_pill_tone_from_the_payload(self):
		"""The pill beside the title does not always mean the same thing.

		"Action required" is a warning and "Under review" is not, and a stage pill
		painted warn on the block would tell a borrower waiting on the lender that
		something is wrong. The due-in-five-days pill beside it is the opposite case
		and keeps its fixed tone.
		"""
		head = summary_block()["children"][0]["children"][0]
		pill = head["children"][1]
		bound_keys = [value["key"] for value in pill["dynamicValues"]]

		self.assertEqual(bound_keys, ["application_stage", "application_stage_tone"])
		# And it goes when there is no application, rather than leaving an empty pill.
		self.assertEqual(pill["visibilityCondition"], "application_stage")

	def test_a_borrower_with_nothing_in_progress_is_not_shown_an_empty_card(self):
		"""The card stands either way, so the empty payload has to fill it.

		A blank headline would read as a page that failed to load. The em dash and the
		line under it say there is nothing, which is a different thing from saying
		nothing.
		"""
		empty = application_lead([])

		self.assertEqual(empty["application_stage"], "")
		self.assertNotEqual(empty["application_headline"], "")
		self.assertNotEqual(empty["application_note"], "")

	def test_the_card_names_the_newest_application_and_says_how_many_more(self):
		"""One card, several applications: it must not look like the whole story.

		get_applications orders newest first, so the card takes the first row. The
		count under it is what sends a borrower to the table below, and it stays away
		when there is only the one they are already reading.
		"""
		newest = dict(self.application("Home Loan"), note="")
		older = self.application("Personal Loan")

		self.assertEqual(application_lead([newest, older])["application_headline"], "Home Loan")
		self.assertIn("2", application_lead([newest, older])["application_more"])
		self.assertEqual(application_lead([newest])["application_more"], "")

	def application(self, product: str) -> dict:
		return {
			"product": product,
			"stage": "Under review",
			"stage_tone": "info",
			"reference": "APP-1 · initiated 1 January 2026",
			"note": "",
		}

	def test_the_sanctioned_amount_is_one_line_under_the_outstanding_figure(self):
		"""It was a card of its own, at the weight of the two figures beside it.

		A borrower checks what was sanctioned once, so it reads as a sentence now. The
		sentence is joined in the data layer because Builder binds one key into one
		element, and the page data script cannot join two.
		"""
		loans = [frappe._dict(status="Active", loan_amount=500000, disbursed_amount=300000)]
		line = build_summary(loans, [])["sanctioned_line"]

		self.assertIn(money(500000), line)
		self.assertIn(money(200000), line)

	def test_a_borrower_with_no_loans_is_not_told_they_are_sanctioned_nothing(self):
		"""An empty payload carries no line, and the block goes with it.

		Both halves: a page that hid nothing would print "Total sanctioned ₹0.00" to
		somebody who has only applied, and a payload that said nothing to a block with
		no condition on it would leave the gap where the line was.

		Two ways to have nothing sanctioned, and both are real. A visitor with no
		customer record at all takes the empty payload. A borrower with a customer
		record and an application still in progress does not: they have loans of zero,
		which is the one the cards used to get wrong.
		"""
		self.assertEqual(empty_dashboard()["sanctioned_line"], "")
		self.assertEqual(build_summary([], [])["sanctioned_line"], "")

		conditioned = [
			node for node in self.summary_blocks() if node.get("visibilityCondition") == "sanctioned_line"
		]

		self.assertEqual(len(conditioned), 1)


class TestPortalRanking(LendingTestSuite):
	"""What the overview puts first, and what it stops saying twice.

	The page used to lead with a filled black button offering a payment eighteen days
	away, while the two applications actually waiting on the borrower were grey text
	in the middle of a table. What is held open here is the order it reads in now:
	the work first, the button following the work, and every fact said once.
	"""

	def draft(self, name="APP-1", product="Personal Loan"):
		return {
			"name": name,
			"url": f"/borrower/application/{name}",
			"product": product,
			"reference": f"{name} · initiated 24 August 2026",
			"note": "Submit to start the review",
			"stage": "Action required",
			"stage_tone": "warn",
			"needs_borrower": True,
			"amount": money(100000),
		}

	def instalment(self, product="Personal Loan"):
		return {
			"date": "09 Oct 2026",
			"product": product,
			"detail": "Principal 900 · interest 100",
			"amount": money(1000),
			"url": "/borrower/loan/LOAN-0001",
		}

	# --- what counts as waiting ------------------------------------------------------

	def test_an_application_under_review_is_not_waiting_on_the_borrower(self):
		"""The strip is work they can do. An application with the lender is not that."""
		reviewing = dict(self.draft(), needs_borrower=False, stage="Under review")

		self.assertEqual(waiting_on_borrower([reviewing]), [])

	def test_a_draft_opens_where_it_is_cleared(self):
		rows = waiting_on_borrower([self.draft(), dict(self.draft(), needs_borrower=False)])

		self.assertEqual([row["url"] for row in rows], ["/borrower/application/APP-1"])
		self.assertEqual(rows[0]["note"], "Submit to start the review")

	def test_the_strip_leaves_the_payment_to_the_button(self):
		"""The two halves of the page's one request must not both make it.

		A strip that also carried the instalment would put the payment on the page
		twice -- once as a row and once as the button right above it -- which is the
		habit the strip was added to break, reintroduced by the fix for it.
		"""
		source = inspect.getsource(waiting_on_borrower)

		self.assertNotIn("schedule", source)
		self.assertNotIn(REPAYMENTS_ROUTE, source)

	# --- the button ------------------------------------------------------------------

	def test_the_button_is_the_payment_page_either_way(self):
		"""The destination was never wrong. Only the insistence was."""
		quiet = next_action(due_soon=False)
		loud = next_action(due_soon=True)

		self.assertEqual(quiet["action_href"], REPAYMENTS_ROUTE)
		self.assertEqual(loud["action_href"], REPAYMENTS_ROUTE)
		self.assertEqual(quiet["action_label"], loud["action_label"])

	def test_the_button_only_insists_when_a_payment_is_near(self):
		"""The whole complaint in one assertion: eighteen days out, this was "1"."""
		self.assertEqual(next_action(due_soon=False)["action_urgent"], "0")
		self.assertEqual(next_action(due_soon=True)["action_urgent"], "1")

	def test_the_quiet_button_has_a_rule_to_be_quiet_by(self):
		"""The payload can say "0" all it likes; something has to paint it.

		The rule rides in this page's own head rather than SHELL_STATE_CSS, which
		every page carries a copy of and which no page serves until all of them have
		been rebuilt.
		"""
		self.assertIn('[data-urgent="0"]', ACTION_TONE_CSS)
		self.assertIn("extra_css=ACTION_TONE_CSS", inspect.getsource(overview_page.build))

	def test_the_strip_hides_itself_when_there_is_nothing_in_it(self):
		"""A borrower in good standing gets no empty shelf announcing they are idle."""
		strips = [
			node
			for node in self.walk(content())
			if node.get("visibilityCondition") == "tasks"
		]

		self.assertEqual(len(strips), 1)

	# --- what is no longer said twice -------------------------------------------------

	def test_one_live_account_reads_its_standing_in_its_own_row(self):
		"""The head said "All accounts regular" over a single row saying "Regular"."""
		one = [frappe._dict(name="L-1", status="Disbursed")]
		two = [frappe._dict(name="L-1", status="Disbursed"), frappe._dict(name="L-2", status="Active")]

		self.assertEqual(account_status(one)["account_status"], "")
		self.assertEqual(account_status(two)["account_status"], "All accounts regular")

	def test_a_fully_drawn_loan_gets_progress_where_it_got_its_own_figure_back(self):
		"""Sanctioned equals disbursed once a loan is fully drawn, so the line was
		repeating the figure above it. How far through they are is the fact that is
		nowhere else on the page."""
		drawn = standing_line(sanctioned=300000, undrawn=0, drawn=300000, repaid=50000)
		partly = standing_line(sanctioned=300000, undrawn=100000, drawn=200000, repaid=0)

		self.assertIn(money(50000), drawn)
		self.assertNotIn("sanctioned", drawn.lower())
		self.assertIn("undrawn", partly.lower())

	def test_nothing_sanctioned_still_says_nothing(self):
		self.assertEqual(standing_line(sanctioned=0, undrawn=0, drawn=0, repaid=0), "")

	def test_one_loans_instalments_stop_repeating_its_name(self):
		"""Four rows of one fixed instalment differ only in date. The name goes up to
		the card's subtitle and the row leads with what actually moves."""
		rows = name_once([self.instalment(), self.instalment()])

		self.assertEqual([row["sub"] for row in rows], ["", ""])
		self.assertEqual([row["title"] for row in rows], [row["detail"] for row in rows])

	def test_two_loans_keep_their_names_on_every_row(self):
		"""With more than one loan the name is what tells the rows apart."""
		rows = name_once([self.instalment("Personal Loan"), self.instalment("Demand Loan")])

		self.assertEqual([row["title"] for row in rows], ["Personal Loan", "Demand Loan"])
		self.assertEqual([row["sub"] for row in rows], [row["detail"] for row in rows])

	def walk(self, nodes) -> list[dict]:
		found = []
		for node in nodes:
			found.append(node)
			found.extend(self.walk(node.get("children") or []))

		return found


class TestPortalActivityList(LendingTestSuite):
	"""The overview's activity list: a line of dots, and one sentence per event.

	It reads the way the desk's own timeline reads, because it answers the same
	question -- has the thing I did landed yet -- and a borrower checking whether their
	payment went through should not have to subtract a date from today to find out.
	"""

	def walk(self, node) -> list[dict]:
		found = [node]
		for child in node.get("children") or []:
			found.extend(self.walk(child))

		return found

	def list_block(self) -> dict:
		return activity_list("activity", "title", "note", url_key="url", date_key="date")

	def test_an_event_from_today_is_not_told_in_hours(self):
		"""The reason days_ago exists rather than frappe.utils.pretty_date.

		These events carry a posting date, which pretty_date reads as midnight: a
		repayment entered this morning came back as "14 hours ago", and one entered
		late last night as "yesterday", though both happened on the same day.
		"""
		self.assertEqual(days_ago(nowdate()), "Today")
		self.assertEqual(days_ago(add_days(nowdate(), -1)), "Yesterday")

	def test_how_long_ago_is_told_in_the_unit_that_fits(self):
		"""Days for a week, then weeks, then months. "56 days ago" is arithmetic."""
		said = [days_ago(add_days(nowdate(), -days)) for days in (3, 8, 40, 400)]

		self.assertEqual(said, ["3 days ago", "1 week ago", "1 month ago", "1 year ago"])

	def test_the_sentence_is_the_event_in_ink_and_the_rest_in_grey(self):
		"""Two spans, not five. The weight changes once, and everything after it --
		how much, which loan, how long ago -- is one grey clause joined in the data
		layer, where the empty parts can drop out without leaving a separator."""
		bodies = [
			node
			for node in self.walk(self.list_block())
			if len(node["children"]) > 1 and all(child.get("dynamicValues") for child in node["children"])
		]
		spans = [child["dynamicValues"][0]["key"] for child in bodies[0]["children"]]

		self.assertEqual(spans, ["title", "note"])

	def test_the_day_it_happened_is_kept_in_the_tooltip(self):
		""""2 days ago" is the faster read; the date is what a borrower needs the
		moment they go looking for the entry on a statement."""
		notes = [
			node
			for node in self.walk(self.list_block())
			if any(value["property"] == "title" for value in node.get("dynamicValues") or [])
		]

		self.assertEqual(len(notes), 1)
		self.assertEqual(notes[0]["dynamicValues"][-1]["key"], "date")

	def test_the_last_dot_does_not_trail_a_line(self):
		"""A stem running on under the final dot is a list that looks truncated.

		The rows are one repeated block, so only a stylesheet can tell the last of them
		apart. Asserted against the markers the blocks actually carry, because renaming
		one of the two and not the other leaves a rule that matches nothing.
		"""
		marked = {
			name
			for node in self.walk(self.list_block())
			for name in (node.get("attributes") or {})
			if name.startswith("data-activity")
		}

		self.assertEqual(marked, {"data-activity-list", "data-activity-stem"})
		for marker in marked:
			self.assertIn(marker, ACTIVITY_CSS)

		self.assertIn(":last-child", ACTIVITY_CSS)
		self.assertIn("extra_css=ACTIVITY_CSS", inspect.getsource(overview_page.build))
