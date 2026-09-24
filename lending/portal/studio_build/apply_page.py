# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The public application form at /apply, as a Studio page.

It replaces the /apply page of the Builder portal this one was migrated from, and posts
to the same guest endpoints: send_mobile_code, confirm_mobile_code, submit_lead and create_account, none
of them changed.

The page asks one question per screen: who is borrowing, what for, the mobile number,
the rest of the details, and then it shows the offer and opens the account. The Builder
page rendered all seven panels up front and a client script showed one at a time,
because a Builder page has no state of its own. Here `step` is a ref and each panel says
which step it is, which is the same thing said in one line rather than two hundred.

The two questions the early screens ask still decide what screen 5 asks for, and the
answers still arrive at submit_lead as one flat set of fields under Loan Lead's own
names -- so the endpoint reads exactly what it always read.
"""

from lending.portal.studio_build.app import api_resource, page_script, upsert_page
from lending.portal.studio_build.blocks import (
	PANEL,
	alert,
	badge,
	block,
	button,
	click,
	column,
	container,
	divider,
	heading,
	icon,
	icon_tile,
	muted,
	pair_rows,
	reader,
	repeater,
	row,
	slot,
	spacer,
	text,
)
from lending.portal.studio_build.public import page

APPLY_SOURCE = "apply"

# Panel 1 is the invitation, so it is not one of the steps the progress bar counts.
STEPS = (
	"Who is borrowing",
	"What you need",
	"Your mobile number",
	"Your details",
	"Your offer",
	"Your account",
)

# Loan Lead.applicant_type. A person borrows in their own name, a company in the
# company's, and the two are not asked the same questions.
APPLICANT_TYPES = (
	("Individual", "Person", "I am borrowing in my own name", "user"),
	("Business", "Company", "The business borrows, not me", "building-2"),
)

# Loan Lead.employment_type accepts these two and nothing else.
EMPLOYMENT_TYPES = ("Salaried", "Self-employed")

# Every box on the details screen, who it is asked of, and whether submit_lead refuses
# without it. An empty "who" means both. The names are Loan Lead's own, because
# submit_lead reads them off the request.
DETAIL_FIELDS = (
	("Company name", "companyName", "company_name", "text", "Business", True),
	("Your full name", "applicantName", "applicant_name", "text", "", True),
	("Date of birth", "dateOfBirth", "date_of_birth", "date", "Individual", False),
	("PAN", "pan", "pan", "text", "", False),
	("Country", "applicantCountry", "applicant_country", "text", "", False),
	("Email", "email", "email", "email", "", True),
	("Amount needed", "loanAmount", "loan_amount", "number", "", True),
	("Over how many months", "proposedTenure", "proposed_tenure", "number", "", False),
	("Monthly income", "income", "income", "number", "", False),
)


read_apply = reader(APPLY_SOURCE)

# The opening screen is a landing page and takes the width of one; the questions after it
# are a form, and keep a form's measure.
PAGE_WIDTH = "1080px"
FORM = {"width": "100%", "maxWidth": "720px", "margin": "0 auto"}

APPLY_SCRIPT = '''\tconst busy = ref(false)
\tconst codeSent = ref(false)
\tconst token = ref("")
\tconst accountToken = ref("")
\tconst offer = ref<Record<string, any>>({})

\tconst fail = (error: any) =>
\t\ttoast.error(String(error?.messages?.[0] || error?.message || error))

\t// A confirmed number is not asked for twice: the mobile screen is stepped over in
\t// whichever direction the visitor is going.
\tconst go = (to: number) => {
\t\tif (to === 4 && token.value) to = step.value > 4 ? 3 : 5
\t\tstep.value = to
\t}

\t// Each type is offered its own products, so a product picked for the other one goes.
\tconst choose = (type: string) => {
\t\tif (type !== applicantType.value) loanProduct.value = ""
\t\tapplicantType.value = type
\t}

\tconst chooseProduct = (product: string) => { loanProduct.value = product }

\tconst resendIn = ref(0)
\tconst countDown = () => {
\t\tresendIn.value = 30
\t\tconst timer = setInterval(() => {
\t\t\tif (--resendIn.value <= 0) clearInterval(timer)
\t\t}, 1000)
\t}

\tconst sendCode = () => {
\t\tbusy.value = true
\t\tcall("lending.portal.apply.send_mobile_code", { mobile_number: mobileNumber.value })
\t\t\t.then((result: any) => {
\t\t\t\tcodeSent.value = true
\t\t\t\tcountDown()
\t\t\t\ttoast.success(result.message)
\t\t\t})
\t\t\t.catch(fail)
\t\t\t.finally(() => { busy.value = false })
\t}

\t// The link stays in place through the countdown, and does nothing until it ends.
\tconst resendCode = () => {
\t\tif (resendIn.value > 0 || busy.value) return
\t\tsendCode()
\t}

\tconst confirmCode = () => {
\t\tbusy.value = true
\t\tcall("lending.portal.apply.confirm_mobile_code", {
\t\t\tmobile_number: mobileNumber.value,
\t\t\totp: otp.value,
\t\t})
\t\t\t.then((result: any) => {
\t\t\t\tif (!result.verified) { toast.error(result.message); return }
\t\t\t\ttoken.value = result.token
\t\t\t\tstep.value = 5
\t\t\t})
\t\t\t.catch(fail)
\t\t\t.finally(() => { busy.value = false })
\t}

\tconst submit = () => {
\t\tbusy.value = true
\t\tcall("lending.portal.apply.submit_lead", {
\t\t\ttoken: token.value,
\t\t\tapplicant_type: applicantType.value,
\t\t\tloan_product: loanProduct.value,
%(fields)s
\t\t\temployment_type: employmentType.value,
\t\t})
\t\t\t.then((result: any) => {
\t\t\t\toffer.value = result
\t\t\t\taccountToken.value = result.account_token
\t\t\t\tstep.value = 6
\t\t\t})
\t\t\t.catch((error: any) => {
\t\t\t\tfail(error)
\t\t\t\t// The proof of the number is gone: verify again, keeping every answer given.
\t\t\t\tif (error?.exc_type !== "VerificationExpiredError") return
\t\t\t\ttoken.value = ""
\t\t\t\tcodeSent.value = false
\t\t\t\totp.value = ""
\t\t\t\tstep.value = 4
\t\t\t})
\t\t\t.finally(() => { busy.value = false })
\t}

\tconst createAccount = () => {
\t\tbusy.value = true
\t\tcall("lending.portal.apply.create_account", {
\t\t\ttoken: accountToken.value,
\t\t\tpassword: password.value,
\t\t\tconfirm_password: confirmPassword.value,
\t\t})
\t\t\t.then(() => { window.location.href = "/borrower-portal/overview" })
\t\t\t.catch(fail)
\t\t\t.finally(() => { busy.value = false })
\t}''' % {
	"fields": "\n".join(
		f"\t\t\t{field}: {ref_name}.value," for _label, ref_name, field, *_rest in DETAIL_FIELDS
	)
}

APPLY_STATE = [
	("step", "1"),
	("applicantType", '"Individual"'),
	("loanProduct", '""'),
	("mobileNumber", '""'),
	("otp", '""'),
	("employmentType", '"Salaried"'),
	("password", '""'),
	("confirmPassword", '""'),
] + [(ref_name, '""') for _label, ref_name, *_rest in DETAIL_FIELDS]

APPLY_RETURNS = [
	"busy",
	"codeSent",
	"offer",
	"go",
	"choose",
	"chooseProduct",
	"sendCode",
	"resendIn",
	"resendCode",
	"confirmCode",
	"submit",
	"createAccount",
]


def action(label, script, **kwargs):
	"""The button that calls the server. It spins while the call is out, so a second
	click cannot send a second code or raise a second lead."""
	return button(label, script=script, variant="solid", props={"loading": "{{ busy }}"}, **kwargs)


def panel(index, title, note, body, back=None, forward=()):
	"""One screen of the wizard: its question, what it asks for, and the way on."""
	head = column([text(title, tag="h2", size="text-2xl", styles={"fontWeight": "600"}), muted(note)], gap="4px")
	buttons = [*([button("Back", script=f"go({back})")] if back else []), spacer(), *forward]
	nav = row([sized(part) for part in buttons], gap="8px")

	return column(
		[head, *body, nav],
		gap="16px",
		styles=dict(PANEL, **FORM),
		visible="{{ step === %d }}" % index,
	)


def sized(part):
	"""A wizard button at `md`: the way on is the one thing to press on each screen,
	and `sm` is the desk's size for a toolbar."""
	if part["componentName"] != "Button":
		return part

	return dict(part, componentProps=dict(part["componentProps"], size="md"))


