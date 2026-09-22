# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What the rail's bell opens: what the portal owes the borrower, and what it has done.

Two lists, and the split between them is the point. The first is work waiting on the
borrower, the second is what has already happened on their accounts. Both come out in
the same {title, note, when, url} shape, so the two tabs of the panel share one row
block between them rather than having one each.

The panel is the whole of it. There was a /borrower/notifications page behind it once,
saying the same thing at a different size, and a borrower who pressed the bell had two
places to read one list. The bell opens the panel and nothing else now.

No new query answers either list. Both are read from the same functions the account
overview reads, so a notification cannot say something the rest of the portal does not.
"""

import hashlib
import json

import frappe
from frappe import _

from lending.portal.core import (
	get_activity,
	get_applications,
	get_loans,
	get_portal_customers,
	get_upcoming_repayments,
)

# Enough to see where things stand without becoming a second statement of account. A
# borrower with two hundred open applications has two hundred things waiting on them,
# and a list of all of them is a list nobody reads: it shows the first and says how
# many there are, and the Applications page is where the rest live.
ATTENTION_LIMIT = 12
SCHEDULE_LIMIT = 4
ACTIVITY_LIMIT = 15

# Where a borrower's read marks are kept: one DefaultValue row against their User,
# holding the keys of every row they have already seen.
#
# A DocType would be the heavier answer, and nothing here needs one. There is at most
# one value per borrower, it is never queried across borrowers, never reported on and
# never read by anything but the two functions below -- and the list it holds is
# capped by ATTENTION_LIMIT + ACTIVITY_LIMIT, so it cannot grow.
READ_KEY = "lending_portal_alerts_read"


def row_key(row: dict) -> str:
	"""What makes a notification the same notification it was yesterday.

	These rows are derived rather than stored: nothing in the database says "the
	borrower has seen this", because there is no row in the database to say it about.
	The identity has to come out of the row itself, so it is a digest of everything
	the row says. An instalment whose amount moves, or an application that reaches a
	new stage, is a different row and comes back unread, which is the point.

	It follows that the mark is per language: the strings are translated before they
	are hashed, so a borrower who switches language sees their list unread once. That
	is the cost of not storing an id for something that has none, and the whole of it.
	"""
	said = "|".join((row["title"], row["note"], row["when"], row["url"]))

	return hashlib.sha256(said.encode()).hexdigest()[:16]


def read_keys() -> set[str]:
	"""What this borrower has already marked as read. Never raises on bad stored JSON."""
	try:
		return set(json.loads(frappe.defaults.get_user_default(READ_KEY) or "[]"))
	except ValueError:
		return set()


def current_rows() -> tuple[list[dict], list[dict]]:
	"""The two lists, before anything is said about whether they have been read.

	Both endpoints below start here, so what the panel shows and what the double tick
	marks cannot drift apart: they are the same query, run twice.
	"""
	customers = get_portal_customers()
	loans = get_loans(customers) if customers else []
	applications = get_applications(customers) if customers else []

	waiting = attention_rows(applications, get_upcoming_repayments(loans, limit=SCHEDULE_LIMIT))
	activity = activity_rows(get_activity(loans, limit=ACTIVITY_LIMIT))

	return waiting, activity


@frappe.whitelist()
def get_notifications() -> dict:
	"""The two lists on their own, for the panel the bell drops down.

	A GET, because it reads and changes nothing -- and because a portal page carries
	none of the frappe bundle, so it has no CSRF token to send with a POST.

	The panel is opened rather than loaded, so this is not part of the shell's payload:
	a borrower who never presses the bell pays nothing for it.
	"""
	waiting, activity = current_rows()
	shown = waiting[:ATTENTION_LIMIT]
	seen = read_keys()

	# The key stays here. The panel needs to know whether a row is read, not what this
	# server calls it, and a digest of the row is not something to hand out.
	for row in shown + activity:
		row["read"] = row_key(row) in seen

	return {
		"attention": shown,
		"attention_note": attention_note(len(waiting)),
		"activity": activity,
		"activity_note": (
			_("The last {0} events on your accounts").format(len(activity))
			if activity
			else _("Nothing has happened yet")
		),
	}


@frappe.whitelist(methods=["POST"])
def mark_all_as_read() -> dict:
	"""The double tick: everything on the panel right now has been seen.

	A POST, because it writes -- which also means frappe commits it for us at the end
	of the request, and that the page has to send the CSRF token frappe puts in its
	head. The panel's fetch helper does.

	What gets written is what the server can see, not what the browser sends: a
	borrower cannot mark read a row that is not theirs, because no row arrives from
	the browser at all. Writing only the current rows is also what prunes the list --
	a key for something that has since dropped off the panel is simply not rewritten.
	"""
	waiting, activity = current_rows()
	keys = sorted({row_key(row) for row in waiting[:ATTENTION_LIMIT] + activity})
	frappe.defaults.set_user_default(READ_KEY, json.dumps(keys))

	return {"read": len(keys)}


def attention_note(total: int) -> str:
	if not total:
		return _("Nothing to do")

	if total > ATTENTION_LIMIT:
		return _("{0} of {1} waiting on you").format(ATTENTION_LIMIT, total)

	return _("{0} waiting on you").format(total)


def attention_rows(applications: list[dict], schedule: list[dict]) -> list[dict]:
	"""Work waiting on the borrower, each row opening the page that clears it."""
	rows = [
		{
			"title": application["product"],
			"note": application["note"],
			"when": application["stage"],
			"url": application["url"],
		}
		for application in applications
		if application["needs_borrower"]
	]

	rows.extend(
		{
			"title": instalment["product"],
			"note": instalment["detail"],
			"when": _("Due {0} · {1}").format(instalment["date"], instalment["amount"]),
			# An instalment is a line of a schedule rather than a document, so the row
			# opens the loan whose schedule it is on. Where the loan behind the line
			# cannot be named, the accounts list is the nearest page that holds it --
			# an empty href would leave the row looking like a link and acting like a
			# dead end.
			"url": instalment.get("url") or "/borrower-portal/loans",
		}
		for instalment in schedule
	)

	return rows


def activity_rows(events: list[dict]) -> list[dict]:
	"""What has happened, in the same shape as the work that is waiting.

	Every row still leads somewhere. A repayment and a disbursement are both lines of
	the statement of account, which is where a borrower goes to see one in full, so a
	row that is only a record is not also a dead end.
	"""
	return [
		{
			"title": event["title"],
			"note": event["sub"],
			"when": _("{0} · {1}").format(event["amount"], event["date"]),
			"url": "/borrower-portal/statement",
		}
		for event in events
	]
