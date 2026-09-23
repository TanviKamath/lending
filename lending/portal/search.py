# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What the Ctrl+K palette finds: the borrower's own records, by any word in them.

Nothing here queries with a LIKE. The page asks the same functions every other portal
page asks -- get_loans, get_applications -- and filters what comes back. That is what
keeps a result honest: a row can only be found if some page already shows it, and it
is already scoped to this login, because those functions take the borrower's own
customers and nothing else.

What it does not reuse is present_loan. That shape costs a query per loan for the next
instalment, which a list of one loan can afford and a search across every loan cannot;
a result row needs the product, the number and what is owed, and all three are on the
row get_loans already returned.
"""

import frappe
from frappe import _

from lending.portal.core import (
	application_url,
	clean,
	get_applications,
	get_loans,
	get_portal_customers,
	loan_url,
	money,
	nav_items,
	outstanding_of,
	status_label,
)

# A borrower with hundreds of accounts can match hundreds of rows on one common word,
# and a palette of those is not an answer. It shows five, as the desk's awesomebar
# does, and says how many it is holding back, which is the prompt to type a second word.
RESULT_LIMIT = 5


def results_for(query: str, customers: list[str], limit: int = RESULT_LIMIT) -> tuple[list[dict], str]:
	"""The page of results for a query, and the line that says how it went.

	An empty box is not an empty answer. The desk's command bar opens already holding
	the places you can go, and so does this: the portal's own pages, which is also the
	one list a borrower with no loans yet has anything to gain from. It costs nothing
	either -- the records are not read at all until there is something to match them
	against.
	"""
	if not query:
		return page_rows()[:limit], results_note(query, 0, limit)

	found = matches(query, searchable(customers))

	return found[:limit], results_note(query, len(found), limit)


def page_rows() -> list[dict]:
	"""The portal's own pages, as things a search can return.

	Read from the same portal menu the sidebar is drawn from, so a page added to
	lending.hooks.portal_menu_items is findable here the moment it is reachable there.
	"""
	return [
		{"title": item["nav_title"], "note": "", "kind": _("Page"), "url": item["nav_route"]}
		for item in nav_items()
	]


@frappe.whitelist(methods=["GET"])
def find() -> dict:
	"""The results for the palette, fetched as the borrower types.

	Only the results, not the portal frame: the palette sits over a page that already
	has one, and it asks again on every pause in the typing.
	"""
	results, note = results_for(clean(frappe.form_dict.get("q")), get_portal_customers())

	return {"results": results, "note": note}


def searchable(customers: list[str]) -> list[dict]:
	"""Everything a search can return, in one flat list: the pages, then the records."""
	rows = page_rows()
	if not customers:
		return rows

	applications = get_applications(customers)
	rows.extend(loan_row(loan) for loan in get_loans(customers))
	rows.extend(application_row(application) for application in applications)
	rows.extend(document_rows(applications))

	return rows


def loan_row(loan: dict) -> dict:
	return {
		"title": loan.loan_product,
		"note": _("{0} · {1} outstanding · {2}").format(
			loan.name, money(outstanding_of(loan)), status_label(loan)
		),
		"kind": _("Loan account"),
		"url": loan_url(loan.name),
	}


def application_row(application: dict) -> dict:
	return {
		"title": application["product"],
		"note": "{0} · {1}".format(application["reference"], application["stage"]),
		"kind": _("Application"),
		"url": application["url"],
	}


def document_rows(applications: list[dict]) -> list[dict]:
	"""Every document sent with any of these applications, in one query.

	applications.document_rows answers for one application at a time, which is right
	for the page that lists them one application at a time and wrong here: a borrower
	with fifty applications would pay fifty queries to search the word "PAN".

	Permissions are skipped for the same reason that function skips them: Loan
	Application Document is a child table with no rules of its own, and the parents
	have already been narrowed to this borrower's applications.
	"""
	names = [application["name"] for application in applications]
	if not names:
		return []

	return [
		{
			# A document has no page of its own, so it opens the application it came with.
			"title": row.document_type or _("Document"),
			"note": _("Attached to {0}").format(row.parent),
			"kind": _("Document"),
			"url": application_url(row.parent),
		}
		for row in frappe.get_all(
			"Loan Application Document",
			filters={"parent": ["in", names], "parenttype": "Loan Application"},
			fields=["parent", "document_type"],
			ignore_permissions=True,
		)
	]


def matches(query: str, rows: list[dict]) -> list[dict]:
	"""Rows carrying every word of the query, in any order and in any of their fields.

	Every word rather than the whole string: a borrower who remembers the product and
	half the number types both, and would find nothing if the two had to sit together
	in that order.
	"""
	words = query.lower().split()

	return [row for row in rows if all(word in haystack(row) for word in words)]


def haystack(row: dict) -> str:
	"""A row's own words. What is shown is what is searched -- nothing hidden matches."""
	return " ".join((row["title"], row["note"], row["kind"])).lower()


def results_note(query: str, total: int, limit: int = RESULT_LIMIT) -> str:
	# An empty box needs no caption: the placeholder already says what to type.
	if not query:
		return ""

	if not total:
		return _("Nothing matches that")

	if total > limit:
		return _("{0} of {1} found · add a word to narrow it").format(limit, total)

	return _("{0} found").format(total)