def progress():
	"""How far through the six questions, and which one is being asked."""
	where = "{{ 'Step ' + (step - 1) + ' of %d · ' + (%s[step - 2] || '') }}" % (len(STEPS), list(STEPS))

	return column(
		[
			block("Progress", props={"value": "{{ (step - 1) / %d * 100 }}" % len(STEPS), "size": "sm"}),
			text(where, size="text-sm", styles={"color": "var(--ink-gray-7)"}),
		],
		gap="6px",
		styles=FORM,
		visible="{{ step > 1 }}",
	)


RADIO = {
	"width": "20px",
	"height": "20px",
	"flexShrink": "0",
	"borderRadius": "9999px",
	"justifyContent": "center",
}


def radio(chosen):
	"""The mark a choice leaves: an empty ring, or a filled disc with a tick in it."""
	return [
		container(
			[],
			styles=dict(RADIO, border="1.5px solid var(--outline-gray-3)"),
			visible="{{ !(%s) }}" % chosen,
		),
		row(
			[icon("check", size=12, stroke=3)],
			styles=dict(RADIO, backgroundColor="var(--ink-gray-9)", color="var(--surface-base)"),
			visible="{{ %s }}" % chosen,
		),
	]


def choice(content, script, chosen, **kwargs):
	"""A tile is this form's radio button, at the size the question deserves.

	A block's styles cannot follow state, so the chosen look is a layer that appears
	behind the content: a ring and a tint, drawn outside the border so nothing moves.
	Hover and press are classes, because an inline style has neither -- and the `!`
	because PANEL's border is inline, which a plain class can never outrank.
	"""
	selected = container(
		[],
		styles={
			"position": "absolute",
			"inset": "-1px",
			"borderRadius": "calc(var(--radius-4) + 1px)",
			"border": "2px solid var(--ink-gray-9)",
			"backgroundColor": "var(--surface-gray-1)",
			"pointerEvents": "none",
		},
		visible="{{ %s }}" % chosen,
	)
	body = row(
		[*content, spacer(), *radio(chosen)],
		gap="12px",
		align="start",
		styles={"position": "relative", "width": "100%"},
	)

	return container(
		[selected, body],
		styles=dict(PANEL, position="relative", cursor="pointer", userSelect="none", flex="1"),
		events=click(script),
		classes=[
			"transition",
			"duration-150",
			"hover:!border-outline-gray-4",
			"hover:shadow-sm",
			"active:scale-[0.98]",
		],
		**kwargs,
	)


