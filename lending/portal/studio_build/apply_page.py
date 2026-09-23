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
	block,
	button,
	card,
	click,
	column,
	container,
	muted,
	pair_rows,
	reader,
	repeater,
	row,
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
	("Individual", "Person", "I am borrowing in my own name"),
	("Business", "Company", "The business borrows, not me"),
)

# Loan Lead.employment_type accepts these two and nothing else.
EMPLOYMENT_TYPES = ("Salaried", "Self-employed")

# Every box on the details screen, and who it is asked of. The last column empty means
# both. The names are Loan Lead's own, because submit_lead reads them off the request.
DETAIL_FIELDS = (
	("Company name", "companyName", "company_name", "text", "Business"),
	("Your full name", "applicantName", "applicant_name", "text", ""),
	("Date of birth", "dateOfBirth", "date_of_birth", "date", "Individual"),
	("PAN", "pan", "pan", "text", ""),
	("Country", "applicantCountry", "applicant_country", "text", ""),
	("Email", "email", "email", "email", ""),
	("Amount needed", "loanAmount", "loan_amount", "number", ""),
	("Over how many months", "proposedTenure", "proposed_tenure", "number", ""),
	("Monthly income", "income", "income", "number", ""),
)


read_apply = reader(APPLY_SOURCE)

