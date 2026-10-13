import frappe

from lending.loan_management.doctype.loan_security_assignment.loan_security_assignment import (
	make_release_for_assignment,
)


def execute():
	# A Released assignment used to drop out of the pledged count with no Loan Security Release.
	# Released assignments now count and only releases are subtracted, so give each one the
	# release it never had. Every pledged quantity stays as it was.
	for name in frappe.get_all(
		"Loan Security Assignment", filters={"docstatus": 1, "status": "Released"}, pluck="name"
	):
		lsa = frappe.get_doc("Loan Security Assignment", name)
		release = make_release_for_assignment(lsa, lsa.get("release_reference") or "Not recorded")
		release.update(
			{"docstatus": 1, "status": "Approved", "unpledge_time": lsa.release_time or lsa.modified}
		)
		release.flags.ignore_validate = True
		release.flags.ignore_permissions = True
		release.flags.ignore_links = True
		release.insert()