def tile(label, note, glyph_name, script, chosen):
	"""One answer to who is borrowing."""
	return choice(
		[
			icon_tile(glyph_name, tile=40, glyph=20),
			column(
				[text(label, size="text-base", styles={"fontWeight": "600"}), muted(note)],
				gap="2px",
			),
		],
		script,
		chosen,
	)


def glyph(names, expression, **kwargs):
	"""The glyph a payload row names, out of the few it may name.

	An icon is SVG written at build time and the row picks it at render time, so this is
	one block per name, each shown when the row says it.
	Returns a list, to be spread into the row that carries it.
	"""
	return [
		icon_tile(name, visible="{{ %s === '%s' }}" % (expression, name), **kwargs) for name in names
	]


def fit(low, share, high):
	"""A length that follows the window's height between two bounds.

	The opening screen is meant to be taken in without scrolling, so its gaps and its
	headline give way on a short laptop screen and keep the mockup's measure on a tall one.
	"""
	return f"clamp({low}px, {share}vh, {high}px)"


def hero():
	"""The promise: what this is, how long it takes, and that it costs nothing to look."""
	tagline = badge(read_apply("tagline"), size="lg", styles={"alignSelf": "flex-start"})
	title = text(
		read_apply("heading"),
		tag="h1",
		size="text-5xl",
		# Studio's type scale stops short of a landing page's headline, so the size is a style.
		styles={
			"fontSize": fit(32, 5.6, 48),
			"fontWeight": "700",
			"lineHeight": "1.08",
			"letterSpacing": "-0.02em",
			"whiteSpace": "pre-line",
			"color": "var(--ink-gray-9)",
		},
		mobile={"fontSize": "2.25rem"},
	)
	intro = text(
		read_apply("intro"),
		size="text-lg",
		styles={"maxWidth": "640px", "lineHeight": "1.5", "color": "var(--ink-gray-6)"},
	)
	point = row(
		[
			*glyph(("chart-no-axes", "shield", "receipt-text"), "dataItem.icon", tile=44, glyph=20),
			column(
				[
					text("{{ dataItem.title }}", size="text-base", styles={"color": "var(--ink-gray-8)"}),
					text("{{ dataItem.note }}", size="text-base", styles={"color": "var(--ink-gray-7)"}),
				],
				gap="0px",
			),
		],
		gap="16px",
	)
	trust = repeater(
		read_apply("trust_points"),
		point,
		data_key="title",
		styles={"display": "flex", "flexDirection": "row", "columnGap": "36px", "rowGap": "16px", "flexWrap": "wrap"},
	)

	return column(
		[tagline, column([title, intro], gap=fit(10, 2, 20)), trust],
		gap=fit(14, 2.6, 26),
	)


