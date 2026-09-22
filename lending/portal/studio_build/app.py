# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Creating the Studio App, its pages and its components.

Studio owns the export. A Studio App and every page under it are saved with
`is_standard` and `frappe_app = lending`, and Studio's own exporters write them to
lending/studio/borrower_portal/ on each save -- the app JSON, one folder per page
holding its JSON and its `setup()` module, and the shared components beside them.
Nothing in this package writes those files.

The route is `borrower-portal`, not `borrower`. The Builder pages still answer on
/borrower/*, /apply and /track, and this migration does not take anything away from
them: the two portals run side by side until whoever owns the cutover says otherwise,
and a cutover is then a rename of one field.
"""

import json
import os

import frappe

APP_NAME = "borrower-portal"
APP_TITLE = "Borrower Portal"
FRAPPE_APP = "lending"

# The file every page's `setup()` module imports. Written here rather than through
# Studio, which exports documents and knows nothing about the app's own source tree.
SHARED_UTILS_PATH = ("utils", "portal.ts")
SHARED_UTILS = '''// Shared by every page's setup() module, as "@app/utils/portal".

const TONES: Record<string, string> = { ok: "green", warn: "orange", danger: "red" }

/** A payload tone -- "", "ok", "warn", "danger" -- as a frappe-ui Badge theme. */
export function tone(value?: string): string {
\treturn TONES[value || ""] || "gray"
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
\tif (!url) return ""
\treturn url.replace(/^\\/borrower(-portal)?/, "") || "/overview"
}
'''

# A page's `setup()` module. An exported Studio app keeps its state in code rather than
# in Studio Page Variables, so this is where a page's refs and handlers live, and
# whatever it returns is what the page's blocks can bind to and its events can write.
#
# Every page returns the four the frame itself reads: the tone helper its badges take
# their colour from, the one way a row opens the record it stands for, and the two
# pieces of state behind the bell. They are here rather than in the header component
# because a Studio Component holds blocks and no state of its own.
SCRIPT_TEMPLATE = '''import {{ computed, ref, watch }} from "vue"
import {{ call, toast }} from "frappe-ui"
import {{ tone, appRoute }} from "@app/utils/portal"

export default function setup(context: any) {{
\tconst {{ router }} = context
\tconst showAlerts = ref(false)
\tconst alertsTab = ref("attention")
{state}
\tconst open = (url?: string) => {{
\t\tconst to = appRoute(url)
\t\tif (to) router.push(to)
\t}}
{body}
\treturn {{ tone, open, showAlerts, alertsTab{returns} }}
}}
'''


def page_script(state=(), body="", returns=()):
	"""One page's setup() module: the frame's own bindings, plus whatever the page adds.

	`state` is (name, initial value) pairs declared as refs, `body` is extra source
	dropped in before the return, and `returns` names anything in `body` the blocks
	need to reach.
	"""
	declarations = "".join(f'\tconst {name} = ref({initial})\n' for name, initial in state)
	extra = ", ".join(name for name, _initial in state) + (", " if state and returns else "")

	return SCRIPT_TEMPLATE.format(
		state=declarations,
		body=f"\n{body}\n" if body else "",
		returns=f", {extra}{', '.join(returns)}" if (state or returns) else "",
	)


PAGE_SCRIPT = page_script()


def api_resource(name, method, params=None, auto=1):
	"""A page's data source: one whitelisted endpoint, called as the page loads.

	The endpoints are the portal's own, unchanged. That is the whole reason this
	migration is a re-layout rather than a rewrite: `lending.portal.*` already answers
	with formatted, translated payloads through @frappe.whitelist, so a Studio page
	reads exactly what a Builder data script read.
	"""
	return {
		"resource_type": "API Resource",
		"resource_name": name,
		"url": method,
		"method": "GET",
		"auto": auto,
		"params": json.dumps(params) if params else None,
	}


def upsert_app():
	"""Create or update the Studio App. Safe to re-run."""
	fields = {
		"app_name": APP_NAME,
		"app_title": APP_TITLE,
		"route": APP_NAME,
		"is_standard": 1,
		"frappe_app": FRAPPE_APP,
	}

	if frappe.db.exists("Studio App", APP_NAME):
		doc = frappe.get_doc("Studio App", APP_NAME)
		doc.update(fields)
		doc.save()
		action = "updated"
	else:
		doc = frappe.get_doc(dict(doctype="Studio App", name=APP_NAME, **fields)).insert()
		action = "created"

	write_shared_utils()
	print(f"{action} Studio App {doc.name} at /{APP_NAME}")

	return doc.name


def write_shared_utils():
	"""Put utils/portal.ts in the exported app folder, creating the folder if Studio has not."""
	folder = frappe.get_app_source_path(FRAPPE_APP, "studio", APP_NAME, SHARED_UTILS_PATH[0])
	frappe.create_folder(folder)
	path = os.path.join(folder, SHARED_UTILS_PATH[1])
	with open(path, "w") as source:
		source.write(SHARED_UTILS)


def upsert_component(component_id, component_name, tree, inputs=()):
	"""Create or replace one shared piece of the frame.

	An unchanged component is left alone: saving one publishes a document change to
	every open editor, and eleven pages built in a row would do it eleven times over.
	"""
	fields = {
		"component_name": component_name,
		"component_id": component_id,
		"block": json.dumps(tree, indent=1),
		"inputs": [{"input_name": name, "type": "string", "description": note} for name, note in inputs],
	}

	if frappe.db.exists("Studio Component", component_id):
		doc = frappe.get_doc("Studio Component", component_id)
		if doc.block == fields["block"]:
			return doc.name
		doc.update(fields)
		doc.save()
		action = "updated"
	else:
		doc = frappe.get_doc(dict(doctype="Studio Component", **fields)).insert()
		action = "created"

	print(f"{action} Studio Component {doc.name}")

	return doc.name


def upsert_page(title, route, blocks, resources, script=PAGE_SCRIPT, allow_guest=False):
	"""Create or replace one page of the app, found by the route it answers on.

	Not by name. Studio names a page `page-<hash>` and frappe clears any name handed to
	an insert before naming runs, so there is no name to look a page up by that this
	module could choose. The route is the page's real identity anyway -- it is what a
	borrower reaches it at, and what Studio itself refuses to let two pages share.

	The exported folder is named after the title, so a retitle relocates it. Studio
	handles that move; what it cannot handle is two pages built for one route, which is
	why this looks the route up rather than trusting a name.
	"""
	fields = {
		"page_title": title,
		"route": route,
		"studio_app": APP_NAME,
		"published": 1,
		"allow_guest": 1 if allow_guest else 0,
		"is_standard": 1,
		"frappe_app": FRAPPE_APP,
		"blocks": frappe.as_json(blocks),
		"resources": resources,
		"script": script,
		# A leftover draft outranks what this script just wrote: the canvas loads
		# draft_blocks when it has one, and so does the published page's preview.
		"draft_blocks": None,
	}

	existing = frappe.db.get_value("Studio Page", {"studio_app": APP_NAME, "route": route}, "name")
	if existing:
		doc = frappe.get_doc("Studio Page", existing)
		doc.resources = []
		doc.update(fields)
		doc.save()
		action = "updated"
	else:
		doc = frappe.get_doc(dict(doctype="Studio Page", **fields)).insert()
		action = "created"

	# The script lives in the page's companion .ts once the page is exported, and the
	# DB field is cleared. Writing it has to come after the save that created the folder.
	doc.write_script_file()

	frappe.clear_document_cache("Studio Page", doc.name)
	print(f"{action} Studio Page {doc.name} at /{APP_NAME}{route}")

	return doc.name
