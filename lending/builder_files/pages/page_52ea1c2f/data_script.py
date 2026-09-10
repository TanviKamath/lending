
# safe_exec blocks _(), so even this page's static wording comes from the data layer.
data.update(frappe.call("lending.portal_apply.get_track_page"))  # noqa: F821
