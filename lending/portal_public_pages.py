# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the two public portal pages: /apply and /track.

Run once with:
	bench --site <site> execute lending.portal_public_pages.build

Then stop running it. Both pages become UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas.

Neither page wears the borrower shell. Every row in that sidebar needs a login, so a
guest clicking one would be bounced; these carry their own top bar instead.

/apply asks one question per screen: who is borrowing, what for, the mobile number,
the rest of the details, and then it shows the offer and opens the account. A form
that asks everything at once reads as work to be done, and the two questions that
decide what the rest of the form even asks -- a person or a company, and which
product -- were buried in two selects halfway down it.

The seven panels are all rendered up front and the script shows one at a time, because
a Builder page has no router and no template engine. Anything the visitor has not
reached yet is `hidden`, never absent, so moving between screens costs no request. The
answers given on the tile screens land in hidden inputs on the details panel, so the
form that posts still posts one flat set of fields and the endpoints are unchanged.

Both pages post to whitelisted guest endpoints through the shared client script in
portal_script, which every portal page that takes input uses.
"""

from lending.portal_shell import build_page
from lending.portal_theme import (
	CHEVRON_LEFT,
	CHEVRON_RIGHT,
	ERROR_STYLES,
	FIELD_GRID_STYLES,
	FIELD_GRID_TABLET_STYLES,
	FIELD_WIDE_STYLES,
	HERO_INTRO_STYLES,
	HERO_TITLE_MOBILE_STYLES,
	HERO_TITLE_STYLES,
	HIDDEN,
	ICON_COMPANY,
	ICON_PERSON,
	LINK_BTN_STYLES,
	OPENING_STYLES,
	PANEL_BODY_STYLES,
	PANEL_HEAD_STYLES,
	PANEL_STEP_STYLES,
	PANEL_STYLES,
	PANEL_SUB_STYLES,
	PANEL_TITLE_STYLES,
	PICKED_ROW_STYLES,
	PICKED_STYLES,
	QUESTION_SUB_STYLES,
	QUESTION_TITLE_MOBILE_STYLES,
	QUESTION_TITLE_STYLES,
	QUIET_NOTE_STYLES,
	START_CARD_MOBILE_STYLES,
	START_CARD_STYLES,
	START_COPY_STYLES,
	START_NOTE_STYLES,
	START_TITLE_STYLES,
	SUBMIT_ROW_STYLES,
	WIZARD_BTN_STYLES,
	WIZARD_GHOST_STYLES,
	WIZARD_STYLES,
	benefits,
	block,
	bound,
	choice_field,
	choice_tile,
	code_boxes,
	echo_field,
	field,
	form_section,
	hidden_input,
	nav_row,
	offer_card,
	product_tiles,
	progress_bar,
	public_frame,
	tile_group,
	timeline_shell,
	trust_row,
	wizard_button,
)

# Loan Lead.employment_type accepts these two and nothing else.
EMPLOYMENT_TYPES = ("Salaried", "Self-employed")

# Loan Lead.applicant_type, and what the form opens on. A person borrows in their own
# name, a company in the company's, and the two are not asked the same questions.
DEFAULT_APPLICANT_TYPE = "Individual"

APPLY_ROUTE = "apply"
TRACK_ROUTE = "track"

# Panel 1 is the invitation, so it is not one of the steps the progress bar counts.
# Each panel names itself for that bar; the script reads the name off the panel.
START_PANEL = 1
APPLY_STEPS = (
	"Who is borrowing",
	"What you need",
	"Your mobile number",
	"Your details",
	"Your offer",
	"Your account",
)

APPLY_DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: the product list and its copy arrive formatted from the data layer.
data.update(frappe.call("lending.portal_apply.get_apply_page"))  # noqa: F821
'''

TRACK_DATA_SCRIPT = '''
# safe_exec blocks _(), so even this page's static wording comes from the data layer.
data.update(frappe.call("lending.portal_apply.get_track_page"))  # noqa: F821
'''


def wide(node):
	"""Let one field span both columns of the details grid."""
	node["baseStyles"].update(FIELD_WIDE_STYLES)

	return node


def only_for(node, audience):
	"""Mark a field as belonging to a person or to a company, not to both.

	The client script hides the half that does not apply and disables what it hides,
	because a required box nobody can see is a form that will not submit and will not
	say why. The server drops whichever does not apply too.
	"""
	node["attributes"]["data-only-for"] = audience

	return node


def panel(index, title, body, note=None, note_key=None, nav=None):
	"""One screen of the wizard: its question, what it asks for, and the way on."""
	head = [
		block(
			"h2",
			styles=QUESTION_TITLE_STYLES,
			mobileStyles=QUESTION_TITLE_MOBILE_STYLES,
			html=title,
		)
	]
	head.append(
		bound("p", note_key, styles=QUESTION_SUB_STYLES)
		if note_key
		else block("p", styles=QUESTION_SUB_STYLES, html=note)
	)

	attributes = {"data-panel": str(index), "data-name": APPLY_STEPS[index - 2]}
	if index > START_PANEL:
		attributes["hidden"] = "hidden"

	return block(
		"section",
		styles=PANEL_STYLES,
		attributes=attributes,
		children=[block("div", styles=PANEL_HEAD_STYLES, children=head), *body, *([nav] if nav else [])],
	)


def error_box():
	return block(
		"div",
		styles={**ERROR_STYLES, "margin": "14px 28px 0"},
		attributes={"data-error": "1", "hidden": "hidden"},
	)


def back_button(target):
	return wizard_button(
		"Back", WIZARD_GHOST_STYLES, chevron=CHEVRON_LEFT, leading=True, attributes={"data-back": str(target)}
	)


def next_button(target, label="Continue", gated=False):
	"""The way on to the next screen. A gated one waits until the question is answered."""
	attributes = {"data-next": str(target)}
	if gated:
		attributes["data-gate"] = "1"
		attributes["disabled"] = "disabled"

	return wizard_button(label, WIZARD_BTN_STYLES, chevron=CHEVRON_RIGHT, attributes=attributes)


def action_button(label, action, styles=None, chevron=CHEVRON_RIGHT, attributes=None):
	"""A button that has to ask the server before anything moves."""
	return wizard_button(
		label,
		styles or WIZARD_BTN_STYLES,
		chevron=chevron,
		attributes={"data-action": action, **(attributes or {})},
	)


def opening_panel():
	"""Screen 1. It asks for nothing: the promise, the three reassurances, one button."""
	card = block(
		"div",
		styles=START_CARD_STYLES,
		mobileStyles=START_CARD_MOBILE_STYLES,
		children=[
			block(
				"div",
				styles=START_COPY_STYLES,
				children=[
					bound("h2", "start_title", styles=START_TITLE_STYLES),
					bound("p", "start_note", styles=START_NOTE_STYLES),
				],
			),
			next_button(2, label="Apply now"),
		],
	)

	return block(
		"section",
		styles=OPENING_STYLES,
		attributes={"data-panel": str(START_PANEL), "data-name": "Start"},
		children=[
			block(
				"h1",
				styles=HERO_TITLE_STYLES,
				mobileStyles=HERO_TITLE_MOBILE_STYLES,
				children=[bound("span", "heading")],
			),
			bound("p", "intro", styles=HERO_INTRO_STYLES),
			trust_row("trust_points"),
			card,
			benefits("benefits"),
		],
	)


def type_panel():
	"""Screen 2. It decides what screen 5 asks for, which is why it comes first."""
	tiles = tile_group(
		"applicant_type",
		"Applicant type",
		[
			choice_tile("Individual", ICON_PERSON, "Person", "I am borrowing in my own name"),
			choice_tile("Business", ICON_COMPANY, "Company", "The business borrows, not me"),
		],
	)

	return panel(
		2,
		"Are you applying as a person or a company?",
		[tiles],
		note_key="type_note",
		nav=nav_row(back_button(1), [next_button(3)]),
	)


def product_panel():
	"""Screen 3. Every Loan Product that is not disabled, with its rate on it."""
	return panel(
		3,
		"What are you looking for?",
		[product_tiles("products", "loan_product")],
		note_key="product_note",
		# Nothing is chosen for the visitor, so the way on waits until they choose.
		nav=nav_row(back_button(2), [next_button(4, gated=True)]),
	)


def verify_panel():
	"""Screen 4. Nothing is written to the database here -- the code is checked against
	the number alone, and the Loan Lead only appears at screen 5."""
	code_section = block(
		"div",
		styles={"display": "block"},
		attributes={"data-code-section": "1", "hidden": "hidden"},
		children=[
			block(
				"div",
				styles={**QUIET_NOTE_STYLES, "padding": "6px 28px 0"},
				attributes={"data-sent-note": "1"},
			),
			bound("div", "code_note", styles={**QUIET_NOTE_STYLES, "padding": "8px 28px 0"}),
			code_boxes(),
			block(
				"div",
				styles={"padding": "6px 28px 0"},
				children=[action_button("Send it again", "resend", styles=LINK_BTN_STYLES, chevron=None)],
			),
		],
	)

	return panel(
		4,
		"What is your mobile number?",
		[
			block(
				"div",
				styles=PANEL_BODY_STYLES,
				children=[field("Mobile number", "mobile_number", input_type="tel", placeholder="98765 43210")],
			),
			code_section,
			error_box(),
		],
		note_key="verify_note",
		# One button, in the same place, whichever half of this screen is showing.
		nav=nav_row(
			back_button(3),
			[
				action_button("Send me a code", "send-code", attributes={"data-when": "before-code"}),
				action_button(
					"Confirm my number",
					"confirm-code",
					attributes={"data-when": "after-code", "hidden": "hidden"},
				),
			],
		),
	)


def details_panel():
	"""Screen 5. Every field here already exists on Loan Lead, so a fuller picture for
	the decision engine costs no schema change -- see PORTAL_PLAN.md section 9 for the
	fields that would need one.

	The two questions the earlier screens asked arrive as hidden inputs, so this is
	still one flat form and submit_lead still reads the same field names.
	"""
	answered = block(
		"div",
		styles=HIDDEN,
		children=[
			hidden_input("applicant_type", DEFAULT_APPLICANT_TYPE),
			hidden_input("loan_product"),
		],
	)
	picked = block(
		"div",
		styles=PICKED_ROW_STYLES,
		attributes={"data-picked": "1"},
		children=[
			block("span", styles=PICKED_STYLES, attributes={"data-picked-type": "1", "hidden": "hidden"}),
			block("span", styles=PICKED_STYLES, attributes={"data-picked-product": "1", "hidden": "hidden"}),
		],
	)
	grid = block(
		"div",
		styles=FIELD_GRID_STYLES,
		tabletStyles=FIELD_GRID_TABLET_STYLES,
		children=[
			form_section("About you"),
			only_for(wide(field("Company name", "company_name", required=False)), "Business"),
			field("Your full name", "applicant_name"),
			only_for(field("Date of birth", "date_of_birth", input_type="date", required=False), "Individual"),
			field("PAN", "pan", required=False, placeholder="ABCDE1234F"),
			field("Country", "applicant_country", required=False, placeholder="India"),
			form_section("How we reach you"),
			field("Email", "email", input_type="email"),
			echo_field("Mobile number", "Verified", "data-verified-echo"),
			form_section("What you need"),
			field("Amount needed", "loan_amount", input_type="number"),
			field("Over how many months", "proposed_tenure", input_type="number", required=False),
			field("Monthly income", "income", input_type="number", required=False),
			only_for(choice_field("Work", "employment_type", EMPLOYMENT_TYPES), "Individual"),
		],
	)

	return panel(
		5,
		"Applicant information",
		[answered, picked, grid, error_box()],
		note_key="details_note",
		nav=nav_row(back_button(4), [action_button("See my offer", "submit")]),
	)


def offer_panel():
	return panel(
		6,
		"Your indicative offer",
		[block("div", styles={"padding": "18px 28px 4px"}, children=[offer_card()])],
		note="What our rules say about the details you gave us.",
		nav=nav_row(forward=[action_button("Open my account", "to-account")]),
	)


def account_panel():
	"""Screen 7. The account is opened here rather than at /login, because by now the
	number is verified and every other detail is already on the lead."""
	return panel(
		7,
		"Keep track of this",
		[
			block(
				"div",
				styles=PANEL_BODY_STYLES,
				children=[
					block(
						"div",
						styles={**QUIET_NOTE_STYLES, "padding": "0 12px 6px"},
						attributes={"data-account-user": "1"},
					),
					field("Choose a password", "password", input_type="password"),
				],
			),
			error_box(),
		],
		note_key="account_note",
		nav=nav_row(forward=[action_button("Create my account", "create-account")]),
	)


def apply_content():
	return [
		public_frame(
			[
				progress_bar(len(APPLY_STEPS)),
				block(
					"div",
					styles=WIZARD_STYLES,
					attributes={"data-wizard": "1"},
					children=[
						opening_panel(),
						type_panel(),
						product_panel(),
						verify_panel(),
						details_panel(),
						offer_panel(),
						account_panel(),
					],
				),
			],
			links=[("Track an application", "/track"), ("Log in", "/login")],
		)
	]


def track_content():
	form = block(
		"form",
		styles=PANEL_STYLES,
		attributes={"data-endpoint": "lending.portal_apply.track_application"},
		children=[
			block(
				"div",
				styles=PANEL_HEAD_STYLES,
				children=[
					block("div", styles=PANEL_STEP_STYLES, html="Your application"),
					block("h2", styles=PANEL_TITLE_STYLES, html="Find your application"),
					bound("p", "track_note", styles=PANEL_SUB_STYLES),
				],
			),
			block(
				"div",
				styles=FIELD_GRID_STYLES,
				tabletStyles=FIELD_GRID_TABLET_STYLES,
				children=[
					field("Reference number", "reference", placeholder="LEAD-0001"),
					field("Mobile number", "mobile_number", input_type="tel", placeholder="98765 43210"),
				],
			),
			block(
				"div",
				styles={**SUBMIT_ROW_STYLES, "padding": "18px 20px", "marginTop": "14px"},
				children=[
					wizard_button(
						"Show me where it is",
						WIZARD_BTN_STYLES,
						chevron=CHEVRON_RIGHT,
						attributes={"data-submit": "1"},
					)
				],
			),
			block(
				"div",
				styles={**ERROR_STYLES, "margin": "0 20px 16px"},
				attributes={"data-error": "1", "hidden": "hidden"},
			),
			block(
				"div",
				styles={"padding": "0 20px 12px"},
				children=[offer_card(action_href="/apply")],
			),
			timeline_shell(),
		],
	)

	return [
		public_frame(
			[form],
			heading_key="heading",
			intro_key="intro",
			links=[("Apply for a loan", "/apply"), ("Log in", "/login")],
		)
	]


def build():
	apply_page = build_page(
		"Portal Apply",
		APPLY_ROUTE,
		"Apply for a loan",
		None,
		apply_content(),
		data_script=APPLY_DATA_SCRIPT,
		authenticated=False,
	)
	track_page = build_page(
		"Portal Track",
		TRACK_ROUTE,
		"Track your application",
		None,
		track_content(),
		data_script=TRACK_DATA_SCRIPT,
		authenticated=False,
	)

	return apply_page, track_page
