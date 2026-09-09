# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the borrower Account overview as a standard Builder page.

Run once per site with:
	bench --site <site> execute lending.portal_page.build

The page is created with is_standard=1 and app="lending", so Builder exports it to
lending/builder_files/ and it ships with the app. Re-running replaces the page in
place, which is how you regenerate after editing this file.

Layout lives in blocks; the stylesheet lives in the page's head_html; brand colours,
fonts and radii live in Builder Token records so a bank restyles without touching
either. Values are the Espresso tokens from the installed frappe source.
"""

from builder.builder.doctype.builder_token.builder_token import clear_builder_token_cache
from builder.utils import Block

import frappe

PAGE_NAME = "Borrower Account Overview"
ROUTE = "borrower/overview"

# A bank overrides these five records. Nothing else in the page carries brand.
BRAND_TOKENS = [
	{"token_name": "brand-primary", "type": "Color", "value": "#171717", "dark_value": "#f8f8f8"},
	{"token_name": "brand-primary-ink", "type": "Color", "value": "#ffffff", "dark_value": "#171717"},
	{"token_name": "brand-mark", "type": "Color", "value": "#2bb24c", "dark_value": "#2fbe6a"},
	{"token_name": "brand-radius", "type": "Dimension", "value": "8px"},
	{"token_name": "brand-font", "type": "Font", "value": "InterVariable"},
]

# One call, so the page makes a single trip to the data layer.
DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer,
# reached through the whitelisted door the Loan Lead server scripts use.
data.update(frappe.call("lending.portal.get_dashboard"))  # noqa: F821
'''

STYLESHEET = """
<!-- Builder Token records are served as :root custom properties by this route, so a bank
	retheming a token in the Builder UI changes this page with no rebuild. Without the
	link the var(--brand-*) references below fall back to their literals. -->
<link rel="stylesheet" href="/builder_assets/tokens.css">
<style>
/* Espresso tokens, copied from frappe/public/css/espresso/. Website pages do not load
	the desk bundle, so the page carries the ones it uses. */
@font-face {
	font-family: InterVariable;
	font-style: normal;
	font-weight: 100 900;
	font-display: swap;
	src: url("/assets/frappe/css/fonts/inter/InterVariable.woff2") format("woff2");
}

:root {
	color-scheme: light;

	--gray-50: #f8f8f8;
	--gray-100: #f3f3f3;
	--gray-200: #ededed;
	--gray-300: #e2e2e2;
	--gray-500: #999999;
	--gray-600: #7c7c7c;
	--gray-700: #525252;
	--gray-900: #171717;
	--gray-950: #0f0f0f;

	--surface-base: #ffffff;
	--surface-sidebar: var(--gray-50);
	--surface-gray-1: var(--gray-50);
	--surface-gray-2: var(--gray-100);
	--border-color: var(--gray-200);
	--outline-gray-2: var(--gray-300);
	--ink-gray-4: var(--gray-500);
	--ink-gray-5: var(--gray-600);
	--text-muted: var(--gray-700);
	--text-color: var(--gray-900);
	--heading-color: var(--gray-950);

	--green-100: #e4faeb;
	--green-700: #14804d;
	--amber-50: #fdf8ed;
	--amber-700: #bb6f0c;

	--radius-1: 4px;
	--radius-3: 6px;
	--radius: 8px;
	--radius-lg: 12px;
	--radius-9: 999px;

	--w-regular: 420;
	--w-medium: 500;
	--w-semibold: 600;

	--text-2xs: 11px;
	--text-xs: 12px;
	--text-sm: 13px;
	--text-base: 14px;
	--text-lg: 16px;
	--text-2xl: 18px;

	--sidebar-active-shadow: 0 0 1px 0 rgba(0, 0, 0, 0.14), 0 1px 3px 0 rgba(0, 0, 0, 0.14);
	--focus-outline: 2px solid #c9c9c9e5;

	--rail-w: 50px;
	--sidebar-width: 220px;
	--page-head-height: 48px;
	--padding-lg: 20px;
	--margin-sm: 10px;
	--grid-gap: 20px;
	--row-y: 12px;
	--pad: 12px;
}

