import frappe
from frappe.utils import flt

from lending.loan_management.doctype.loan_security_assignment.loan_security_assignment import (
	make_release_for_assignment,
)
from lending.loan_management.doctype.loan_security_release.loan_security_release import (
	LOCKED_STATUSES,
	PLEDGED_STATUSES,
	get_unpledge_fields,
	get_unreleased_qty,
)


def execute():
	# Release rows now name the assignment they free, and only approved releases reduce the
	# pledged quantity. Bring existing data into that shape.
	link_existing_releases()
	release_uncovered_released_assignments()
	mark_covered_assignments_released()


def link_existing_releases():
	# The old Release button marked an assignment Released without a release. A release made
	# by hand for the same shares most likely belongs to it, so Released assignments are
	# matched first, then the oldest pledges.
	fields = get_unpledge_fields()
	releases = frappe.get_all(
		"Loan Security Release",
		filters={"docstatus": 1},
		fields=["name", "applicant_type", "applicant", "loan"],
		order_by="creation asc",
	)

	for release in releases:
		rows = frappe.get_all(
			"Unpledge",
			filters={"parent": release.name, "parenttype": "Loan Security Release"},
			fields=["name", "idx", *fields],
			order_by="idx asc",
		)
		if all(row.loan_security_assignment for row in rows):
			continue

		candidates = get_candidates(release)
		unreleased = get_unreleased_qty(candidates)
		next_idx = max(row.idx for row in rows) + 1

		for row in rows:
			if row.loan_security_assignment:
				continue

			pieces, remaining = [], flt(row.qty)
			for name in candidates:
				free = flt(unreleased.get((name, row.loan_security)))
				if remaining <= 0:
					break
				if free <= 0:
					continue
				qty = min(free, remaining)
				pieces.append((name, qty))
				unreleased[(name, row.loan_security)] -= qty
				remaining -= qty

			if not pieces:
				continue
			if remaining > 0:
				pieces.append((None, remaining))

			first, *rest = pieces
			frappe.db.set_value(
				"Unpledge",
				row.name,
				{"loan_security_assignment": first[0], "qty": first[1]},
				update_modified=False,
			)
			for assignment, qty in rest:
				piece = frappe.get_doc(
					{
						**{field: row.get(field) for field in fields},
						"doctype": "Unpledge",
						"parent": release.name,
						"parenttype": "Loan Security Release",
						"parentfield": "securities",
						"idx": next_idx,
						"docstatus": 1,
						"qty": qty,
						"loan_security_assignment": assignment,
					}
				)
				piece.db_insert()
				next_idx += 1


def get_candidates(release):
	filters = {"docstatus": 1, "status": ("in", PLEDGED_STATUSES)}
	if release.loan:
		filters["loan"] = release.loan
	else:
		filters.update({"applicant_type": release.applicant_type, "applicant": release.applicant})

	assignments = frappe.get_all(
		"Loan Security Assignment",
		filters=filters,
		fields=["name", "status"],
		order_by="pledge_time asc, creation asc",
	)
	return [d.name for d in assignments if d.status == "Released"] + [
		d.name for d in assignments if d.status != "Released"
	]


def release_uncovered_released_assignments():
	for name in frappe.get_all(
		"Loan Security Assignment", filters={"docstatus": 1, "status": "Released"}, pluck="name"
	):
		uncovered = {
			security: qty for (_name, security), qty in get_unreleased_qty([name]).items() if qty > 0
		}
		if not uncovered:
			continue

		lsa = frappe.get_doc("Loan Security Assignment", name)
		release = make_release_for_assignment(lsa, uncovered, lsa.get("release_reference") or "Not recorded")
		release.update(
			{"docstatus": 1, "status": "Approved", "unpledge_time": lsa.release_time or lsa.modified}
		)
		release.flags.ignore_validate = True
		release.flags.ignore_permissions = True
		release.flags.ignore_links = True
		release.insert()


def mark_covered_assignments_released():
	for name in frappe.get_all(
		"Loan Security Assignment", filters={"docstatus": 1, "status": ("in", LOCKED_STATUSES)}, pluck="name"
	):
		unreleased = get_unreleased_qty([name], approved_only=True)
		if not unreleased or any(qty > 0 for qty in unreleased.values()):
			continue

		unpledge = frappe.qb.DocType("Unpledge")
		release = frappe.qb.DocType("Loan Security Release")
		last = (
			frappe.qb.from_(unpledge)
			.inner_join(release)
			.on(unpledge.parent == release.name)
			.select(release.unpledge_time, unpledge.release_reference)
			.where(unpledge.loan_security_assignment == name)
			.where(release.docstatus == 1)
			.where(release.status == "Approved")
			.orderby(release.unpledge_time, order=frappe.qb.desc)
			.limit(1)
		).run()

		frappe.db.set_value(
			"Loan Security Assignment",
			name,
			{
				"status": "Released",
				"release_time": last[0][0] if last else None,
				"release_reference": last[0][1] if last else None,
			},
			update_modified=False,
		)
