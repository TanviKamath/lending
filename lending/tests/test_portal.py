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

from unittest.mock import patch

import frappe
from frappe.utils import add_years, nowdate

from lending.portal import assert_owns, get_portal_customers, leads_for_login
from lending.portal_accounts import customer_for_email
from lending.portal_applications import (
	get_application_detail,
	get_applications_page,
	get_document_choices,
	upload_document,
)
from lending.portal_apply import (
	confirm_mobile_code,
	create_account,
	get_apply_page,
	send_mobile_code,
	submit_lead,
	track_application,
)
from lending.portal_loans import get_loan_detail, get_loans_page
from lending.portal_profile import get_profile_page, save_profile
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
		with patch("lending.portal_apply.telephony_otp") as telephony:
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
		with patch("lending.portal_apply.telephony_otp") as telephony:
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
		with patch("lending.portal_apply.telephony_otp") as telephony:
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
		with patch("lending.portal_apply.telephony_otp") as telephony:
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
