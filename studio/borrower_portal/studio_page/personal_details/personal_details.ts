import { computed, ref, watch } from "vue"
import { call, toast } from "frappe-ui"
import { tone, appRoute } from "@app/utils/portal"

export default function setup(context: any) {
	const { router } = context
	const showAlerts = ref(false)
	const alertsTab = ref("attention")
	const sidebarCollapsed = ref<boolean | null>(null)
	const editing = ref(false)

	const open = (url?: string) => {
		const to = appRoute(url)
		if (to) router.push(to)
	}

	const form = ref<Record<string, string>>({})
	const customer = ref("")
	const saving = ref(false)

	const fillForm = () => {
		const data = context.profile.data || {}
		customer.value = data.form_customer || ""
		form.value = Object.fromEntries(
			['email', 'mobile', 'phone', 'address_line1', 'address_line2', 'city', 'state', 'pincode', 'country'].map((field) => [field, data["form_" + field] || ""]),
		)
	}
	watch(() => context.profile.data, fillForm, { immediate: true })

	const edit = () => { fillForm(); editing.value = true }

	const save = () => {
		saving.value = true
		call("lending.portal.profile.save_profile", { customer: customer.value, ...form.value })
			.then((result: any) => {
				toast.success(result?.message || "Your details have been updated.")
				editing.value = false
				context.profile.reload()
			})
			.catch((error: any) => toast.error(String(error.messages?.[0] || error)))
			.finally(() => { saving.value = false })
	}

	return { tone, open, showAlerts, alertsTab, sidebarCollapsed, editing, form, customer, edit, save, saving }
}
