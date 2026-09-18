
(function () {
	function ready(fn) {
		if (document.readyState !== "loading") fn();
		else document.addEventListener("DOMContentLoaded", fn);
	}

	function post(endpoint, body) {
		var options = { method: "POST", body: body };
		// A multipart body sets its own boundary in the Content-Type, so naming the
		// header here would produce one without a boundary and the upload would fail.
		if (!(body instanceof FormData)) {
			options.headers = { "Content-Type": "application/x-www-form-urlencoded" };
			options.body = body.toString();
		}

		return fetch("/api/method/" + endpoint, options).then(function (response) {
			return response.json().then(function (data) {
				return { ok: response.ok, data: data };
			});
		});
	}

	// frappe puts the readable reason in _server_messages; the exception string is a
	// traceback and not for a visitor.
	function reason(payload) {
		try {
			var messages = JSON.parse(payload._server_messages || "[]");
			if (messages.length) return JSON.parse(messages[0]).message;
		} catch (error) {}
		return "Something went wrong. Please try again.";
	}

	function fail(box, message) {
		if (!box) return;
		box.textContent = message;
		box.hidden = false;
	}

	function clear(box) {
		if (box) box.hidden = true;
	}

	// The label is its own element inside the button, because a button that also
	// holds a chevron would lose it the first time the label was swapped out.
	function busy(button, state, label) {
		var slot = button.querySelector("[data-label]") || button;
		button.disabled = state;
		if (state) {
			slot.dataset.idleLabel = slot.textContent;
			slot.textContent = label;
		} else if (slot.dataset.idleLabel) {
			slot.textContent = slot.dataset.idleLabel;
		}
	}

	function values(scope, multipart) {
		var body = multipart ? new FormData() : new URLSearchParams();
		var missing = false;
		scope.querySelectorAll("input[name], select[name]").forEach(function (input) {
			// Disabled means the field does not apply: a company has no date of birth.
			// Whatever was typed before the visitor changed their mind is not theirs.
			if (input.disabled) return;
			if (input.type === "file") {
				if (input.required && !input.files.length) missing = true;
				if (input.files.length) body.append(input.name, input.files[0]);
				return;
			}
			if (input.required && !input.value.trim()) missing = true;
			// A blank optional box is left out rather than posted as an empty string.
			if (input.value.trim()) body.append(input.name, input.value.trim());
		});
		return { body: body, missing: missing };
	}

	// --- filling the two result shells ---------------------------------------------
	//
	// Both are rendered by the page and cloned from here, so every style stays in
	// theme and this function only ever sets text.

	function fillOffer(card, payload) {
		if (!card) return;
		card.querySelector("[data-offer-headline]").textContent = payload.headline || "";
		card.querySelector("[data-offer-message]").textContent = payload.message || "";

		var grid = card.querySelector("[data-offer-grid]");
		var template = grid.querySelector("[data-offer-cell]");
		grid.querySelectorAll("[data-offer-cell]").forEach(function (cell, index) {
			if (index) cell.remove();
		});

		(payload.offer || []).forEach(function (row) {
			var cell = template.cloneNode(true);
			cell.querySelector("[data-offer-label]").textContent = row.label;
			cell.querySelector("[data-offer-value]").textContent = row.value;
			cell.hidden = false;
			grid.appendChild(cell);
		});
		grid.hidden = !(payload.offer || []).length;

		card.querySelector("[data-offer-reference]").textContent = payload.reference_note || "";

		var action = card.querySelector("[data-offer-action]");
		action.textContent = payload.action || "";
		action.hidden = !payload.action;

		card.hidden = false;
	}

	function fillTimeline(track, steps) {
		if (!track) return;
		var template = track.querySelector("[data-step-row]");
		track.querySelectorAll("[data-step-row]").forEach(function (row, index) {
			if (index) row.remove();
		});

		(steps || []).forEach(function (item, index) {
			var row = template.cloneNode(true);
			var mark = row.querySelector("[data-step-mark]");
			mark.innerHTML = item.mark || "";
			mark.setAttribute("style", item.tone || "");
			row.querySelector("[data-step-title]").textContent = item.title || "";
			row.querySelector("[data-step-note]").textContent = item.note || "";
			// The last stem would trail off into nothing below the final step.
			row.querySelector("[data-step-stem]").hidden = index === (steps || []).length - 1;
			row.hidden = false;
			track.appendChild(row);
		});
		track.hidden = !(steps || []).length;
	}

	// --- the simple one-shot forms (/track) ----------------------------------------

	function wireForms() {
		document.querySelectorAll("[data-endpoint]").forEach(function (form) {
			var button = form.querySelector("[data-submit]");
			if (!button) return;
			var error = form.querySelector("[data-error]");
			var card = form.querySelector("[data-offer]");
			var track = form.querySelector("[data-timeline]");

			button.addEventListener("click", function (event) {
				event.preventDefault();
				clear(error);
				if (card) card.hidden = true;
				if (track) track.hidden = true;

				var read = values(form, form.hasAttribute("data-upload"));
				if (read.missing) return fail(error, "Please fill in every field.");

				busy(button, true, "Working\u2026");
				post(form.dataset.endpoint, read.body)
					.then(function (outcome) {
						if (!outcome.ok || !outcome.data.message) {
							return fail(error, reason(outcome.data));
						}

						fillOffer(card, outcome.data.message);
						fillTimeline(track, outcome.data.message.steps);

						// A write changes what the rest of the page shows, so the page
						// is re-read rather than patched in half a dozen places.
						if (form.hasAttribute("data-reload")) {
							window.location.reload();
						}
					})
					.catch(function () {
						fail(error, "We could not reach the server. Please try again.");
					})
					.finally(function () {
						busy(button, false);
					});
			});
		});
	}

	// --- the sections kept back until they are asked for ---------------------------
	//
	// A page that opens with its edit form showing reads as a form to fill in, when
	// what the borrower came for is what is already on record. So the form is built
	// hidden and one button brings it out. Pairing is by name rather than by position,
	// so the button and the panel it opens need not be near each other on the page.

	function wireReveals() {
		document.querySelectorAll("[data-reveals]").forEach(function (button) {
			var name = button.dataset.reveals;
			var panel = document.querySelector('[data-revealed="' + name + '"]');
			if (!panel) return;

			function show(open) {
				panel.hidden = !open;
				button.hidden = open;
				if (!open) return button.focus();
				var first = panel.querySelector("input:not([type=hidden])");
				if (first) first.focus();
			}

			button.addEventListener("click", function (event) {
				event.preventDefault();
				show(true);
			});

			// Closing again leaves whatever was typed in the boxes. Nothing has been
			// sent, and the page re-reads itself after a save, so the next opening
			// starts from what is on record either way.
			panel.querySelectorAll('[data-hides="' + name + '"]').forEach(function (close) {
				close.addEventListener("click", function (event) {
					event.preventDefault();
					show(false);
				});
			});
		});
	}

	// --- the code boxes ------------------------------------------------------------

	function wireCodeBoxes(group) {
		if (!group) return;
		var boxes = Array.prototype.slice.call(group.querySelectorAll("input"));

		boxes.forEach(function (box, index) {
			box.addEventListener("input", function () {
				box.value = box.value.replace(/\D/g, "").slice(0, 1);
				if (box.value && boxes[index + 1]) boxes[index + 1].focus();
			});

			box.addEventListener("keydown", function (event) {
				if (event.key === "Backspace" && !box.value && boxes[index - 1]) {
					boxes[index - 1].focus();
				}
			});

			// Codes arrive by text message, so most people paste all six at once.
			box.addEventListener("paste", function (event) {
				event.preventDefault();
				var digits = (event.clipboardData || window.clipboardData)
					.getData("text")
					.replace(/\D/g, "");
				boxes.forEach(function (target, offset) {
					if (offset >= index) target.value = digits.charAt(offset - index) || "";
				});
				var last = Math.min(index + digits.length, boxes.length - 1);
				boxes[last].focus();
			});
		});

		return function () {
			return boxes
				.map(function (box) {
					return box.value;
				})
				.join("");
		};
	}

	// --- the sidebar ---------------------------------------------------------------
	//
	// Every /borrower page is its own request, so a sidebar that reopened on each one
	// would undo the visitor's choice seven times an hour. The choice is remembered
	// per browser; localStorage throws outright in a few privacy settings, so every
	// read and write of it is guarded and a failure just means it is not remembered.

	var SIDEBAR_KEY = "lending-portal-sidebar-collapsed";

	function remembered(key) {
		try {
			return window.localStorage.getItem(key);
		} catch (error) {
			return null;
		}
	}

	function remember(key, value) {
		try {
			window.localStorage.setItem(key, value);
		} catch (error) {}
	}

	function wireSidebar() {
		var sidebar = document.querySelector("[data-sidebar]");
		var toggle = sidebar && sidebar.querySelector("[data-sidebar-toggle]");
		if (!toggle) return;

		// One button for both directions. The stylesheet turns it over; this says what
		// it will do next, for anyone who cannot see which way it points.
		function apply(collapsed) {
			sidebar.dataset.collapsed = collapsed ? "1" : "0";
			toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
			toggle.setAttribute("aria-label", collapsed ? "Show the menu" : "Hide the menu");
		}

		apply(remembered(SIDEBAR_KEY) === "1");

		toggle.addEventListener("click", function (event) {
			event.preventDefault();
			var collapsed = sidebar.dataset.collapsed !== "1";
			apply(collapsed);
			remember(SIDEBAR_KEY, collapsed ? "1" : "0");
		});
	}

	// --- the apply wizard ----------------------------------------------------------

	function wireApply() {
		var wizard = document.querySelector("[data-wizard]");
		if (!wizard) return;

		var panels = wizard.querySelectorAll("[data-panel]");
		var progress = document.querySelector("[data-progress]");
		var steps = progress ? Number(progress.dataset.progress) : 0;
		var token = null;
		var accountToken = null;

		// --- moving between the screens --------------------------------------------

		function setStep(current) {
			panels.forEach(function (panel) {
				panel.hidden = Number(panel.dataset.panel) !== current;
			});
			showProgress(current);
			window.scrollTo({ top: 0, behavior: "smooth" });
		}

		function showProgress(current) {
			if (!progress) return;

			// The first screen is the invitation, not a step, so the bar starts empty.
			progress.hidden = current < 2;
			var done = current - 1;
			var panel = wizard.querySelector('[data-panel="' + current + '"]');

			progress.querySelector("[data-progress-name]").textContent = panel ? panel.dataset.name : "";
			progress.querySelector("[data-progress-count]").textContent =
				"Step " + done + " of " + steps;
			progress.querySelector("[data-progress-fill]").style.width = (done / steps) * 100 + "%";
		}

		wizard.querySelectorAll("[data-next], [data-back]").forEach(function (button) {
			button.addEventListener("click", function (event) {
				event.preventDefault();
				setStep(Number(button.dataset.next || button.dataset.back));
			});
		});

		// --- the tiles -------------------------------------------------------------
		//
		// Each group of tiles answers for one field, which lives as a hidden input on
		// the details panel: the screens are separate, the form that posts is not.

		var pills = {
			applicant_type: wizard.querySelector("[data-picked-type]"),
			loan_product: wizard.querySelector("[data-picked-product]"),
		};

		function wireChoice(group) {
			var name = group.dataset.choice;
			var answer = wizard.querySelector('input[name="' + name + '"]');
			var panel = group.closest("[data-panel]");
			var gate = panel ? panel.querySelector("[data-gate]") : null;
			var tiles = group.querySelectorAll("[data-tile]");

			function choose(tile) {
				tiles.forEach(function (other) {
					var chosen = other === tile;
					other.dataset.chosen = chosen ? "1" : "0";
					other.setAttribute("aria-checked", chosen ? "true" : "false");
				});

				if (answer) answer.value = tile.dataset.value || "";
				// A screen whose question is unanswered has nothing to go on with.
				if (gate) gate.disabled = false;
				if (name === "applicant_type") showFieldsFor(tile.dataset.value);
				show(pills[name], tile);
			}

			tiles.forEach(function (tile) {
				tile.addEventListener("click", function () {
					choose(tile);
				});
				// The form opens with an answer to the first question, so the tiles
				// have to open agreeing with it.
				if (answer && answer.value && answer.value === tile.dataset.value) choose(tile);
			});
		}

		// What was answered two screens ago, on the screen that posts it.
		function show(pill, tile) {
			if (!pill) return;
			var label = tile.querySelector("[data-tile-label]");
			pill.textContent = label ? label.textContent.trim() : tile.dataset.value;
			pill.hidden = false;
		}

		wizard.querySelectorAll("[data-choice]").forEach(wireChoice);

		// --- who is borrowing ------------------------------------------------------
		//
		// A company has no date of birth and no job; a person has no company name. The
		// server drops whichever does not apply, and this keeps the form saying the same.

		var details = wizard.querySelector('[data-panel="5"]');

		function showFieldsFor(audience) {
			details.querySelectorAll("[data-only-for]").forEach(function (node) {
				var applies = node.dataset.onlyFor === audience;
				node.hidden = !applies;
				node.querySelectorAll("input, select").forEach(function (input) {
					// A hidden required box would block the form with nothing to see.
					input.disabled = !applies;
				});
			});
		}

		// --- the mobile number -----------------------------------------------------

		var verify = wizard.querySelector('[data-panel="4"]');
		var mobile = verify.querySelector('input[name="mobile_number"]');
		var codeSection = verify.querySelector("[data-code-section]");
		var readCode = wireCodeBoxes(verify.querySelector("[data-code]"));
		var verifyError = verify.querySelector("[data-error]");
		var verifyNote = verify.querySelector("[data-sent-note]");

		// One way on, in one place, whichever half of the screen is showing.
		function showCodeSection() {
			codeSection.hidden = false;
			verify.querySelectorAll('[data-when="before-code"]').forEach(function (node) {
				node.hidden = true;
			});
			verify.querySelectorAll('[data-when="after-code"]').forEach(function (node) {
				node.hidden = false;
			});
		}

		function sendCode(button) {
			clear(verifyError);
			if (!mobile.value.trim()) return fail(verifyError, "Please give your mobile number.");

			var body = new URLSearchParams();
			body.append("mobile_number", mobile.value.trim());

			busy(button, true, "Sending…");
			post("lending.portal.apply.send_mobile_code", body)
				.then(function (outcome) {
					if (!outcome.ok || !outcome.data.message) return fail(verifyError, reason(outcome.data));
					showCodeSection();
					verifyNote.textContent = outcome.data.message.message || "";
					var first = codeSection.querySelector("input");
					if (first) first.focus();
				})
				.catch(function () {
					fail(verifyError, "We could not reach the server. Please try again.");
				})
				.finally(function () {
					busy(button, false);
				});
		}

		function confirmCode(button) {
			clear(verifyError);
			var code = readCode();
			if (code.length !== 6) return fail(verifyError, "Please enter all six digits.");

			var body = new URLSearchParams();
			body.append("mobile_number", mobile.value.trim());
			body.append("otp", code);

			busy(button, true, "Checking…");
			post("lending.portal.apply.confirm_mobile_code", body)
				.then(function (outcome) {
					if (!outcome.ok || !outcome.data.message) return fail(verifyError, reason(outcome.data));

					var payload = outcome.data.message;
					// A wrong code comes back as a value, not an error, so that the
					// telephony app keeps its record of the failed attempt.
					if (!payload.verified) return fail(verifyError, payload.message);

					token = payload.token;
					// The number is settled, so the next screen shows it back rather
					// than asking for it a second time.
					var echo = details.querySelector("[data-verified-echo]");
					if (echo) echo.value = mobile.value.trim();

					setStep(5);
					var first = details.querySelector("input[name]:not([type=hidden])");
					if (first) first.focus();
				})
				.catch(function () {
					fail(verifyError, "We could not reach the server. Please try again.");
				})
				.finally(function () {
					busy(button, false);
				});
		}

		// Enter on the number field is the same intent as pressing Send code.
		mobile.addEventListener("keydown", function (event) {
			if (event.key !== "Enter") return;
			event.preventDefault();
			verify.querySelector('[data-action="send-code"]').click();
		});

		// --- the details, and the offer they earn ----------------------------------

		var offer = wizard.querySelector('[data-panel="6"]');
		var detailsError = details.querySelector("[data-error]");

		function submitLead(button) {
			clear(detailsError);
			var product = details.querySelector('input[name="loan_product"]');
			if (product && !product.value) return fail(detailsError, "Please pick what you are looking for.");

			var read = values(details);
			if (read.missing) return fail(detailsError, "Please fill in every required field.");
			if (!token) return fail(detailsError, "Please confirm your mobile number first.");

			read.body.append("token", token);

			busy(button, true, "Working it out…");
			post("lending.portal.apply.submit_lead", read.body)
				.then(function (outcome) {
					if (!outcome.ok || !outcome.data.message) return fail(detailsError, reason(outcome.data));
					// The token is spent server-side, so a second submit cannot succeed.
					token = null;
					accountToken = outcome.data.message.account_token || null;
					fillOffer(offer.querySelector("[data-offer]"), outcome.data.message);
					setStep(6);
				})
				.catch(function () {
					fail(detailsError, "We could not reach the server. Please try again.");
				})
				.finally(function () {
					busy(button, false);
				});
		}

		// --- the account -----------------------------------------------------------

		var account = wizard.querySelector('[data-panel="7"]');
		var accountError = account.querySelector("[data-error]");

		function toAccount() {
			var who = account.querySelector("[data-account-user]");
			var email = details.querySelector('input[name="email"]');
			who.textContent = email && email.value ? "You will sign in as " + email.value.trim() : "";
			setStep(7);
			var box = account.querySelector('input[name="password"]');
			if (box) box.focus();
		}

		function createAccount(button) {
			clear(accountError);
			var read = values(account);
			if (read.missing) return fail(accountError, "Please choose a password.");
			if (!accountToken) return fail(accountError, "Please finish your application first.");

			read.body.append("token", accountToken);

			busy(button, true, "Creating…");
			post("lending.portal.apply.create_account", read.body)
				.then(function (outcome) {
					if (!outcome.ok || !outcome.data.message) return fail(accountError, reason(outcome.data));
					// Spent server-side, so a second click cannot open a second account.
					accountToken = null;
					window.location.assign(outcome.data.message.redirect || "/borrower/overview");
				})
				.catch(function () {
					fail(accountError, "We could not reach the server. Please try again.");
				})
				.finally(function () {
					busy(button, false);
				});
		}

		var actions = {
			"send-code": sendCode,
			resend: sendCode,
			"confirm-code": confirmCode,
			submit: submitLead,
			"to-account": toAccount,
			"create-account": createAccount,
		};

		wizard.querySelectorAll("[data-action]").forEach(function (button) {
			button.addEventListener("click", function (event) {
				event.preventDefault();
				actions[button.dataset.action](button);
			});
		});

		// The details form opens with an answer to the first question already in it,
		// so it has to open showing the fields that answer asks for.
		var opening = details.querySelector('input[name="applicant_type"]');
		showFieldsFor(opening ? opening.value : "Individual");
		setStep(1);
	}

	ready(function () {
		wireSidebar();
		wireReveals();
		wireForms();
		wireApply();
	});
})();
