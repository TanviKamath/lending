
# safe_exec blocks str.format and _(), and cannot import lending. So this script only
# bridges: every value arrives already formatted and translated from the data layer.
data.update(frappe.call("lending.portal_applications.get_documents_page"))  # noqa: F821
data.update(frappe.call("lending.portal_applications.get_document_choices"))  # noqa: F821
