# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The join between a login and the Customer records it may see.

Everything the borrower portal shows hangs off one row: `Customer.portal_users`. Miss
it and the borrower logs in, sees their own name, and is told they have no loans.
PORTAL_PLAN.md section 12.1.3 asks for that row to be written when an applicant first
becomes a Customer, and this module is where that happens.

It sits apart from the portal pages because two very different callers need it. The
portal opens an account at the end of an application, and `Loan Application` creates a
Customer when staff convert a lead. Both must reach the same record: if they each make
their own, the borrower ends up with two Customers, a login joined to the wrong one,
and loans that are invisible from the portal.

Matching is by email, through the Contact rather than through `Customer.email_id`.
`email_id` is fetched from `customer_primary_contact`, so it is empty on any customer
whose contact was never set -- 22 of the 28 on this bench -- and matching on it alone
would miss them and make a duplicate.
"""

import frappe

# What a portal borrower's Customer looks like. Company covers a business borrowing in
# its own name; Loan Lead calls that applicant_type "Business".
CUSTOMER_TYPES = {"Individual": "Individual", "Business": "Company"}


def customer_for_email(email: str) -> str | None:
	"""The Customer this email already belongs to, if any."""
	if not email:
		return None

	linked = frappe.get_all(
		"Contact",
		filters=[
			["Contact Email", "email_id", "=", email],
			["Dynamic Link", "link_doctype", "=", "Customer"],
		],
		fields=["`tabDynamic Link`.link_name as customer"],
		limit=1,
	)
	if linked:
		return linked[0].customer

	return frappe.db.get_value("Customer", {"email_id": email}, "name")


def create_customer(customer_name: str, customer_type: str, email: str, mobile: str) -> str:
	"""A Customer with a Contact behind it, so its email is readable afterwards.

	The Contact is not decoration. `Customer.email_id` and `mobile_no` are fetched
	from the primary contact rather than stored, so a Customer created without one
	has no email on it and customer_for_email cannot find it next time.
	"""
	customer = frappe.new_doc("Customer")
	customer.update({"customer_name": customer_name, "customer_type": customer_type})
	customer.insert(ignore_permissions=True)

	contact = frappe.new_doc("Contact")
	contact.first_name = customer_name
	if email:
		contact.append("email_ids", {"email_id": email, "is_primary": 1})
	if mobile:
		contact.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})
	contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	contact.insert(ignore_permissions=True)

	customer.customer_primary_contact = contact.name
	customer.save(ignore_permissions=True)

	return customer.name


def customer_for_applicant(
	customer_name: str, applicant_type: str, email: str, mobile: str
) -> str:
	"""The Customer for this applicant: the one they already have, or a new one."""
	return customer_for_email(email) or create_customer(
		customer_name, CUSTOMER_TYPES.get(applicant_type, "Individual"), email, mobile
	)


def link_portal_user(customer: str, user: str) -> bool:
	"""Join a login to a Customer. Returns whether a row was actually added.

	Silent when there is no such login yet: staff often create the Customer before
	the borrower has an account, and the row is added when the account is opened.
	"""
	if not customer or not user or not frappe.db.exists("User", user):
		return False

	record = frappe.get_doc("Customer", customer)
	if any(row.user == user for row in record.portal_users):
		return False

	record.append("portal_users", {"user": user})
	record.save(ignore_permissions=True)

	return True
