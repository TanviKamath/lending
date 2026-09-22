// Shared by every page's setup() module, as "@app/utils/portal".

const TONES: Record<string, string> = { ok: "green", warn: "orange", danger: "red" }

/** A payload tone -- "", "ok", "warn", "danger" -- as a frappe-ui Badge theme. */
export function tone(value?: string): string {
	return TONES[value || ""] || "gray"
}

// A portal URL from the data layer as this app's own route.
//
// Every endpoint answers with the Builder portal's paths -- "/borrower/loan/L-0001" --
// because the Builder pages still serve them. The data layer is shared and is not
// forked for this app, so the prefix comes off here instead.
//
// Line comments rather than a JSDoc block: a continuation line of one begins with a
// space, and pycodestyle takes the first space-indented line in a file as its indent
// character -- after which every tab in this tab-indented module reads as E117.
export function appRoute(url?: string): string {
	if (!url) return ""
	return url.replace(/^\/borrower(-portal)?/, "") || "/overview"
}