def start_card():
	"""The one thing to press, on a panel of its own so nothing else competes with it."""
	# The label goes in the default slot as well as the prop: once a block has any slot,
	# Studio hands Button an empty default one too, and Button renders that over `label`.
	apply = button(
		"Apply now",
		script="go(2)",
		variant="solid",
		props={"size": "lg"},
		slots={
			**slot("suffix", [icon("arrow-right", size=16)]),
			**slot("default", [text("Apply now", tag="span", size="text-lg", styles={"fontWeight": "500"})]),
		},
		mobile={"width": "100%"},
	)

	return row(
		[
			icon_tile("file-text", tile=48, glyph=22),
			column(
				[
					heading(read_apply("start_title"), size="text-xl"),
					text(read_apply("start_note"), size="text-base", styles={"color": "var(--ink-gray-6)"}),
				],
				gap="4px",
				styles={"flex": "1 1 240px"},
			),
			apply,
		],
		gap="20px",
		styles=dict(PANEL, padding=f"{fit(16, 2.4, 24)} 24px", borderRadius="var(--radius-6)", flexWrap="wrap"),
		mobile={"padding": "20px"},
	)


def how_it_works():
	"""What happens after the button, in the three steps a visitor will see."""
	step = row(
		[
			*glyph(("file-text", "search", "percent"), "dataItem.icon", tile=44, glyph=20),
			column(
				[
					text("{{ dataItem.title }}", size="text-base", styles={"fontWeight": "600"}),
					text("{{ dataItem.note }}", size="text-sm", styles={"color": "var(--ink-gray-6)", "lineHeight": "1.5"}),
				],
				gap="6px",
				styles={"flex": "1", "minWidth": "0px"},
			),
		],
		gap="16px",
		align="start",
		styles=dict(PANEL, padding=f"{fit(14, 2.2, 22)} 16px", borderRadius="var(--radius-6)", flex="1 1 240px"),
	)

	return column(
		[
			column(
				[
					heading(read_apply("how_title"), size="text-xl", styles={"fontWeight": "700"}),
					text(read_apply("how_note"), size="text-base", styles={"color": "var(--ink-gray-6)"}),
				],
				gap="2px",
			),
			repeater(
				read_apply("benefits"),
				step,
				data_key="icon",
				styles={"display": "flex", "flexDirection": "row", "gap": "16px", "flexWrap": "wrap"},
			),
		],
		gap=fit(12, 1.8, 20),
	)


