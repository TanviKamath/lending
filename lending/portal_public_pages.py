# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Builds the two public portal pages: /apply and /track.

Run once with:
	bench --site <site> execute lending.portal_public_pages.build

Then stop running it. Both pages become UI-owned: Builder exports every save to
lending/builder_files/, and re-running this discards whatever was laid out on the
canvas.

Neither page wears the borrower shell. Every row in that sidebar needs a login, so a
guest clicking one would be bounced; these carry their own heading instead.

Both post to a whitelisted guest endpoint through one client script, because Builder's
published pages ship no JavaScript of their own -- no frappe bundle, no CSRF token, so
the script uses plain fetch. Guest sessions carry no CSRF token, and frappe skips the
check when there is none to compare against, which is what makes that work.
"""

from lending.portal_shell import build_page
from lending.portal_theme import (
	BTN_STYLES,
	CARD_HEAD_STYLES,
	CARD_STYLES,
	CARD_SUB_STYLES,
	CARD_TITLE_STYLES,
	ERROR_STYLES,
	RESULT_STYLES,
	SUBMIT_ROW_STYLES,
	block,
	bound,
	field,
	pair_rows,
	public_frame,
	select_field,
)

APPLY_ROUTE = "apply"
TRACK_ROUTE = "track"

APPLY_SCRIPT_NAME = "lending-portal-apply"

APPLY_DATA_SCRIPT = '''
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: the product list and its copy arrive formatted from the data layer.
data.update(frappe.call("lending.portal_apply.get_apply_page"))  # noqa: F821
'''

TRACK_DATA_SCRIPT = '''
# safe_exec blocks _(), so even this page's static wording comes from the data layer.
data.update(frappe.call("lending.portal_apply.get_track_page"))  # noqa: F821
'''

# One script serves both pages. It finds the form by its endpoint attribute, so adding
# a third public form needs no new JavaScript.
CLIENT_SCRIPT = """
(function () {
	function ready(fn) {
		if (document.readyState !== "loading") fn();
		else document.addEventListener("DOMContentLoaded", fn);
	}

	function show(container, payload) {
		container.innerHTML = "";
		var heading = document.createElement("strong");
		heading.textContent = payload.headline || "";
		container.appendChild(heading);

		if (payload.message) {
			var message = document.createElement("div");
			message.textContent = payload.message;
			container.appendChild(message);
		}

		(payload.offer || []).forEach(function (row) {
			var line = document.createElement("div");
			line.textContent = row.label + ": " + row.value;
			container.appendChild(line);
		});

		if (payload.reference_note) {
			var note = document.createElement("div");
			note.textContent = payload.reference_note;
			container.appendChild(note);
		}
		container.hidden = false;
	}

	function fail(box, message) {
		box.textContent = message;
		box.hidden = false;
	}

	ready(function () {
		document.querySelectorAll("[data-endpoint]").forEach(function (form) {
			var button = form.querySelector("[data-submit]");
			var result = form.querySelector("[data-result]");
			var error = form.querySelector("[data-error]");
			if (!button) return;

			button.addEventListener("click", function (event) {
				event.preventDefault();
				error.hidden = true;
				result.hidden = true;

				var body = new URLSearchParams();
				var missing = false;
				form.querySelectorAll("input[name], select[name]").forEach(function (input) {
					if (input.required && !input.value) missing = true;
					body.append(input.name, input.value);
				});

				if (missing) {
					fail(error, "Please fill in every field.");
					return;
				}

				button.disabled = true;
				fetch("/api/method/" + form.dataset.endpoint, {
					method: "POST",
					headers: { "Content-Type": "application/x-www-form-urlencoded" },
					body: body.toString(),
				})
					.then(function (response) {
						return response.json().then(function (data) {
							return { ok: response.ok, data: data };
						});
					})
					.then(function (outcome) {
						if (outcome.ok && outcome.data.message) {
							show(result, outcome.data.message);
							form.querySelectorAll("input[name]").forEach(function (input) {
								input.value = "";
							});
						} else {
							// frappe puts the readable reason in _server_messages; the
							// exception string is a traceback and not for a visitor.
							var reason = "Something went wrong. Please try again.";
							try {
								var messages = JSON.parse(outcome.data._server_messages || "[]");
								if (messages.length) reason = JSON.parse(messages[0]).message;
							} catch (e) {}
							fail(error, reason);
						}
					})
					.catch(function () {
						fail(error, "We could not reach the server. Please try again.");
					})
					.finally(function () {
						button.disabled = false;
					});
			});
		});
	});
})();
"""


def form_card(title, subtitle_key, endpoint, fields, submit_label):
	"""A card whose fields post to one guest endpoint, with its own result and error."""
	result = block("div", styles=RESULT_STYLES, attributes={"data-result": "1", "hidden": "hidden"})
	error = block("div", styles=ERROR_STYLES, attributes={"data-error": "1", "hidden": "hidden"})

	return block(
		"form",
		styles=CARD_STYLES,
		attributes={"data-endpoint": endpoint},
		children=[
			block(
				"div",
				styles=CARD_HEAD_STYLES,
				children=[
					block("h2", styles=CARD_TITLE_STYLES, html=title),
					bound("div", subtitle_key, styles=CARD_SUB_STYLES),
				],
			),
			*fields,
			block(
				"div",
				styles=SUBMIT_ROW_STYLES,
				children=[
					block(
						"button",
						styles=BTN_STYLES,
						html=submit_label,
						attributes={"type": "button", "data-submit": "1"},
					)
				],
			),
			error,
			result,
		],
	)


def apply_content():
	return [
		public_frame(
			"heading",
			"intro",
			[
				form_card(
					"Your details",
					"products_note",
					"lending.portal_apply.submit_lead",
					[
						field("Full name", "applicant_name"),
						field("Email", "email", input_type="email"),
						field("Mobile number", "mobile_number", input_type="tel"),
						select_field("Product", "loan_product", "options"),
						field("Amount needed", "loan_amount", input_type="number"),
						field("Monthly income", "income", input_type="number", required=False),
						field("Tenure in months", "proposed_tenure", input_type="number", required=False),
					],
					"See my indicative offer",
				),
				block(
					"section",
					styles=CARD_STYLES,
					children=[
						block(
							"div",
							styles=CARD_HEAD_STYLES,
							children=[
								block("h2", styles=CARD_TITLE_STYLES, html="Our products"),
								bound("div", "products_note", styles=CARD_SUB_STYLES),
							],
						),
						pair_rows("products", with_detail=True),
					],
				),
			],
		)
	]


def track_content():
	return [
		public_frame(
			"heading",
			"intro",
			[
				form_card(
					"Find your application",
					"intro",
					"lending.portal_apply.track_application",
					[
						field("Reference number", "reference"),
						field("Mobile number", "mobile_number", input_type="tel"),
					],
					"Track",
				)
			],
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
		client_script=(APPLY_SCRIPT_NAME, CLIENT_SCRIPT),
	)
	track_page = build_page(
		"Portal Track",
		TRACK_ROUTE,
		"Track your application",
		None,
		track_content(),
		data_script=TRACK_DATA_SCRIPT,
		authenticated=False,
		client_script=(APPLY_SCRIPT_NAME, CLIENT_SCRIPT),
	)

	return apply_page, track_page
