import { computed, ref, watch } from "vue"
import { call, toast } from "frappe-ui"
import { tone, appRoute } from "@app/utils/portal"

export default function setup(context: any) {
	const { router } = context
	const showAlerts = ref(false)
	const alertsTab = ref("attention")
	const application = ref("")
	const documentType = ref("")

	const open = (url?: string) => {
		const to = appRoute(url)
		if (to) router.push(to)
	}

	const uploading = ref(false)

	const upload = () => {
		const input = document.querySelector("[data-portal-file]") as HTMLInputElement | null
		const chosen = input?.files?.[0]
		if (!chosen || !application.value || !documentType.value) {
			toast.error("Please choose an application, a document type and a file.")
			return
		}
		const body = new FormData()
		body.append("application", application.value)
		body.append("document_type", documentType.value)
		body.append("file", chosen)
		uploading.value = true
		fetch("/api/method/lending.portal.applications.upload_document", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": (window as any).csrf_token },
			body,
		})
			.then((response) => response.json())
			.then((payload) => {
				if (payload.exc) throw new Error(payload._server_messages || "Upload failed")
				toast.success(payload.message?.message || "Received")
				if (input) input.value = ""
				context.documents.reload()
			})
			.catch((error) => toast.error(String(error.message || error)))
			.finally(() => { uploading.value = false })
	}

	return { tone, open, showAlerts, alertsTab, application, documentType, upload, uploading }
}
