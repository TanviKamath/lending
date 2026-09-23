# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

"""The one rule the portal build has to keep: a rebuild never takes out a hand edit."""

import frappe
from frappe.tests import IntegrationTestCase

from lending.portal.studio_build.blocks import block
from lending.portal.studio_build.merge import identify, merge_blocks, merge_resources


class TestStudioMerge(IntegrationTestCase):
	def test_ids_are_the_same_on_every_run(self):
		first = identify([self.generated()], "/overview")
		second = identify([self.generated()], "/overview")

		self.assertEqual(self.ids(first), self.ids(second))
		self.assertEqual(first[0]["componentId"], "overview-0")

	def test_ids_do_not_move_when_another_component_is_added_beside_them(self):
		before = self.ids(identify([self.generated()], "/overview"))

		grown = self.generated()
		grown["children"].insert(0, block("Badge", {"label": "New"}))
		after = self.ids(identify([grown], "/overview"))

		self.assertTrue(set(before) <= set(after))

	def test_a_hand_edited_prop_survives_a_rebuild(self):
		base = identify([self.generated()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))
		live[0]["children"][0]["componentProps"]["label"] = "Renamed by hand"

		new = identify([self.generated(title="Generator's new title")], "/overview")
		merged = merge_blocks(base, live, new)

		self.assertEqual(merged[0]["children"][0]["componentProps"]["label"], "Renamed by hand")

	def test_an_untouched_prop_takes_the_new_value(self):
		base = identify([self.generated()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))

		new = identify([self.generated(title="Generator's new title")], "/overview")
		merged = merge_blocks(base, live, new)

		self.assertEqual(merged[0]["children"][0]["componentProps"]["label"], "Generator's new title")

	def test_a_hand_added_block_survives_a_rebuild(self):
		base = identify([self.generated()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))
		live[0]["children"].append(block("Badge", {"label": "Mine"}, componentId="hand-added"))

		merged = merge_blocks(base, live, identify([self.generated()], "/overview"))

		self.assertIn("hand-added", self.ids(merged))

	def test_a_hand_edited_block_survives_the_generator_dropping_it(self):
		base = identify([self.generated()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))
		live[0]["children"][0]["componentProps"]["label"] = "Kept"

		emptied = identify([block("container", children=[])], "/overview")
		merged = merge_blocks(base, live, emptied)

		self.assertEqual(merged[0]["children"][0]["componentProps"]["label"], "Kept")

	def test_the_generator_may_drop_a_block_nobody_touched(self):
		base = identify([self.generated()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))

		emptied = identify([block("container", children=[])], "/overview")
		merged = merge_blocks(base, live, emptied)

		self.assertEqual(merged[0]["children"], [])

	def test_a_hand_edited_style_survives_a_rebuild(self):
		base = identify([self.generated()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))
		live[0]["baseStyles"]["backgroundColor"] = "pink"

		new = identify([self.generated()], "/overview")
		new[0]["baseStyles"]["gap"] = "2rem"
		merged = merge_blocks(base, live, new)

		self.assertEqual(merged[0]["baseStyles"]["backgroundColor"], "pink")
		self.assertEqual(merged[0]["baseStyles"]["gap"], "2rem")

	def test_a_block_deleted_by_hand_is_not_put_back(self):
		base = identify([self.generated()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))
		live[0]["children"] = []

		merged = merge_blocks(base, live, identify([self.generated()], "/overview"))

		self.assertEqual(merged[0]["children"], [])

	def test_a_hand_added_data_source_survives_a_rebuild(self):
		live = [{"resource_name": "overview", "url": "old"}, {"resource_name": "mine", "url": "custom"}]
		new = [{"resource_name": "overview", "url": "new"}]

		merged = merge_resources(live, new)

		self.assertEqual({row["resource_name"]: row["url"] for row in merged}, {"overview": "new", "mine": "custom"})

	def test_a_hand_edited_slot_survives_a_rebuild(self):
		base = identify([self.with_slot()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))
		live[0]["componentSlots"]["default"]["slotContent"][0]["componentProps"]["label"] = "Kept"

		merged = merge_blocks(base, live, identify([self.with_slot()], "/overview"))

		self.assertEqual(
			merged[0]["componentSlots"]["default"]["slotContent"][0]["componentProps"]["label"], "Kept"
		)

	def test_a_page_that_matches_its_baseline_takes_the_rebuild_whole(self):
		"""What _replace_page buys, and why it overwrites once to buy it.

		A page saved straight from a build has nothing on it the canvas owns, so a
		rebuild is free to write the new tree as it stands -- including a tree of another
		shape, which is the case the merge cannot otherwise handle.
		"""
		base = identify([self.generated()], "/overview")
		live = frappe.parse_json(frappe.as_json(base))

		reshaped = identify([block("container", children=[block("HTML", {"html": "<svg/>"})])], "/overview")
		merged = merge_blocks(base, live, reshaped)

		self.assertEqual(merged, reshaped)

	def test_a_baseline_that_is_not_the_page_strands_the_rebuild(self):
		"""Why the baseline may only ever be what was written to the page.

		Recording what a build *would* have written, against a page it did not write,
		says two things at once that cannot both be acted on: every block on the page was
		added by hand, and every block of the new tree has already been deleted there. So
		the old tree stays and the new one never lands -- here in full, and on a real page
		in patches, one tree stacked on the other wherever their ids happen to meet.
		"""
		live = identify([self.generated()], "/overview")
		new = identify([block("container", children=[block("HTML", {"html": "<svg/>"})])], "/overview")

		merged = merge_blocks(new, live, new)

		self.assertEqual(self.ids(merged), self.ids(live))
		self.assertNotIn("overview-0-html1", self.ids(merged))

	@staticmethod
	def generated(title="Overview"):
		return block(
			"container",
			children=[block("TextBlock", {"label": title}), block("Badge", {"label": "Active"})],
			styles={"display": "flex"},
		)

	@staticmethod
	def with_slot():
		return block(
			"Card",
			slots={"default": {"slotName": "default", "slotContent": [block("TextBlock", {"label": "Hi"})]}},
		)

	def ids(self, blocks):
		found = []
		for node in blocks:
			found.append(node["componentId"])
			found += self.ids(node.get("children") or [])
			for slot in (node.get("componentSlots") or {}).values():
				found += self.ids(slot.get("slotContent") or [])

		return found
