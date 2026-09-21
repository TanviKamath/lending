# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The block vocabulary the Studio pages are written in.

Studio stores a page as a tree of blocks, each naming a Vue component: a frappe-ui one
(Button, Badge, FormControl, List), a Studio one (TextBlock, Repeater, HTML), or the
bare `container`, which renders as a div. This module is the Studio counterpart of
the Builder portal's own theme module, and the difference between the two says what
the migration was:
theme draws a badge as a styled span, and `badge()` below asks for the Badge component.

Almost nothing here sets a colour, a border or a font. The Builder portal carries its
own design system -- some thirty CSS custom properties driven by Lending Settings --
and the Studio pages deliberately do not: they take frappe-ui's own appearance first,
so what is on the canvas is a component to restyle rather than a div already painted.
Only layout (flex, gap, padding, width) is written here.

A value in a prop can be a `{{ }}` expression, evaluated against the page's data
sources, its script's return value, and `route`/`router`. That is how a block reads
live data, so most helpers take an expression rather than a string.
"""

# A payload tone -- "", "ok", "warn", "danger" -- read through the page script's own
# `tone()` helper. Written once here so no page spells the call out.
TONE = "tone({0})"


def reader(source):
	"""A page's own way of reading its data source.

	`read = reader("overview")` makes `read("crumb")` the expression
	`{{ overview.data.crumb }}`, and `read()` the whole payload. Every page binds
	dozens of keys, and spelling the source out at each of them is what makes a page
	hard to move to another endpoint.
	"""

	def read(key=""):
		return "{{ %s.data%s }}" % (source, f".{key}" if key else "")

	return read


def block(name, props=None, styles=None, children=None, **kwargs):
	"""One block. `name` is the component, everything else is optional."""
	node = {
		"componentName": name,
		"componentProps": props or {},
		"componentSlots": kwargs.pop("slots", None) or {},
		"componentEvents": kwargs.pop("events", None) or {},
		"baseStyles": styles or {},
		"mobileStyles": kwargs.pop("mobile", None) or {},
		"tabletStyles": kwargs.pop("tablet", None) or {},
		"children": children or [],
	}
	if visible := kwargs.pop("visible", None):
		node["visibilityCondition"] = visible

	node.update(kwargs)

	return node


def slot(name, content):
	"""A named slot, in the shape Studio stores one."""
	return {name: {"slotName": name, "slotContent": content}}


def click(script):
	"""An onclick handler, in the shape Studio stores one."""
	return {"click": {"event": "click", "action": "Run Script", "script": script}}


# --- layout -------------------------------------------------------------------------


def root(children, direction="row"):
	"""The page's one outermost block.

	A page stores a list of blocks and renders the first of them -- AppContainer reads
	`blocks[0]`, and so does the exporter that collects which components a page uses. So
	a page is one root with everything inside it, never two blocks side by side.

	`originalElement: body` is what marks a block the root.
	"""
	return [
		block(
			"div",
			styles={
				"display": "flex",
				"flexDirection": direction,
				"width": "100%",
				"height": "100%",
				"overflowX": "hidden",
			},
			children=children,
			originalElement="body",
			blockName="body",
		)
	]


def container(children=None, styles=None, **kwargs):
	"""A div. `originalElement` is required, or the block and its children do not render."""
	return block("container", styles=styles, children=children, originalElement="div", **kwargs)


def column(children, gap="16px", **kwargs):
	styles = {"display": "flex", "flexDirection": "column", "gap": gap}
	styles.update(kwargs.pop("styles", None) or {})

	return container(children, styles=styles, **kwargs)


def row(children, gap="8px", align="center", **kwargs):
	styles = {"display": "flex", "flexDirection": "row", "alignItems": align, "gap": gap}
	styles.update(kwargs.pop("styles", None) or {})

	return container(children, styles=styles, **kwargs)


# --- text ---------------------------------------------------------------------------


def text(value, tag="p", size="text-p-sm", **kwargs):
	"""A line of copy. `size` follows Studio's own scale; text-p-* is the paragraph family."""
	return block("TextBlock", props={"text": value, "tag": tag, "fontSize": size}, **kwargs)


def heading(value, tag="h2", size="text-lg", **kwargs):
	styles = {"fontWeight": "600"}
	styles.update(kwargs.pop("styles", None) or {})

	return text(value, tag=tag, size=size, styles=styles, **kwargs)


def muted(value, **kwargs):
	"""The quieter second line under a heading or a row."""
	styles = {"color": "var(--ink-gray-6)"}
	styles.update(kwargs.pop("styles", None) or {})

	return text(value, size="text-p-xs", styles=styles, **kwargs)


# --- components -----------------------------------------------------------------------


def badge(label, theme="gray", **kwargs):
	"""A status. `theme` is a frappe-ui theme, or an expression producing one."""
	props = {"label": label, "theme": theme, "variant": "subtle", "size": "sm"}

	return block("Badge", props=props, **kwargs)


def toned_badge(label, tone_expression, **kwargs):
	"""A status whose colour comes from the payload rather than from the page."""
	return badge(label, theme="{{ %s }}" % TONE.format(tone_expression), **kwargs)


def button(label, script=None, variant="subtle", **kwargs):
	props = {"label": label, "variant": variant, "size": "sm"}
	props.update(kwargs.pop("props", None) or {})

	return block("Button", props=props, events=click(script) if script else None, **kwargs)


def alert(message, theme="blue", **kwargs):
	"""A quiet panel of guidance, shown only when the data supplies one."""
	return block("Alert", props={"title": message, "theme": theme}, **kwargs)


def divider(**kwargs):
	return block("Divider", **kwargs)


