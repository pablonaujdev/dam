{
    "name": "DAM Website Site Porter",
    "summary": "Export and import full Odoo 17 websites in one file",
    "description": """
Single-shot export/import for a complete website:
- all website pages and routes (website.page)
- website-specific views
- website menus
- website assets and attachments
- website design/configuration fields
    """,
    "author": "DAM",
    "website": "https://www.dammad.es",
    "category": "Website",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "security/ir.model.access.csv",
        "views/website_site_transfer_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
}

