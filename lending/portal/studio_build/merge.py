# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Keeping hand edits when the generator rebuilds a page.

`upsert_page` used to replace a page outright: it wrote `blocks`, cleared `resources`,
rewrote the script file and set `draft_blocks` to None. Anything laid out on the Studio
canvas was gone the next time the build ran, whether it had been published or was still
a draft, because those two fields are exactly where the canvas keeps its work.

So a rebuild merges instead. Three trees go in -- what the generator wrote last time
(the baseline, kept beside this module), what is in the database now, and what the
generator wants to write -- and the rule between them is one sentence: **the canvas
always wins**. A field the canvas has not touched takes the generator's new value, so a
rebuild still carries changes into the page; a field the canvas has touched is left
alone, and so is any block added there. The generator can only delete what is still
exactly as it left it.

Identity
--------
The merge matches blocks by `componentId`, which the generator never used to set --
Studio invents a random one per block on load, so two runs of the same generator
produced two trees with nothing in common. `identify` now stamps a deterministic id
onto every block from its position in the tree, which is what makes a block on the
canvas recognisable as the same block on the next run.

The ids shift if a block is inserted before its same-named siblings. That is a real
limit, and it is pointed the safe way: an id that fails to match reads as "added on the
canvas" and is kept, so the worst case is a duplicated block to delete rather than a
lost edit.

It is also why a page cannot be brought into the merge without being overwritten once.
Every tree in a merge has to carry ids stamped the same way, and a page written before
this module existed carries Studio's random ones. See `_replace_page` in app.
"""

import json
import os
import re
from contextlib import contextmanager

import frappe

BASELINE_FOLDER = ("portal", "studio_build", "baseline")

# Set while a build is throwing the merge away -- see reset(). A flag on the module
# rather than an argument, because a reset is a property of the run and not of any one
# page, and every page's build() calls upsert_page for itself.
_RESET = False


@contextmanager
def reset(active=True):
	"""Read every baseline as missing, so the build inside takes the replace path throughout."""
	global _RESET

	_RESET, previous = active, _RESET
	try:
		yield
	finally:
		_RESET = previous


def identify(blocks, route):
	"""Stamp a deterministic componentId onto every block of a generated tree."""
	for index, node in enumerate(blocks):
		_identify(node, f"{baseline_key(route)}-{index}")

	return blocks


def merge_blocks(base, live, new):
	"""The tree to save: `new` carried onto `live`, with the canvas's own work kept."""
	return PageMerge().children(base, live, new)


def merge_resources(live, new):
	"""The generator's data sources, plus any the canvas added that it does not know about."""
	generated = {row["resource_name"] for row in new}

	return list(new) + [row for row in live if row.get("resource_name") not in generated]


