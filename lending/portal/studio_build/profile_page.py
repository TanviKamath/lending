# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower's Personal details page, as a Studio page.

It replaces `portal.build.profile_page` and reads `get_profile_page`, posting back to
`save_profile` -- the same two endpoints, and the same fixed list of fields, because
section 6.3 of PORTAL_PLAN.md is what decides which of them a borrower may correct.
Name and tax id appear in the list and in no input: they are the outcome of a KYC
check rather than a preference.

The page reads first and edits second. The form stays hidden until the Edit button is
pressed, because a borrower opening this page has come to check what is on record far
more often than to change it, and a page that opens with nine empty boxes below the
answer asks to be filled in.

The Builder page did that with a data-reveals attribute the shared client script wired
up. Here it is a ref, and the form's boxes are FormControls filled from the payload
once the page loads.
"""

from lending.portal.studio_build.app import api_resource, page_script, upsert_page
from lending.portal.studio_build.blocks import (
	alert,
	block,
	button,
	card,
	column,
	container,
	pair_rows,
	reader,
	row,
)
from lending.portal.studio_build.shell import frame

SOURCE = "profile"
read = reader(SOURCE)

# The boxes, and the payload key each opens filled from. `save_profile` reads exactly
# these names off the request and nothing else, so a box added here without a matching
# field there changes nothing.
FIELDS = (
	("Email", "email", "email"),
	("Mobile", "mobile", "tel"),
	("Phone", "phone", "tel"),
	("Address line 1", "address_line1", "text"),
	("Address line 2", "address_line2", "text"),
	("City", "city", "text"),
	("State", "state", "text"),
	("Pin code", "pincode", "text"),
	("Country", "country", "text"),
)

# The form's own state. It is filled from the payload rather than declared with values,
# because the payload is what knows the borrower's current details -- and it arrives
# after the script has run, so a watcher rather than an initial value.
FORM = '''\tconst form = ref<Record<string, string>>({})
\tconst customer = ref("")
\tconst saving = ref(false)

\tconst fillForm = () => {
\t\tconst data = context.profile.data || {}
\t\tcustomer.value = data.form_customer || ""
\t\tform.value = Object.fromEntries(
\t\t\t%(fields)s.map((field) => [field, data["form_" + field] || ""]),
\t\t)
\t}
\twatch(() => context.profile.data, fillForm, { immediate: true })

\tconst edit = () => { fillForm(); editing.value = true }

\tconst save = () => {
\t\tsaving.value = true
\t\tcall("lending.portal.profile.save_profile", { customer: customer.value, ...form.value })
\t\t\t.then((result: any) => {
\t\t\t\ttoast.success(result?.message || "Your details have been updated.")
\t\t\t\tediting.value = false
\t\t\t\tcontext.profile.reload()
\t\t\t})
\t\t\t.catch((error: any) => toast.error(String(error.messages?.[0] || error)))
\t\t\t.finally(() => { saving.value = false })
\t}''' % {"fields": [name for _label, name, _kind in FIELDS]}


def edit_form():
	"""One form, aimed at one customer record, posting a fixed list of fields."""
	switcher = block(
		"FormControl",
		props={
			"type": "select",
			"label": "Which record",
			"options": read("customer_options"),
			"modelValue": {"$type": "variable", "name": "customer"},
		},
		visible="{{ %s.data.customer_options.length > 1 }}" % SOURCE,
	)
	boxes = [
		block(
			"FormControl",
			props={
				"type": kind,
				"label": label,
				"modelValue": {"$type": "variable", "name": f"form.{name}"},
			},
		)
		for label, name, kind in FIELDS
	]
	grid = container(
		boxes,
		styles={
			"display": "grid",
			"gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
			"gap": "12px",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
	)
	actions = row(
		[
			button(read("save_label"), script="save()", variant="solid"),
			button("Cancel", script="editing.value = false"),
		],
		gap="8px",
	)

	return card(
		"Edit your details",
		read("form_note"),
		column([switcher, grid, actions], gap="12px"),
		visible="{{ editing }}",
	)


def content():
	return [
		card(
			"On record",
			read("records_note"),
			pair_rows(read("records"), with_detail=True),
			action=button("Edit", script="edit()"),
		),
		alert(read("edit_note")),
		edit_form(),
	]


def build():
	return upsert_page(
		"Personal details",
		"/profile",
		frame(SOURCE, content(), action_label="Contact us", action_route="/borrower/documents"),
		[
			api_resource(SOURCE, "lending.portal.profile.get_profile_page"),
			api_resource("alerts", "lending.portal.notifications.get_notifications", auto=0),
		],
		script=page_script(
			state=[("editing", "false")],
			body=FORM,
			returns=["form", "customer", "edit", "save", "saving"],
		),
	)
