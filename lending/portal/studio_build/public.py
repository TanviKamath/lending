# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The frame the two public pages share.

Neither /apply nor /track wears the borrower frame. Every row in that sidebar needs a
login, so a guest clicking one would be bounced; they carry this top bar instead, which
is why it is here rather than in `shell`.

Both pages are published with `allow_guest`, which is what lets the app renderer serve
them to somebody who has not signed in -- and, because one published guest page makes
the whole app guest-renderable, what lets the router reach them at all.
"""

from lending.portal.studio_build.blocks import button, container, root, row, spacer, text


def page(read, links, body):
	"""A public page: the bar, then one column of content, centred and capped."""
	well = container(
		body,
		styles={
			"display": "flex",
			"flexDirection": "column",
			"gap": "16px",
			"padding": "24px 20px",
			"width": "100%",
			"maxWidth": "720px",
			"margin": "0 auto",
		},
	)

	return root(
		[
			container(
				[top_bar(read, links), well],
				styles={
					"display": "flex",
					"flexDirection": "column",
					"width": "100%",
					"height": "100%",
					"overflowY": "auto",
				},
			)
		],
		direction="column",
	)


def top_bar(read, links):
	"""The lender's name, and the two other places a visitor might want to be."""
	return row(
		[
			text(read("brand_name"), tag="span", size="text-lg", styles={"fontWeight": "600"}),
			spacer(),
			*[
				button(label, script=f"window.location.href = '{href}'", variant="ghost")
				for label, href in links
			],
		],
		gap="8px",
		styles={
			"padding": "12px 20px",
			"width": "100%",
			"borderWidth": "0px 0px 1px 0px",
			"borderStyle": "solid",
			"borderColor": "var(--outline-gray-2)",
		},
	)