APPLY_SCRIPT = '''\tconst busy = ref(false)
\tconst codeSent = ref(false)
\tconst token = ref("")
\tconst accountToken = ref("")
\tconst offer = ref<Record<string, any>>({})

\tconst fail = (error: any) =>
\t\ttoast.error(String(error?.messages?.[0] || error?.message || error))

\tconst go = (to: number) => { step.value = to }

\tconst choose = (type: string) => { applicantType.value = type }

\tconst chooseProduct = (product: string) => { loanProduct.value = product }

\tconst sendCode = () => {
\t\tbusy.value = true
\t\tcall("lending.portal.apply.send_mobile_code", { mobile_number: mobileNumber.value })
\t\t\t.then((result: any) => { codeSent.value = true; toast.success(result.message) })
\t\t\t.catch(fail)
\t\t\t.finally(() => { busy.value = false })
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
\t\t\t.catch(fail)
\t\t\t.finally(() => { busy.value = false })
\t}

\tconst createAccount = () => {
\t\tbusy.value = true
\t\tcall("lending.portal.apply.create_account", {
\t\t\ttoken: accountToken.value,
\t\t\tpassword: password.value,
\t\t})
\t\t\t.then(() => { window.location.href = "/borrower-portal/overview" })
\t\t\t.catch(fail)
\t\t\t.finally(() => { busy.value = false })
\t}''' % {
	"fields": "\n".join(
		f"\t\t\t{field}: {ref_name}.value," for _label, ref_name, field, _kind, _who in DETAIL_FIELDS
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
] + [(ref_name, '""') for _label, ref_name, _field, _kind, _who in DETAIL_FIELDS]

APPLY_RETURNS = [
	"busy",
	"codeSent",
	"offer",
	"go",
	"choose",
	"chooseProduct",
	"sendCode",
	"confirmCode",
	"submit",
	"createAccount",
]


def panel(index, title, note, body, back=None, forward=()):
	"""One screen of the wizard: its question, what it asks for, and the way on."""
	head = column([text(title, tag="h2", size="text-2xl", styles={"fontWeight": "600"}), muted(note)], gap="4px")
	nav = row(
		[
			*([button("Back", script=f"go({back})")] if back else []),
			spacer(),
			*forward,
		],
		gap="8px",
	)

	return column(
		[head, *body, nav],
		gap="16px",
		styles=PANEL,
		visible="{{ step === %d }}" % index,
	)


def progress():
	"""How far through the six questions, and which one is being asked."""
	return column(
		[
			block("Progress", props={"value": "{{ (step - 1) / %d * 100 }}" % len(STEPS), "size": "sm"}),
			muted("{{ %s[step - 2] || '' }}" % list(STEPS)),
		],
		gap="6px",
		visible="{{ step > 1 }}",
	)


def tile(label, note, script, chosen):
	"""A tile is this form's radio button, at the size the question deserves.

	The chosen one wears a badge, because a choice that leaves no mark is not a choice.
	The Builder page drew that state in a stylesheet keyed off a data attribute; here it
	is a Badge that says when it is the one.
	"""
	return column(
		[
			row(
				[
					text(label, size="text-base", styles={"fontWeight": "600"}),
					spacer(),
					block("Badge", props={"label": "Chosen", "theme": "green", "size": "sm"}, visible=chosen),
				],
				gap="6px",
			),
			muted(note),
		],
		gap="2px",
		styles=dict(PANEL, cursor="pointer", flex="1"),
		events=click(script),
	)


def opening():
	"""Screen 1. It asks for nothing: the promise, the three reassurances, one button."""
	trust = repeater(
		read_apply("trust_points"),
		muted("{{ dataItem.label }}"),
		data_key="label",
		styles={"display": "flex", "flexDirection": "row", "gap": "16px", "flexWrap": "wrap"},
	)
	benefit = column(
		[
			text("{{ dataItem.step }}. {{ dataItem.title }}", size="text-base", styles={"fontWeight": "600"}),
			muted("{{ dataItem.note }}"),
		],
		gap="2px",
		styles=dict(PANEL, flex="1"),
	)

	return column(
		[
			text(read_apply("heading"), tag="h1", size="text-6xl", styles={"fontWeight": "600"}),
			muted(read_apply("intro")),
			trust,
			card(
				read_apply("start_title"),
				read_apply("start_note"),
				button("Apply now", script="go(2)", variant="solid"),
			),
			repeater(
				read_apply("benefits"),
				benefit,
				data_key="step",
				styles={"display": "flex", "flexDirection": "row", "gap": "12px"},
				mobile={"flexDirection": "column"},
			),
		],
		gap="16px",
		visible="{{ step === 1 }}",
	)


def type_panel():
	"""Screen 2. It decides what screen 5 asks for, which is why it comes first."""
	tiles = row(
		[
			tile(label, note, f"choose('{value}')", "{{ applicantType === '%s' }}" % value)
			for value, label, note in APPLICANT_TYPES
		],
		gap="12px",
		align="stretch",
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
	"""Screen 3. Every Loan Product open to the portal, with its rate on it."""
	product = column(
		[
			row(
				[
					text("{{ dataItem.label }}", size="text-base", styles={"fontWeight": "600"}),
					spacer(),
					block(
						"Badge",
						props={"label": "Chosen", "theme": "green", "size": "sm"},
						visible="{{ loanProduct === dataItem.value }}",
					),
				],
				gap="6px",
			),
			muted("{{ dataItem.rate }} {{ dataItem.rate_note }} · {{ dataItem.kind }}"),
			muted("Up to {{ dataItem.ceiling }}"),
		],
		gap="2px",
		styles=dict(PANEL, cursor="pointer"),
		events=click("chooseProduct(dataItem.value)"),
	)

	return panel(
		3,
		"What are you looking for?",
		read_apply("product_note"),
		[repeater(read_apply("products"), product, data_key="value")],
		back=2,
		# Nothing is chosen for the visitor, so the way on waits until they choose.
		forward=[
			button("Continue", script="go(4)", variant="solid", visible="{{ loanProduct }}"),
			muted("Pick a product to carry on", visible="{{ !loanProduct }}"),
		],
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
					"type": "text",
					"label": "The six digits we sent you",
					"modelValue": {"$type": "variable", "name": "otp"},
				},
			),
			button("Send it again", script="sendCode()", variant="ghost"),
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
			button("Send me a code", script="sendCode()", variant="solid", visible="{{ !codeSent }}"),
			button("Confirm my number", script="confirmCode()", variant="solid", visible="{{ codeSent }}"),
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
				"modelValue": {"$type": "variable", "name": ref_name},
			},
			visible="{{ applicantType === '%s' }}" % who if who else None,
		)
		for label, ref_name, _field, kind, who in DETAIL_FIELDS
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
		forward=[button("See my offer", script="submit()", variant="solid")],
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
			pair_rows("{{ offer.offer }}", data_key="label"),
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
			)
		],
		forward=[button("Create my account", script="createAccount()", variant="solid")],
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
		page(read_apply, [("Track an application", "/track"), ("Log in", "/login")], body),
		[api_resource(APPLY_SOURCE, "lending.portal.apply.get_apply_page")],
		script=page_script(state=APPLY_STATE, body=APPLY_SCRIPT, returns=APPLY_RETURNS, search=False),
		allow_guest=True,
	)


def build():
	return build_apply()
