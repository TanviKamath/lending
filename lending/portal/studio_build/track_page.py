# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The public tracker at /track, as a Studio page.

It replaces the /track page of the Builder portal this one was migrated from, and posts
to
`track_application`, unchanged -- which is what insists on both the reference number and
the mobile number matching, so neither on its own turns this into a reference-number
oracle.
"""

from lending.portal.studio_build.app import api_resource, page_script, upsert_page
from lending.portal.studio_build.blocks import (
	PANEL,
	block,
	button,
	column,
	container,
	heading,
	icon,
	icon_tile,
	muted,
	reader,
	repeater,
	row,
	slot,
	text,
)
from lending.portal.studio_build.public import page

TRACK_SOURCE = "track"


read_track = reader(TRACK_SOURCE)

TRACK_SCRIPT = '''\tconst busy = ref(false)
\tconst result = ref<Record<string, any>>({})

\tconst find = () => {
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
\t}

\tconst startOver = () => { result.value = {} }'''


PAGE_WIDTH = "840px"

# The form and the result are one panel apart on the page, so they share its shape.
SHEET = dict(PANEL, padding="28px", borderRadius="var(--radius-6)")
SHEET_MOBILE = {"padding": "20px"}


def intro():
	"""What this page is for, centred over the form the way the mockup sets it."""
	centred = {"textAlign": "center", "alignSelf": "center"}

	eyebrow = text(
		read_track("eyebrow"),
		tag="span",
		size="text-sm",
		styles=dict(
			centred,
			textTransform="uppercase",
			letterSpacing="0.06em",
			color="var(--ink-gray-6)",
		),
	)
	title = text(
		read_track("heading"),
		tag="h1",
		size="text-5xl",
		# Studio's type scale stops short of a headline this size, so the size is a style.
		styles=dict(
			centred,
			fontSize="clamp(28px, 4.4vh, 40px)",
			fontWeight="700",
			lineHeight="1.15",
			letterSpacing="-0.02em",
			color="var(--ink-gray-9)",
		),
		mobile={"fontSize": "1.75rem"},
	)
	note = text(
		read_track("intro"),
		size="text-lg",
		# The payload puts each sentence on a line of its own; a phone still wraps them.
		styles=dict(centred, maxWidth="680px", lineHeight="1.6", color="var(--ink-gray-6)", whiteSpace="pre-line"),
	)

	return column(
		[eyebrow, column([title, note], gap="10px")],
		gap="16px",
		styles={"alignItems": "center", "padding": "clamp(8px, 3vh, 32px) 0 clamp(8px, 2vh, 20px)"},
	)


def field(label, ref_name, kind, placeholder, glyph):
	"""One of the two details, led by a glyph saying which it is."""
	return block(
		"FormControl",
		props={
			"type": kind,
			"label": label,
			"placeholder": placeholder,
			"required": True,
			"size": "lg",
			"variant": "outline",
			"modelValue": {"$type": "variable", "name": ref_name},
		},
		slots=slot("prefix", [icon(glyph, size=18, styles={"color": "var(--ink-gray-5)"})]),
		styles={"flex": "1", "minWidth": "0px"},
	)


def track_form():
	"""Both details have to match, so neither on its own is a reference-number oracle."""
	head = row(
		[
			icon_tile("file-search-corner", tile=48, glyph=22),
			heading(read_track("track_title"), size="text-xl"),
		],
		gap="16px",
	)
	boxes = row(
		[
			field("Reference number", "reference", "text", "e.g. LEAD-0001", "file-text"),
			field("Mobile number", "mobileNumber", "tel", "e.g. 98765 43210", "phone"),
		],
		gap="24px",
		align="end",
		mobile={"flexDirection": "column", "alignItems": "stretch", "gap": "16px"},
	)
	# The label goes in the default slot as well as the prop: once a block has any slot,
	# Studio hands Button an empty default one too, and Button renders that over `label`.
	show = button(
		"Show me where it is",
		script="find()",
		variant="solid",
		props={"size": "lg", "loading": "{{ busy }}"},
		slots={
			**slot("suffix", [icon("arrow-right", size=16)]),
			**slot("default", [text("Show me where it is", tag="span", size="text-lg", styles={"fontWeight": "500"})]),
		},
		styles={"alignSelf": "flex-end"},
		mobile={"alignSelf": "stretch"},
	)

	return column([head, boxes, show], gap="24px", styles=SHEET, mobile=SHEET_MOBILE)


DOT = 28

# What the dot of each step state looks like: its fill, its ring, and what sits in it.
DOT_STATES = {
	# A wash of the lender's primary colour, and green where none is set.
	"done": (
		"var(--portal-primary-soft, var(--surface-green-2))",
		"var(--portal-primary-soft, var(--surface-green-2))",
		"var(--portal-primary-deep, var(--ink-green-7))",
		"check",
	),
	# The step the application is on wears the lender's primary colour, where one is set.
	"now": (
		"var(--portal-primary, var(--surface-gray-9))",
		"var(--portal-primary, var(--surface-gray-9))",
		"var(--portal-primary-ink, var(--surface-base))",
		None,
	),
	"todo": ("var(--surface-base)", "var(--outline-gray-3)", "var(--ink-gray-4)", None),
	"stopped": ("var(--surface-red-2)", "var(--surface-red-2)", "var(--ink-red-6)", "x"),
}


def step_dot(state, fill, ring, ink, glyph):
	"""The dot for one state. A dot is a style, and only props are evaluated, so each
	state is its own block and the step's `state` shows one of them."""
	inside = [icon(glyph, size=14, stroke=3)] if glyph else []
	if state == "now":
		# A ring: the dot's own fill with the page showing through the middle of it.
		inside = [container(styles={"width": "10px", "height": "10px", "borderRadius": "9999px", "backgroundColor": ink})]

	return row(
		inside,
		gap="0px",
		styles={
			"width": f"{DOT}px",
			"height": f"{DOT}px",
			"flex": "0 0 auto",
			"justifyContent": "center",
			"borderRadius": "9999px",
			"border": f"1.5px solid {ring}",
			"backgroundColor": fill,
			"color": ink,
			# Over the rail, which runs behind every dot.
			"position": "relative",
		},
		visible="{{ dataItem.state === '%s' }}" % state,
	)


