import { computed, ref, watch } from "vue"
import { call, toast } from "frappe-ui"
import { tone, appRoute, useSearch } from "@app/utils/portal"

export default function setup(context: any) {
	const { router } = context
	const showAlerts = ref(false)
	const alertsTab = ref("attention")
	const sidebarCollapsed = ref<boolean | null>(null)
	const previewTab = ref("terms")

	const open = (url?: string) => {
		const to = appRoute(url)
		if (to) router.push(to)
	}
	const search = useSearch(open)

	return { tone, open, showAlerts, alertsTab, sidebarCollapsed, ...search, previewTab }
}