class PageMerge:
	"""A three-way merge of one page's blocks, in which the hand edit always wins.

	`base` is what the generator wrote last time, `live` is what the database holds now
	and `new` is what the generator wants to write. Every comparison asks the same
	question -- has the canvas changed this since the generator wrote it? -- and takes
	the generator's value only where the answer is no.
	"""

	SCALARS = ("componentName", "blockName", "visibilityCondition", "originalElement", "classes")
	MAPS = (
		"componentProps",
		"componentEvents",
		"baseStyles",
		"mobileStyles",
		"tabletStyles",
		"attributes",
	)

	def __init__(self):
		# ids of blocks kept because the canvas had changed them, for the build's report
		self.kept = []

	def children(self, base, live, new):
		"""One list of sibling blocks, matched by componentId."""
		base_by_id = self._by_id(base)
		live_by_id = self._by_id(live)
		new_by_id = self._by_id(new)

		merged = []
		for node in new:
			node_id = node.get("componentId")
			if node_id in live_by_id:
				merged.append(self.node(base_by_id.get(node_id), live_by_id[node_id], node))
			elif node_id not in base_by_id:
				merged.append(node)
			# a block the baseline has and the canvas does not was deleted there; a
			# delete is a hand edit too, so the generator does not put it back

		self._readd(merged, base_by_id, live, new_by_id)

		return merged

	def node(self, base, live, new):
		"""One block: its own fields, then its children and its slots."""
		base = base or {}
		merged = dict(live)

		for field in self.SCALARS:
			if live.get(field) != base.get(field):
				continue
			if field in new:
				merged[field] = new[field]
			else:
				merged.pop(field, None)

		for field in self.MAPS:
			self._set(merged, live, new, field, self.mapping(base.get(field) or {}, live.get(field) or {}, new.get(field) or {}))

		self._set(
			merged,
			live,
			new,
			"children",
			self.children(base.get("children") or [], live.get("children") or [], new.get("children") or []),
		)
		self._set(
			merged,
			live,
			new,
			"componentSlots",
			self.slots(
				base.get("componentSlots") or {},
				live.get("componentSlots") or {},
				new.get("componentSlots") or {},
			),
		)

		return merged

	@staticmethod
	def _set(merged, live, new, field, value):
		"""Write a merged field, but do not invent an empty one neither side carried.

		A rebuild that adds `attributes: {}` to every block of every page is a diff
		nobody can read past, and it is what makes a real change invisible.
		"""
		if value or field in live or field in new:
			merged[field] = value
		else:
			merged.pop(field, None)

	def mapping(self, base, live, new):
		"""One dict of props, styles, events or attributes, key by key."""
		merged = dict(live)

		for key, value in new.items():
			if live.get(key) == base.get(key):
				merged[key] = value

		for key in base:
			if key not in new and live.get(key) == base.get(key):
				merged.pop(key, None)

		return merged

	def slots(self, base, live, new):
		"""Named slots. A slot the generator has dropped stays, since it may hold hand-added blocks."""
		merged = dict(live)

		for name, slot in new.items():
			live_slot = live.get(name)
			if live_slot is None:
				merged[name] = slot
				continue

			merged[name] = dict(
				live_slot,
				slotContent=self.children(
					(base.get(name) or {}).get("slotContent") or [],
					live_slot.get("slotContent") or [],
					slot.get("slotContent") or [],
				),
			)

		return merged

	def _readd(self, merged, base_by_id, live, new_by_id):
		"""Put back what the canvas holds and the generated tree has no place for.

		Two kinds: a block added on the canvas, which the baseline has never seen, and a
		block the generator has dropped but the canvas has since changed. Both are hand
		edits, so both survive the rebuild, near where they sat.
		"""
		for index, node in enumerate(live):
			node_id = node.get("componentId")
			if node_id in new_by_id:
				continue
			if node_id in base_by_id and node == base_by_id[node_id]:
				continue

			self.kept.append(node_id)
			merged.insert(min(index, len(merged)), node)

	@staticmethod
	def _by_id(blocks):
		return {node.get("componentId"): node for node in blocks if node.get("componentId")}


def read_baseline(key):
	"""What the generator last left under this key, or None if it has never written it."""
	path = _baseline_path(key)
	if _RESET or not os.path.exists(path):
		return None

	with open(path) as source:
		return json.load(source)


def write_baseline(key, record):
	"""Record what the generator leaves behind, as the base of the next merge.

	Files in the app rather than fields on the documents: the baseline has to survive a
	site rebuild and be readable in a diff, since it is the only record of which half of
	a page is the generator's.
	"""
	with open(_baseline_path(key), "w") as target:
		json.dump(record, target, indent=1)


def baseline_key(value):
	"""One route, component id or filename as the name of its baseline file.

	A slug rather than a scrub: a route can carry a parameter -- /loan/:name -- and the
	result is both a filename and the prefix of every block id under it, so it can hold
	nothing but word characters.
	"""
	return re.sub(r"\W+", "_", value).strip("_").lower() or "index"


def _baseline_path(key):
	# get_app_path, not get_app_source_path: the baselines belong beside the generators
	# that write them, inside the package, rather than at the top of the repo.
	folder = frappe.get_app_path("lending", *BASELINE_FOLDER)
	frappe.create_folder(folder)

	return os.path.join(folder, f"{key}.json")


def _identify(node, node_id):
	node["componentId"] = node_id
	_identify_siblings(node.get("children") or [], node_id)

	for name, slot in (node.get("componentSlots") or {}).items():
		content = slot.get("slotContent")
		if isinstance(content, list):
			_identify_siblings(content, f"{node_id}-{frappe.scrub(name)}")


def _identify_siblings(children, parent_id):
	"""Number each child among its same-named siblings, so a block of another type
	inserted beside it does not move it."""
	seen = {}
	for child in children:
		name = frappe.scrub(child.get("componentName") or "block")
		seen[name] = seen.get(name, 0) + 1
		_identify(child, f"{parent_id}-{name}{seen[name]}")
