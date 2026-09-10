
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