def instance(component_id, props=None, **kwargs):
	"""A Studio Component, rendered with these inputs.

	A component's own tree reads them as `{{ inputs.<name> }}`. Its children are its
	own: unlike a Builder component, a Studio one cannot be wrapped around page
	content, which is why the portal frame is three components beside the content
	rather than one around it. See shell.
	"""
	return block(component_id, props=props, isStudioComponent=True, **kwargs)


# --- lists ----------------------------------------------------------------------------


def repeater(data, template, data_key="name", empty="", **kwargs):
	"""`template` once per row of `data`. Inside it, a row is `dataItem`."""
	props = {"data": data, "dataKey": data_key, "emptyStateMessage": empty}

	return block("Repeater", props=props, children=[template], **kwargs)


def record_list(columns, items, cells, row_key="name", script=None):
	"""The List family: a header of labels, then one row per record.

	`columns` are CSS grid tracks paired with their heading, and `cells` builds the
	blocks of one row from `item`, the slot's name for the current record. `script`
	makes the whole row the way into the record it stands for.
	"""
	header = block(
		"ListHeader",
		children=[
			block("ListHeaderCell", children=[text(label, size="text-xs")])
			for _track, label in columns
		],
	)
	record = block(
		"ListRow",
		props={"value": "{{ value }}"},
		children=[block("ListCell", children=cell) for cell in cells],
		events=click(script) if script else None,
	)
	rows = block(
		"ListRows",
		props={"items": items, "rowKey": row_key},
		slots=slot("default", [record]),
	)

	return block(
		"List",
		props={"columns": [track for track, _label in columns], "rowHeight": 56},
		children=[header, rows],
	)


def pair_rows(items, with_detail=False, **kwargs):
	"""A repeater over {label, value, detail} rows -- the portal's workhorse shape."""
	body = [muted("{{ dataItem.label }}"), text("{{ dataItem.value }}", size="text-base")]
	if with_detail:
		body.append(muted("{{ dataItem.detail }}", visible="{{ dataItem.detail }}"))

	template = column(body, gap="2px", styles={"padding": "8px 0"})

	return repeater(items, template, empty="Nothing to show", **kwargs)


def pair_grid(items, with_detail=False, **kwargs):
	"""The same rows, three to a row -- eight readings of one record, within a glance."""
	styles = {"display": "grid", "gridTemplateColumns": "repeat(3, minmax(0, 1fr))", "gap": "12px"}
	tablet = {"gridTemplateColumns": "repeat(2, minmax(0, 1fr))"}
	mobile = {"gridTemplateColumns": "minmax(0, 1fr)"}
	body = [muted("{{ dataItem.label }}"), text("{{ dataItem.value }}", size="text-base")]
	if with_detail:
		body.append(muted("{{ dataItem.detail }}", visible="{{ dataItem.detail }}"))

	return repeater(
		items,
		column(body, gap="2px"),
		styles=styles,
		tablet=tablet,
		mobile=mobile,
		**kwargs,
	)


# --- panels ---------------------------------------------------------------------------

# What a card and a number card are both drawn on. The one place this file names a
# colour, because a panel that does not separate itself from the page is not a panel.
PANEL = {
	"padding": "16px",
	"borderWidth": "1px",
	"borderStyle": "solid",
	"borderColor": "var(--outline-gray-2)",
	"borderRadius": "0.5rem",
	"backgroundColor": "var(--surface-base)",
}


def card(title, subtitle, body, action=None, **kwargs):
	"""A titled panel with a subtitle from the data. Every portal page is built of these.

	Studio Components take inputs, not children, so a card cannot be one: its body is
	whatever the page puts in it. It stays a function that builds blocks, the way
	`theme.card` is on the Builder side.
	"""
	parts = ([heading(title)] if title else []) + ([muted(subtitle)] if subtitle else [])
	titles = column(parts, gap="2px")
	head = titles if action is None else row([titles, spacer(), action], align="start")
	children = [body] if not parts and action is None else [head, body]
	styles = dict(PANEL, **(kwargs.pop("styles", None) or {}))

	return column(children, gap="12px", styles=styles, **kwargs)


def stat(title, value, note, flag=None, flag_tone=None, sub=None):
	"""One number card: a label, the figure, and a line saying what it is.

	Not a NumberChart. Every figure on the portal arrives already formatted and
	translated -- "₹3,17,450", "Nothing due" -- because the Builder pages could not
	format one, and a chart that wants a number would print the string as NaN.
	"""
	head = [text(title, size="text-xs")]
	if flag:
		theme = "{{ %s }}" % TONE.format(flag_tone) if flag_tone else "orange"
		head.append(badge(flag, theme=theme, visible=flag))

	body = [text(value, tag="div", size="text-4xl", styles={"fontWeight": "600"}), muted(note)]
	if sub:
		body.append(muted(sub, visible=sub))

	return column(
		[row(head, gap="6px"), column(body, gap="2px")],
		gap="8px",
		styles=dict(PANEL, flex="1"),
	)


def stat_strip(cards):
	styles = {"display": "flex", "flexDirection": "row", "gap": "12px", "width": "100%"}

	return container(cards, styles=styles, tablet={"flexWrap": "wrap"}, mobile={"flexDirection": "column"})


def two_columns(wide, narrow):
	"""The record down the wide side, what is coming down the narrow one."""
	styles = {
		"display": "grid",
		"gridTemplateColumns": "minmax(0, 2fr) minmax(0, 1fr)",
		"gap": "16px",
		"width": "100%",
	}

	return container(
		[column(wide), column(narrow)],
		styles=styles,
		tablet={"gridTemplateColumns": "minmax(0, 1fr)"},
	)


def spacer():
	return container(styles={"flex": "1 1 auto"})