body, .bp-body {
	margin: 0;
	background: var(--surface-base);
	color: var(--text-color);
	font-family: var(--brand-font, InterVariable), "Inter", -apple-system, BlinkMacSystemFont,
		"Segoe UI", Roboto, "Helvetica Neue", sans-serif;
	font-variation-settings: "opsz" 24;
	font-size: var(--text-base);
	font-weight: var(--w-regular);
	letter-spacing: 0.02em;
	line-height: 1.5;
	-webkit-font-smoothing: antialiased;
}

.bp-shell { display: flex; min-height: 100vh; align-items: stretch; }

.bp-rail {
	width: var(--rail-w); flex-shrink: 0; background: var(--surface-sidebar);
	display: flex; flex-direction: column; align-items: center; gap: 4px;
	padding: 11px 0 14px; position: sticky; top: 0; height: 100vh;
}
.bp-mark {
	width: 28px; height: 28px; border-radius: var(--radius); flex-shrink: 0;
	background: var(--brand-mark, #2bb24c); color: #fff;
	display: grid; place-items: center; margin-bottom: 8px;
	font-size: var(--text-xs); font-weight: var(--w-semibold);
}
.bp-rail-spacer { flex: 1 1 auto; }
.bp-avatar {
	width: 28px; height: 28px; border-radius: var(--radius-9); flex-shrink: 0;
	background: var(--green-100); color: var(--green-700);
	display: grid; place-items: center;
	font-size: var(--text-xs); font-weight: var(--w-semibold);
}

.bp-sidebar {
	width: var(--sidebar-width); flex-shrink: 0; background: var(--surface-sidebar);
	border-right: 1px solid var(--border-color);
	display: flex; flex-direction: column; gap: 12px;
	padding: 8px 8px 10px 8px; position: sticky; top: 0; height: 100vh;
}
.bp-side-head { padding: 6px 8px 0; font-size: 15px; font-weight: var(--w-semibold); color: var(--heading-color); }
.bp-switcher { padding: 6px 8px; border-radius: var(--radius); }
.bp-switcher b { display: block; font-size: var(--text-sm); font-weight: var(--w-medium); }
.bp-switcher span { font-size: var(--text-xs); color: var(--ink-gray-5); }
.bp-nav { flex: 1 1 auto; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.bp-nav-item {
	display: flex; align-items: center; gap: var(--margin-sm);
	padding: 6px 8px; border-radius: var(--radius); margin-bottom: 1px;
	font-size: var(--text-sm); color: var(--text-muted); text-decoration: none;
}
.bp-nav-item:hover { background: var(--surface-gray-2); text-decoration: none; color: var(--text-color); }
.bp-nav-item.bp-active {
	background: var(--surface-base); color: var(--text-color);
	font-weight: var(--w-medium); box-shadow: var(--sidebar-active-shadow);
}
.bp-nav-group {
	padding: 6px 8px; margin-top: 10px;
	font-size: var(--text-xs); font-weight: var(--w-medium); color: var(--text-color);
}
.bp-nav-children {
	display: flex; flex-direction: column; gap: 2px;
	margin-left: 11px; border-left: 1px solid var(--border-color);
}
.bp-nav-children .bp-nav-item { margin-left: 5px; }
.bp-side-foot {
	padding: 10px 8px 0; border-top: 1px solid var(--border-color);
}
.bp-side-foot b { display: block; font-size: var(--text-sm); font-weight: var(--w-medium); }
.bp-side-foot span { font-size: var(--text-xs); color: var(--ink-gray-5); }

.bp-main { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
.bp-page-head {
	display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
	min-height: var(--page-head-height); padding: 0 var(--padding-lg);
	border-bottom: 1px solid var(--border-color);
}
.bp-crumb { font-size: var(--text-lg); font-weight: var(--w-medium); color: var(--heading-color); letter-spacing: 0.015em; }
.bp-head-note { font-size: var(--text-sm); color: var(--text-muted); }
.bp-head-end { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.bp-status { display: flex; align-items: center; gap: 6px; font-size: var(--text-sm); color: var(--text-muted); }
.bp-status-dot { width: 6px; height: 6px; border-radius: var(--radius-9); background: var(--green-700); }

.bp-btn {
	font-family: inherit; font-size: var(--text-sm); font-weight: var(--w-medium);
	cursor: pointer; padding: 6px 12px; border-radius: var(--brand-radius, 8px);
	border: 1px solid transparent; white-space: nowrap; text-decoration: none;
	background: var(--brand-primary, #171717); color: var(--brand-primary-ink, #fff);
}
.bp-btn:hover { filter: brightness(1.4); color: var(--brand-primary-ink, #fff); text-decoration: none; }
.bp-btn-quiet { background: var(--surface-gray-2); color: var(--text-color); }
.bp-btn-quiet:hover { background: var(--border-color); filter: none; color: var(--text-color); }

.bp-content { flex: 1 1 auto; padding: var(--padding-lg); display: flex; flex-direction: column; gap: var(--grid-gap); }
.bp-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: var(--grid-gap); }
.bp-ncard {
	min-height: 110px; padding: var(--pad); background: var(--surface-base);
	border: 1px solid var(--border-color); border-radius: var(--radius-lg);
	display: flex; flex-direction: column;
}
.bp-ncard-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.bp-ncard-title { font-size: var(--text-sm); font-weight: var(--w-medium); }
.bp-ncard-body { padding-top: var(--pad); display: flex; flex-direction: column; }
.bp-number {
	font-size: var(--text-2xl); font-weight: var(--w-semibold); letter-spacing: 0.01em;
	line-height: 115%; font-variant-numeric: tabular-nums;
}
.bp-ncard-stat { margin-top: var(--margin-sm); font-size: var(--text-sm); color: var(--text-muted); font-variant-numeric: tabular-nums; }

.bp-grid { display: grid; grid-template-columns: minmax(0, 1.9fr) minmax(0, 1fr); gap: var(--grid-gap); align-items: start; }
.bp-stack { display: flex; flex-direction: column; gap: var(--grid-gap); min-width: 0; }
.bp-card {
	background: var(--surface-base); border: 1px solid var(--border-color);
	border-radius: var(--radius-lg); display: flex; flex-direction: column; min-width: 0;
}
.bp-card-head { padding: var(--pad) var(--pad) 14px; }
.bp-card-head h2 {
	margin: 0; font-size: var(--text-lg); font-weight: var(--w-semibold);
	color: var(--heading-color); line-height: 1.3em; letter-spacing: 0.015em;
}
.bp-card-sub { margin-top: 5px; font-size: var(--text-base); color: var(--text-muted); font-variant-numeric: tabular-nums; }

.bp-thead, .bp-row {
	display: flex; align-items: center; gap: 12px;
	padding: var(--row-y) var(--pad); border-top: 1px solid var(--border-color);
}
.bp-thead { padding: 0 var(--pad) 8px; border-top: 0; border-bottom: 1px solid var(--border-color); }
.bp-thead span { font-size: var(--text-xs); color: var(--ink-gray-5); }
.bp-row:hover { background: var(--surface-gray-1); }
.bp-col-main { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.bp-col-status { width: 150px; flex-shrink: 0; }
.bp-col-next { width: 120px; flex-shrink: 0; display: flex; flex-direction: column; gap: 2px; }
.bp-col-amt { width: 150px; flex-shrink: 0; text-align: right; display: flex; flex-direction: column; gap: 2px; }
.bp-p { font-size: var(--text-sm); font-weight: var(--w-medium); }
.bp-s { font-size: var(--text-xs); color: var(--ink-gray-5); font-variant-numeric: tabular-nums; }
.bp-amt { font-size: var(--text-sm); font-weight: var(--w-medium); font-variant-numeric: tabular-nums; }
.bp-num { font-variant-numeric: tabular-nums; }

.bp-state { display: inline-flex; align-items: center; gap: 6px; font-size: var(--text-sm); color: var(--text-muted); }
.bp-dot { width: 6px; height: 6px; border-radius: var(--radius-9); background: var(--ink-gray-4); flex-shrink: 0; }
.bp-flag {
	display: inline-block; font-size: var(--text-xs); font-weight: var(--w-medium);
	color: var(--amber-700); background: var(--amber-50);
	padding: 2px 8px; border-radius: var(--radius-1);
}
.bp-why { font-size: var(--text-xs); color: var(--amber-700); }
.bp-chip { font-size: var(--text-xs); color: var(--ink-gray-5); }

.bp-li { display: flex; align-items: baseline; gap: 12px; padding: var(--row-y) var(--pad); border-top: 1px solid var(--border-color); }
.bp-li-date { width: 80px; flex-shrink: 0; font-size: var(--text-sm); color: var(--text-muted); font-variant-numeric: tabular-nums; }
.bp-li-body { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.bp-li-amt { flex-shrink: 0; font-size: var(--text-sm); font-weight: var(--w-medium); font-variant-numeric: tabular-nums; }

.bp-footer {
	display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
	padding: 14px var(--padding-lg); border-top: 1px solid var(--border-color);
	font-size: var(--text-xs); color: var(--ink-gray-5);
}
.bp-footer a { color: var(--text-muted); text-decoration: none; margin-right: 18px; }
.bp-footer a:hover { color: var(--text-color); }
.bp-empty { padding: var(--row-y) var(--pad); font-size: var(--text-sm); color: var(--ink-gray-5); border-top: 1px solid var(--border-color); }

a:focus-visible, .bp-btn:focus-visible { outline: var(--focus-outline); outline-offset: 1px; }

@media (max-width: 1100px) { .bp-grid { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 780px) { .bp-sidebar, .bp-rail { display: none; } }
</style>
"""


def block(element, classes=None, children=None, html=None, attributes=None, **kwargs):
	"""A Block with a stable id. Styling comes from classes, not inline styles."""
	options = {
		"blockId": frappe.generate_hash(length=9),
		"element": element,
		"classes": classes or [],
		"attributes": attributes or {},
		"baseStyles": {},
		"mobileStyles": {},
		"tabletStyles": {},
	}
	options.update(kwargs)
	node = Block(**options)
	if html is not None:
		node.innerHTML = html
	if children:
		node.attach_children(*children)

	return node


def bound(element, key, classes=None):
	"""A block whose text comes from the page data script."""
	node = block(element, classes=classes)
	node.set_dynamic_value(key, "key", "innerHTML")
	return node


def repeater(key, row):
	node = block("div", isRepeaterBlock=True)
	node.attach_data_key(key, "dataKey")
	node.attach_children(row)
	return node


def nav_item(label, active=False):
	classes = ["bp-nav-item"] + (["bp-active"] if active else [])
	return block("a", classes=classes, html=label, attributes={"href": "#"})


def nav_group(label, items):
	return block(
		"div",
		children=[
			block("div", classes=["bp-nav-group"], html=label),
			block("div", classes=["bp-nav-children"], children=items),
		],
	)


def sidebar():
	return block(
		"aside",
		classes=["bp-sidebar"],
		children=[
			block("div", classes=["bp-side-head"], html="Meridian Finance"),
			block(
				"div",
				classes=["bp-switcher"],
				children=[
					block("b", html="All customer records"),
					bound("span", "customer_note"),
				],
			),
			block(
				"nav",
				classes=["bp-nav"],
				children=[
					nav_item("Account overview", active=True),
					nav_group(
						"Borrowing",
						[
							nav_item("Loan accounts"),
							nav_item("Repayments"),
							nav_item("Disbursements"),
							nav_item("Charges"),
						],
					),
					nav_group("Applications", [nav_item("In progress"), nav_item("Documents")]),
					nav_group(
						"Statements",
						[nav_item("Statement of account"), nav_item("Interest certificate")],
					),
					nav_group("Profile", [nav_item("Personal details"), nav_item("Bank accounts")]),
				],
			),
			block(
				"div",
				classes=["bp-side-foot"],
				children=[bound("b", "holder_name"), bound("span", "customer_note")],
			),
		],
	)


def rail():
	return block(
		"div",
		classes=["bp-rail"],
		children=[
			block("span", classes=["bp-mark"], html="M"),
			block("span", classes=["bp-rail-spacer"]),
			block("span", classes=["bp-avatar"], html="TK"),
		],
	)


def page_head():
	return block(
		"div",
		classes=["bp-page-head"],
		children=[
			block("span", classes=["bp-crumb"], html="Account overview"),
			bound("span", "head_note", classes=["bp-head-note"]),
			block(
				"div",
				classes=["bp-head-end"],
				children=[
					block(
						"span",
						classes=["bp-status"],
						children=[
							block("span", classes=["bp-status-dot"]),
							bound("span", "account_status"),
						],
					),
					block(
						"a",
						classes=["bp-btn"],
						html="View payment details",
						attributes={"href": "/borrower/repayments"},
					),
				],
			),
		],
	)


def number_card(title_key, value_key, stat_key, flag_key=None):
	head_children = [bound("span", title_key, classes=["bp-ncard-title"])]
	if flag_key:
		flag = bound("span", flag_key, classes=["bp-flag"])
		flag.visibilityCondition = flag_key
		head_children.append(flag)

	return block(
		"div",
		classes=["bp-ncard"],
		children=[
			block("div", classes=["bp-ncard-head"], children=head_children),
			block(
				"div",
				classes=["bp-ncard-body"],
				children=[
					bound("div", value_key, classes=["bp-number"]),
					bound("div", stat_key, classes=["bp-ncard-stat"]),
				],
			),
		],
	)


def number_cards():
	return block(
		"section",
		classes=["bp-cards"],
		children=[
			number_card("label_next", "next_amount", "next_note", flag_key="next_flag"),
			number_card("label_outstanding", "outstanding", "outstanding_note"),
			number_card("label_sanctioned", "sanctioned", "sanctioned_note"),
		],
	)


def card(title, subtitle_key, body):
	return block(
		"section",
		classes=["bp-card"],
		children=[
			block(
				"div",
				classes=["bp-card-head"],
				children=[
					block("h2", html=title),
					bound("div", subtitle_key, classes=["bp-card-sub"]),
				],
			),
			body,
		],
	)


def thead(labels):
	widths = ["bp-col-main", "bp-col-status", "bp-col-next", "bp-col-amt"]
	return block(
		"div",
		classes=["bp-thead"],
		children=[
			block("span", classes=[widths[i]], html=label) for i, label in enumerate(labels)
		],
	)


def accounts_body():
	row = block(
		"div",
		classes=["bp-row"],
		children=[
			block(
				"div",
				classes=["bp-col-main"],
				children=[bound("div", "product", classes=["bp-p"]), bound("div", "terms", classes=["bp-s"])],
			),
			block(
				"div",
				classes=["bp-col-status"],
				children=[
					block(
						"span",
						classes=["bp-state"],
						children=[block("span", classes=["bp-dot"]), bound("span", "status_label")],
					)
				],
			),
			block(
				"div",
				classes=["bp-col-next"],
				children=[bound("div", "next_date", classes=["bp-num"]), bound("div", "next_amount", classes=["bp-s"])],
			),
			block(
				"div",
				classes=["bp-col-amt"],
				children=[bound("div", "outstanding", classes=["bp-amt"]), bound("div", "against", classes=["bp-s"])],
			),
		],
	)

	return block(
		"div",
		children=[
			thead(["Account", "Status", "Next repayment", "Outstanding"]),
			repeater("accounts", row),
		],
	)


def applications_body():
	why = bound("div", "note", classes=["bp-why"])
	why.visibilityCondition = "note"

	row = block(
		"div",
		classes=["bp-row"],
		children=[
			block(
				"div",
				classes=["bp-col-main"],
				children=[
					bound("div", "product", classes=["bp-p"]),
					bound("div", "reference", classes=["bp-s"]),
					why,
				],
			),
			block(
				"div",
				classes=["bp-col-status"],
				children=[bound("span", "stage", classes=["bp-state"])],
			),
			block(
				"div",
				classes=["bp-col-amt"],
				children=[bound("div", "amount", classes=["bp-amt"])],
			),
		],
	)

	return block(
		"div",
		children=[
			thead(["Application", "Stage", "Amount sought"]),
			repeater("applications", row),
		],
	)


def schedule_body():
	row = block(
		"div",
		classes=["bp-li"],
		children=[
			bound("span", "date", classes=["bp-li-date"]),
			block(
				"div",
				classes=["bp-li-body"],
				children=[bound("div", "product", classes=["bp-p"]), bound("div", "detail", classes=["bp-s"])],
			),
			bound("span", "amount", classes=["bp-li-amt"]),
		],
	)
	return repeater("schedule", row)


def activity_body():
	row = block(
		"div",
		classes=["bp-li"],
		children=[
			bound("span", "date", classes=["bp-li-date"]),
			block(
				"div",
				classes=["bp-li-body"],
				children=[bound("div", "title", classes=["bp-p"]), bound("div", "sub", classes=["bp-s"])],
			),
			bound("span", "amount", classes=["bp-li-amt"]),
		],
	)
	return repeater("activity", row)


def footer():
	links = [
		block("a", html="Fair practice code", attributes={"href": "#"}),
		block("a", html="Grievance redressal", attributes={"href": "#"}),
		block("a", html="Interest rate policy", attributes={"href": "#"}),
	]
	return block(
		"footer",
		classes=["bp-footer"],
		children=[block("span", html="Meridian Finance Limited"), block("span", children=links)],
	)


def build_blocks():
	main = block(
		"div",
		classes=["bp-main"],
		children=[
			page_head(),
			block(
				"main",
				classes=["bp-content"],
				children=[
					number_cards(),
					block(
						"div",
						classes=["bp-grid"],
						children=[
							block(
								"div",
								classes=["bp-stack"],
								children=[
									card("Loan accounts", "accounts_note", accounts_body()),
									card("Applications", "applications_note", applications_body()),
								],
							),
							block(
								"div",
								classes=["bp-stack"],
								children=[
									card("Scheduled repayments", "schedule_note", schedule_body()),
									card("Recent activity", "activity_note", activity_body()),
								],
							),
						],
					),
				],
			),
			footer(),
		],
	)

	body = block("div", classes=["bp-body"], originalElement="body")
	body.attach_children(block("div", classes=["bp-shell"], children=[rail(), sidebar(), main]))

	return body.as_json(wrap_in_array=True)


def upsert_tokens():
	"""Create the brand tokens under readable, stable document names.

	Builder Token.autoname only falls back to a UUID when no name is set, and the
	emitted CSS custom property is --<document name>. Naming them after the token
	gives every site the same --brand-* properties, so the stylesheet below is
	portable; left to autoname, each site would emit a different UUID.
	"""
	for token in BRAND_TOKENS:
		name = token["token_name"]

		if frappe.db.exists("Builder Token", name):
			doc = frappe.get_doc("Builder Token", name)
			doc.update(token)
			doc.save()
			continue

		# drop any earlier UUID-named copy of the same token
		for stale in frappe.get_all("Builder Token", filters={"token_name": name}, pluck="name"):
			frappe.delete_doc("Builder Token", stale, force=True, ignore_permissions=True)

		doc = frappe.new_doc("Builder Token")
		doc.update(token)
		doc.insert()

		# frappe.model.naming.set_new_name clears an explicitly assigned name unless the
		# doctype autonames by prompt or uuid, so the rename has to follow the insert.
		if doc.name != name:
			frappe.rename_doc("Builder Token", doc.name, name, force=True, show_alert=False)


def build():
	"""Create or replace the standard Account overview page."""
	upsert_tokens()
	clear_builder_token_cache()

	fields = {
		"page_name": PAGE_NAME,
		"page_title": "Account overview",
		"route": ROUTE,
		"published": 1,
		"authenticated_access": 1,
		"disable_indexing": 1,
		"is_standard": 1,
		"app": "lending",
		"head_html": STYLESHEET,
		"page_data_script": DATA_SCRIPT,
		"blocks": build_blocks(),
	}

	existing = frappe.db.get_value("Builder Page", {"route": ROUTE}, "name")
	if existing:
		page = frappe.get_doc("Builder Page", existing)
		page.update(fields)
		page.save()
		action = "updated"
	else:
		page = frappe.get_doc(dict(doctype="Builder Page", **fields)).insert()
		action = "created"

	frappe.db.commit()
	print(f"{action} Builder Page {page.name} at /{ROUTE}")

	return page.name