def opening():
	"""Screen 1. It asks for nothing: the promise, the three reassurances, one button."""
	return column(
		[hero(), start_card(), divider(), how_it_works()],
		gap=fit(14, 2.6, 28),
		# Centred in the height the frame leaves, so a tall window has no empty band below.
		styles={"marginTop": "auto", "marginBottom": "auto"},
		visible="{{ step === 1 }}",
	)


def type_panel():
	"""Screen 2. It decides what screen 5 asks for, which is why it comes first."""
	tiles = row(
		[
			tile(label, note, glyph_name, f"choose('{value}')", "applicantType === '%s'" % value)
			for value, label, note, glyph_name in APPLICANT_TYPES
		],
		gap="12px",
		align="stretch",
		mobile={"flexDirection": "column"},
	)

	return panel(
		2,
		"Are you applying as a person or a company?",
		read_apply("type_note"),
		[tiles],
		back=1,
		forward=[button("Continue", script="go(3)", variant="solid")],
	)


def product_panel():
	"""Screen 3. Every Loan Product open to the portal and to the applicant type chosen
	on screen 2, with its rate on it."""
	product = choice(
		[
			column(
				[
					text("{{ dataItem.label }}", size="text-base", styles={"fontWeight": "600"}),
					# One expression: Studio renders only the first of several bindings in a string.
					muted("{{ dataItem.rate + ' ' + dataItem.rate_note + ' · ' + dataItem.kind }}"),
					muted("Up to {{ dataItem.ceiling }}"),
				],
				gap="2px",
			)
		],
		"chooseProduct(dataItem.value)",
		"loanProduct === dataItem.value",
	)
	products = repeater(
		read_apply("products[applicantType]"),
		product,
		data_key="value",
		empty="Nothing is open to this kind of applicant yet",
		styles={
			"display": "grid",
			"gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
			"gap": "12px",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
	)

	return panel(
		3,
		"What are you looking for?",
		read_apply("product_note"),
		[products],
		back=2,
		# Nothing is chosen for the visitor, so the way on waits until they choose.
		forward=[
			button("Continue", script="go(4)", variant="solid", visible="{{ loanProduct }}"),
			muted("Pick a product to carry on", visible="{{ !loanProduct }}"),
		],
	)


def resend_line():
	"""The hint under the OTP box: a link to send it again, and how long until it may."""
	link = text(
		"Resend OTP",
		styles={"color": "var(--ink-gray-9)", "fontWeight": "500", "cursor": "pointer"},
		events=click("resendCode()"),
	)

	return row(
		[
			row([muted("Didn't receive the OTP?"), link], gap="6px"),
			muted(
				"{{ 'Resend in 00:' + String(resendIn).padStart(2, '0') }}",
				styles={"color": "var(--ink-gray-5)"},
				visible="{{ resendIn > 0 }}",
			),
		],
		styles={"justifyContent": "space-between", "width": "100%"},
	)


def verify_panel():
	"""Screen 4. Nothing is written here -- the code is checked against the number alone."""
	number = block(
		"FormControl",
		props={
			"type": "tel",
			"label": "Mobile number",
			"placeholder": "98765 43210",
			"modelValue": {"$type": "variable", "name": "mobileNumber"},
		},
	)
	code = column(
		[
			muted(read_apply("code_note")),
			block(
				"FormControl",
				props={
					"type": "password",
					"label": "OTP",
					"modelValue": {"$type": "variable", "name": "otp"},
				},
			),
			resend_line(),
		],
		gap="8px",
		visible="{{ codeSent }}",
	)

	return panel(
		4,
		"What is your mobile number?",
		read_apply("verify_note"),
		[number, code],
		back=3,
		# One button, in the same place, whichever half of this screen is showing.
		forward=[
			action("Send OTP", "sendCode()", visible="{{ !codeSent }}"),
			action("Confirm my number", "confirmCode()", visible="{{ codeSent }}"),
		],
	)


def details_panel():
	"""Screen 5. Every field here already exists on Loan Lead, so a fuller picture for
	the decision engine costs no schema change."""
	boxes = [
		block(
			"FormControl",
			props={
				"type": kind,
				"label": label,
				"required": required,
				"modelValue": {"$type": "variable", "name": ref_name},
			},
			visible="{{ applicantType === '%s' }}" % who if who else None,
		)
		for label, ref_name, _field, kind, who, required in DETAIL_FIELDS
	]
	work = block(
		"FormControl",
		props={
			"type": "select",
			"label": "Work",
			"options": [{"label": kind, "value": kind} for kind in EMPLOYMENT_TYPES],
			"modelValue": {"$type": "variable", "name": "employmentType"},
		},
		visible="{{ applicantType === 'Individual' }}",
	)
	grid = container(
		[*boxes, work],
		styles={
			"display": "grid",
			"gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
			"gap": "12px",
			"width": "100%",
		},
		mobile={"gridTemplateColumns": "minmax(0, 1fr)"},
	)
	chosen = row(
		[
			block("Badge", props={"label": "{{ applicantType }}", "theme": "gray", "size": "sm"}),
			block("Badge", props={"label": "{{ loanProduct }}", "theme": "gray", "size": "sm"}),
		],
		gap="6px",
	)

	return panel(
		5,
		"Applicant information",
		read_apply("details_note"),
		[chosen, grid],
		back=4,
		forward=[action("See my offer", "submit()")],
	)


def offer_panel():
	"""Screen 6. What our rules said about the details that were given."""
	return panel(
		6,
		"Your indicative offer",
		"What our rules say about the details you gave us.",
		[
			text("{{ offer.headline }}", tag="h3", size="text-xl", styles={"fontWeight": "600"}),
			muted("{{ offer.message }}"),
			# A holding message has no figures, and an empty list would say "Nothing to show".
			pair_rows("{{ offer.offer }}", data_key="label", visible="{{ offer.offer?.length }}"),
			alert("{{ offer.reference_note }}", visible="{{ offer.reference_note }}"),
		],
		forward=[button("Open my account", script="go(7)", variant="solid")],
	)


def account_panel():
	"""Screen 7. The account is opened here rather than at /login, because by now the
	number is verified and every other detail is already on the lead."""
	return panel(
		7,
		"Keep track of this",
		read_apply("account_note"),
		[
			block(
				"FormControl",
				props={
					"type": "password",
					"label": "Choose a password",
					"modelValue": {"$type": "variable", "name": "password"},
				},
			),
			block(
				"FormControl",
				props={
					"type": "password",
					"label": "Confirm password",
					"modelValue": {"$type": "variable", "name": "confirmPassword"},
				},
			),
		],
		forward=[action("Create my account", "createAccount()")],
	)


def build_apply():
	body = [
		progress(),
		opening(),
		type_panel(),
		product_panel(),
		verify_panel(),
		details_panel(),
		offer_panel(),
		account_panel(),
	]

	return upsert_page(
		"Apply for a loan",
		"/apply",
		page(read_apply, [("Track an application", "/track"), ("Log in", "/login", "user")], body, width=PAGE_WIDTH),
		[api_resource(APPLY_SOURCE, "lending.portal.apply.get_apply_page")],
		script=page_script(state=APPLY_STATE, body=APPLY_SCRIPT, returns=APPLY_RETURNS, search=False),
		allow_guest=True,
	)


def build():
	return build_apply()
