{
    "name": "DAM Website Page Porter",
    "summary": "Export and import full Website pages with images",
    "description": """
Export a Website page from Odoo 17 (content, SEO, visibility and images)
into a JSON/ZIP file, then import it into another page with overwrite.
    """,
    "author": "DAM",
    "website": "https://www.dammad.es",
    "category": "Website",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "security/ir.model.access.csv",
        "views/website_page_transfer_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
}