def timeline():
	"""The steps top to bottom, a dot for each on a rail that joins them."""
	step = row(
		[
			*[step_dot(state, *look) for state, look in DOT_STATES.items()],
			column(
				[
					text("{{ dataItem.title }}", size="text-base", styles={"fontWeight": "500", "color": "var(--ink-gray-9)"}),
					text("{{ dataItem.note }}", size="text-p-sm", styles={"color": "var(--ink-gray-6)"}),
				],
				gap="2px",
				styles={"flex": "1 1 auto", "minWidth": "0px", "paddingTop": "4px"},
			),
		],
		gap="14px",
		align="start",
	)
	# The rail stops at the first and last dots' centres, so it never pokes out past them.
	rail = container(
		styles={
			"position": "absolute",
			"top": f"{DOT // 2}px",
			"bottom": f"{DOT // 2}px",
			"left": f"{DOT // 2}px",
			"width": "1.5px",
			"transform": "translateX(-50%)",
			"backgroundColor": "var(--outline-gray-2)",
		}
	)
	steps = repeater(
		"{{ result.steps || [] }}",
		step,
		data_key="title",
		styles={"display": "flex", "flexDirection": "column", "gap": "20px"},
	)

	return container([rail, steps], styles={"position": "relative"})


def figures():
	"""What was asked for and where it stands, side by side on a quiet band."""
	figure = column(
		[
			muted("{{ dataItem.label }}"),
			text("{{ dataItem.value }}", size="text-lg", styles={"fontWeight": "600", "color": "var(--ink-gray-9)"}),
		],
		gap="4px",
	)

	return repeater(
		"{{ result.offer || [] }}",
		figure,
		data_key="label",
		styles={
			"display": "grid",
			"gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
			"gap": "16px",
			"padding": "16px 20px",
			"borderRadius": "var(--radius-5)",
			"backgroundColor": "var(--surface-gray-1)",
		},
		mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
	)


def track_result():
	"""The tracker, once both details have matched."""
	head = row(
		[
			icon_tile("file-text", tile=48, glyph=22),
			column(
				[heading("{{ result.headline }}", size="text-xl"), muted("{{ result.message }}")],
				gap="2px",
				styles={"flex": "1 1 auto", "minWidth": "0px"},
			),
		],
		gap="16px",
	)
	after = row(
		[
			icon("info", size=16, styles={"color": "var(--ink-gray-5)"}),
			muted("{{ result.reference_note }}", styles={"flex": "1 1 auto"}),
			button("Log in", script="window.location.href = '/login'", variant="outline", props={"size": "md"}),
		],
		gap="10px",
		styles={"paddingTop": "20px", "borderTop": "1px solid var(--outline-gray-1)"},
	)

	return column(
		[head, figures(), timeline(), after],
		gap="24px",
		styles=SHEET,
		mobile=SHEET_MOBILE,
	)


def back():
	"""Back to the form, with both details still in it."""
	# The label goes in the default slot too, for the same reason as the form's button.
	return button(
		"Track another application",
		script="startOver()",
		variant="ghost",
		slots={
			**slot("prefix", [icon("arrow-left", size=16)]),
			**slot("default", [text("Track another application", tag="span", size="text-base")]),
		},
		styles={"alignSelf": "flex-start"},
	)


def build_track():
	# The form and the result are two screens: a match swaps one for the other.
	asking = "{{ !result.reference }}"
	found = "{{ result.reference }}"
	body = [
		column([intro(), track_form()], visible=asking),
		column([back(), track_result()], visible=found),
	]

	return upsert_page(
		"Track your application",
		"/track",
		page(read_track, [("Apply for a loan", "/apply"), ("Log in", "/login", "user")], body, width=PAGE_WIDTH),
		[api_resource(TRACK_SOURCE, "lending.portal.apply.get_track_page")],
		script=page_script(
			state=[("reference", '""'), ("mobileNumber", '""')],
			body=TRACK_SCRIPT,
			# Not `track`: that is the data source's name, and a script value of the same
			# name shadows it, so every `track.data` binding on the page reads nothing.
			returns=["busy", "result", "find", "startOver"],
			search=False,
		),
		allow_guest=True,
	)


def build():
	return build_track()
