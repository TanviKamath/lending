# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The public tracker at /track, as a Studio page.

It replaces the /track half of `portal.build.public_pages` and posts to
`track_application`, unchanged -- which is what insists on both the reference number and
the mobile number matching, so neither on its own turns this into a reference-number
oracle.
"""

from lending.portal.studio_build.app import api_resource, page_script, upsert_page
from lending.portal.studio_build.blocks import (
	alert,
	block,
	button,
	card,
	column,
	muted,
	pair_rows,
	reader,
	repeater,
	row,
	text,
)
from lending.portal.studio_build.public import page

TRACK_SOURCE = "track"


read_track = reader(TRACK_SOURCE)

TRACK_SCRIPT = '''\tconst busy = ref(false)
\tconst result = ref<Record<string, any>>({})

\tconst track = () => {
\t\tbusy.value = true
\t\tcall("lending.portal.apply.track_application", {
\t\t\treference: reference.value,
\t\t\tmobile_number: mobileNumber.value,
\t\t})
\t\t\t.then((payload: any) => { result.value = payload })
\t\t\t.catch((error: any) =>
\t\t\t\ttoast.error(String(error?.messages?.[0] || error?.message || error)),
\t\t\t)
\t\t\t.finally(() => { busy.value = false })
\t}'''


def track_form():
	"""Both details have to match, so neither on its own is a reference-number oracle."""
	boxes = row(
		[
			block(
				"FormControl",
				props={
					"type": "text",
					"label": "Reference number",
					"placeholder": "LEAD-0001",
					"modelValue": {"$type": "variable", "name": "reference"},
				},
				styles={"flex": "1", "minWidth": "0px"},
			),
			block(
				"FormControl",
				props={
					"type": "tel",
					"label": "Mobile number",
					"placeholder": "98765 43210",
					"modelValue": {"$type": "variable", "name": "mobileNumber"},
				},
				styles={"flex": "1", "minWidth": "0px"},
			),
		],
		gap="12px",
		align="end",
	)

	return card(
		"Find your application",
		read_track("track_note"),
		column(
			[boxes, button("Show me where it is", script="track()", variant="solid")],
			gap="12px",
		),
	)


def track_result():
	"""The tracker, once both details have matched."""
	step = column(
		[
			row([muted("{{ dataItem.mark }}"), text("{{ dataItem.title }}", size="text-base")], gap="6px"),
			muted("{{ dataItem.note }}"),
		],
		gap="2px",
		styles={"flex": "1", "minWidth": "0px"},
	)

	return card(
		"{{ result.headline }}",
		"{{ result.message }}",
		column(
			[
				repeater(
					"{{ result.steps }}",
					step,
					data_key="title",
					styles={"display": "flex", "flexDirection": "row", "gap": "12px"},
					mobile={"flexDirection": "column"},
				),
				pair_rows("{{ result.offer }}", data_key="label"),
				alert("{{ result.reference_note }}"),
			],
			gap="12px",
		),
		visible="{{ result.reference }}",
	)


def build_track():
	body = [
		text(read_track("heading"), tag="h1", size="text-5xl", styles={"fontWeight": "600"}),
		muted(read_track("intro")),
		track_form(),
		track_result(),
	]

	return upsert_page(
		"Track your application",
		"/track",
		page(read_track, [("Apply for a loan", "/apply"), ("Log in", "/login")], body),
		[api_resource(TRACK_SOURCE, "lending.portal.apply.get_track_page")],
		script=page_script(
			state=[("reference", '""'), ("mobileNumber", '""')],
			body=TRACK_SCRIPT,
			returns=["busy", "result", "track"],
		),
		allow_guest=True,
	)


def build():
	return build_track()
