# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The borrower's Documents page, as a Studio page.

It replaces a page of the Builder portal this one was migrated from, reading the
same two endpoints:
`get_documents_page` for what has been sent, and `get_document_choices` for what the
upload form may offer.

The upload form only appears when there is a draft application to attach to. A
submitted application is with our team, and section 6.2 of PORTAL_PLAN.md keeps the
borrower out of it from that point, so offering a file picker the server would refuse
would be a worse page than offering none.

The Builder form posted a multipart body through the shared client script. Here the two
choices are frappe-ui FormControls and the page script does the post, for the reason
given beside the file input: `upload_document` wants the file, not a File document.
"""

from lending.portal.studio_build.app import api_resource, page_script, upsert_page
from lending.portal.studio_build.blocks import (
	alert,
	block,
	button,
	card,
	column,
	muted,
	pair_rows,
	reader,
	record_list,
	text,
	toned_badge,
)
from lending.portal.studio_build.shell import frame

SOURCE = "documents"
CHOICES = "choices"
read = reader(SOURCE)
pick = reader(CHOICES)

# The upload, written as code because it sends a file. `call()` posts JSON, so the
# multipart body is built here and handed to fetch with the CSRF token the app carries.
UPLOAD = '''\tconst uploading = ref(false)

\tconst upload = () => {
\t\tconst input = document.querySelector("[data-portal-file]") as HTMLInputElement | null
\t\tconst chosen = input?.files?.[0]
\t\tif (!chosen || !application.value || !documentType.value) {
\t\t\ttoast.error("Please choose an application, a document type and a file.")
\t\t\treturn
\t\t}
\t\tconst body = new FormData()
\t\tbody.append("application", application.value)
\t\tbody.append("document_type", documentType.value)
\t\tbody.append("file", chosen)
\t\tuploading.value = true
\t\tfetch("/api/method/lending.portal.applications.upload_document", {
\t\t\tmethod: "POST",
\t\t\theaders: { "X-Frappe-CSRF-Token": (window as any).csrf_token },
\t\t\tbody,
\t\t})
\t\t\t.then((response) => response.json())
\t\t\t.then((payload) => {
\t\t\t\tif (payload.exc) throw new Error(payload._server_messages || "Upload failed")
\t\t\t\ttoast.success(payload.message?.message || "Received")
\t\t\t\tif (input) input.value = ""
\t\t\t\tcontext.documents.reload()
\t\t\t})
\t\t\t.catch((error) => toast.error(String(error.message || error)))
\t\t\t.finally(() => { uploading.value = false })
\t}'''


def upload_form():
	"""Which application, what kind of document, and the file itself."""
	fields = [
		block(
			"FormControl",
			props={
				"type": "select",
				"label": "For which application",
				"options": pick("application_options"),
				"modelValue": {"$type": "variable", "name": "application"},
			},
		),
		block(
			"FormControl",
			props={
				"type": "select",
				"label": "What is it",
				"options": pick("document_type_options"),
				"modelValue": {"$type": "variable", "name": "documentType"},
			},
		),
		# Not FileUploader. That component uploads to frappe's own upload_file and hands
		# back a File document, which would go round `upload_document` -- the endpoint
		# that checks the application is the borrower's, is still a draft, and stores
		# the file private and attached. It wants the file itself, so the page keeps a
		# plain input and posts a multipart body to it.
		block(
			"HTML",
			props={
				"html": '<input type="file" data-portal-file accept=".pdf,.png,.jpg,.jpeg">',
			},
		),
		muted("A PDF or a photo, up to 5 MB. We keep it private."),
		button(pick("upload_label"), script="upload()", variant="solid"),
	]

	return card(
		"Send us a document",
		read("upload_note"),
		column(fields, gap="12px"),
		visible=pick("can_upload"),
	)


def applications():
	"""Each application, where it has reached, and how much of it is already here."""
	return record_list(
		[("minmax(0, 1fr)", "Application"), ("9rem", "Stage"), ("9rem", "Documents")],
		read("applications"),
		[
			[
				text("{{ item.product }}", size="text-base"),
				muted("{{ item.reference }}"),
				muted("{{ item.progress }}"),
			],
			[toned_badge("{{ item.stage }}", "item.stage_tone")],
			[text("{{ item.attached }}", size="text-base")],
		],
		script="open(item.url)",
	)


def content():
	return [
		card(
			"Documents you have sent",
			read("documents_note"),
			pair_rows(read("documents"), with_detail=True),
		),
		upload_form(),
		# Shown instead of the form, so its condition is the opposite of the form's.
		alert(read("no_upload_note"), visible="{{ !%s.data.can_upload }}" % CHOICES),
		card("Applications", read("applications_note"), applications()),
	]


def build():
	return upsert_page(
		"Documents",
		"/documents",
		frame(SOURCE, content(), action_label="Contact us", action_route="/borrower-portal/profile"),
		[
			api_resource(SOURCE, "lending.portal.applications.get_documents_page"),
			api_resource(CHOICES, "lending.portal.applications.get_document_choices"),
			api_resource("alerts", "lending.portal.notifications.get_notifications", auto=0),
		],
		script=page_script(
			state=[("application", '""'), ("documentType", '""')],
			body=UPLOAD,
			returns=["upload", "uploading"],
		),
	)
