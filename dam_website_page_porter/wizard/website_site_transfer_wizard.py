import base64
import io
import json
import re
import zipfile
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WebsiteSiteTransferWizard(models.TransientModel):
    _name = "website.site.transfer.wizard"
    _description = "Website Full Site Export/Import"

    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        default=lambda self: self._default_website_id(),
    )
    export_format = fields.Selection(
        [("json", "JSON"), ("zip", "ZIP")],
        string="Export Format",
        required=True,
        default="zip",
    )
    export_file = fields.Binary(string="Export File", readonly=True, attachment=False)
    export_filename = fields.Char(string="Export Filename", readonly=True)

    import_file = fields.Binary(string="Import File", attachment=False)
    import_filename = fields.Char(string="Import Filename")

    preserve_domain = fields.Boolean(
        string="Preserve Destination Domain",
        default=True,
        help="Keep the current target domain instead of replacing it with the source one.",
    )
    overwrite_pages = fields.Boolean(string="Overwrite Pages", default=True)
    overwrite_menus = fields.Boolean(string="Overwrite Menus", default=True)
    overwrite_views = fields.Boolean(string="Overwrite Views", default=True)
    overwrite_assets = fields.Boolean(string="Overwrite Assets", default=True)
    overwrite_attachments = fields.Boolean(string="Overwrite Attachments", default=True)
    log_message = fields.Text(string="Result", readonly=True)

    @api.model
    def _default_website_id(self):
        website = self.env["website"].get_current_website(fallback=False)
        if website:
            return website.id
        return self.env["website"].search([], limit=1).id

    def action_export_site(self):
        self.ensure_one()
        website = self.website_id
        if not website:
            raise UserError(_("Select a website to export."))

        payload = self._build_export_payload(website)
        payload_json = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        extension = "json"
        output_bytes = payload_json
        if self.export_format == "zip":
            extension = "zip"
            out = io.BytesIO()
            with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr("website_site_payload.json", payload_json)
            output_bytes = out.getvalue()

        filename = "website_full_%s.%s" % (website.id, extension)
        self.write(
            {
                "export_file": base64.b64encode(output_bytes),
                "export_filename": filename,
                "log_message": _(
                    "Export completed: %(file)s (pages=%(pages)s, views=%(views)s, assets=%(assets)s, attachments=%(atts)s).",
                    file=filename,
                    pages=len(payload.get("pages", [])),
                    views=len(payload.get("views", [])),
                    assets=len(payload.get("assets", [])),
                    atts=len(payload.get("attachments", [])),
                ),
            }
        )
        return self._reload_wizard_action()

    def action_import_site(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Upload the website export file first."))

        payload = self._parse_payload_file()
        stats = self._import_payload(payload)
        self.write(
            {
                "log_message": _(
                    "Import completed (website=%(website)s, views=%(views)s, pages=%(pages)s, menus=%(menus)s, assets=%(assets)s, attachments=%(atts)s).",
                    website=self.website_id.name,
                    views=stats["views"],
                    pages=stats["pages"],
                    menus=stats["menus"],
                    assets=stats["assets"],
                    atts=stats["attachments"],
                )
            }
        )
        return self._reload_wizard_action()

    def _reload_wizard_action(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Website Full Export/Import"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _build_export_payload(self, website):
        pages = self._export_pages(website)
        views = self._export_views(website)
        assets = self._export_assets(website)
        menus = self._export_menus(website)
        website_values = self._export_website_values(website)
        attachments = self._export_attachments(website, views, menus, website_values)

        return {
            "meta": {
                "tool": "dam_website_site_porter",
                "format_version": 1,
                "exported_at": fields.Datetime.to_string(fields.Datetime.now()),
            },
            "website": website_values,
            "views": views,
            "pages": pages,
            "menus": menus,
            "assets": assets,
            "attachments": attachments,
        }

    def _export_website_values(self, website):
        def _to_text(binary_value):
            if isinstance(binary_value, bytes):
                return binary_value.decode()
            return binary_value

        return {
            "source_website_id": website.id,
            "name": website.name,
            "domain": website.domain,
            "homepage_url": website.homepage_url,
            "custom_code_head": website.custom_code_head,
            "custom_code_footer": website.custom_code_footer,
            "cookies_bar": website.cookies_bar,
            "auto_redirect_lang": website.auto_redirect_lang,
            "auth_signup_uninvited": website.auth_signup_uninvited,
            "cdn_activated": website.cdn_activated,
            "cdn_url": website.cdn_url,
            "cdn_filters": website.cdn_filters,
            "google_analytics_key": website.google_analytics_key,
            "google_search_console": website.google_search_console,
            "google_maps_api_key": website.google_maps_api_key,
            "plausible_shared_key": website.plausible_shared_key,
            "plausible_site": website.plausible_site,
            "robots_txt": website.sudo().robots_txt,
            "social_twitter": website.social_twitter,
            "social_facebook": website.social_facebook,
            "social_github": website.social_github,
            "social_linkedin": website.social_linkedin,
            "social_youtube": website.social_youtube,
            "social_instagram": website.social_instagram,
            "social_tiktok": website.social_tiktok,
            "logo": _to_text(website.logo),
            "favicon": _to_text(website.favicon),
            "social_default_image": _to_text(website.social_default_image),
            "theme_module": website.theme_id.name if website.theme_id else False,
        }

    def _export_pages(self, website):
        pages = website.with_context(website_id=website.id)._get_website_pages(
            domain=[("url", "!=", False)],
            order="id",
        )
        result = []
        for page in pages:
            result.append(
                {
                    "source_id": page.id,
                    "key": page.key,
                    "view_key": page.view_id.key,
                    "view_source_id": page.view_id.id,
                    "name": page.name,
                    "url": page.url,
                    "website_indexed": page.website_indexed,
                    "is_published": page.is_published,
                    "date_publish": fields.Datetime.to_string(page.date_publish) if page.date_publish else False,
                    "header_overlay": page.header_overlay,
                    "header_color": page.header_color,
                    "header_text_color": page.header_text_color,
                    "header_visible": page.header_visible,
                    "footer_visible": page.footer_visible,
                }
            )
        return result

    def _export_views(self, website):
        views = self.env["ir.ui.view"].sudo().with_context(active_test=False).search(
            [("website_id", "=", website.id)],
            order="id",
        )
        result = []
        for view in views:
            result.append(
                {
                    "source_id": view.id,
                    "key": view.key,
                    "name": view.name,
                    "type": view.type or "qweb",
                    "priority": view.priority,
                    "mode": view.mode,
                    "active": view.active,
                    "track": view.track,
                    "visibility": view.visibility,
                    "visibility_password": view.sudo().visibility_password,
                    "website_meta_title": view.website_meta_title,
                    "website_meta_description": view.website_meta_description,
                    "website_meta_keywords": view.website_meta_keywords,
                    "website_meta_og_img": view.website_meta_og_img,
                    "seo_name": view.seo_name,
                    "inherit_key": view.inherit_id.key if view.inherit_id else False,
                    "arch_db": view.with_context(lang=None).arch_db or "",
                }
            )
        return result

    def _export_assets(self, website):
        assets = self.env["ir.asset"].sudo().with_context(active_test=False).search(
            [("website_id", "=", website.id)],
            order="sequence, id",
        )
        result = []
        for asset in assets:
            result.append(
                {
                    "source_id": asset.id,
                    "key": asset.key,
                    "name": asset.name,
                    "bundle": asset.bundle,
                    "directive": asset.directive,
                    "path": asset.path,
                    "target": asset.target,
                    "active": asset.active,
                    "sequence": asset.sequence,
                }
            )
        return result

    def _export_menus(self, website):
        menus = self.env["website.menu"].sudo().with_context(active_test=False).search(
            [("website_id", "=", website.id)],
            order="parent_path, sequence, id",
        )
        result = []
        for menu in menus:
            result.append(
                {
                    "source_id": menu.id,
                    "parent_source_id": menu.parent_id.id or False,
                    "name": menu.name,
                    "url": menu.url,
                    "page_url": menu.page_id.url if menu.page_id else False,
                    "new_window": menu.new_window,
                    "sequence": menu.sequence,
                    "mega_menu_content": menu.mega_menu_content,
                    "mega_menu_classes": menu.mega_menu_classes,
                }
            )
        return result

    def _export_attachments(self, website, views_payload, menus_payload, website_values):
        Attachment = self.env["ir.attachment"].sudo().with_context(active_test=False)
        view_ids = [view["source_id"] for view in views_payload]
        attachments = Attachment.search([("website_id", "=", website.id)])
        if view_ids:
            attachments |= Attachment.search(
                [("res_model", "=", "ir.ui.view"), ("res_id", "in", view_ids)]
            )

        referenced_ids = set()
        for view in views_payload:
            referenced_ids |= self._extract_attachment_ids(
                "%s %s" % ((view.get("arch_db") or ""), (view.get("website_meta_og_img") or ""))
            )
        for menu in menus_payload:
            referenced_ids |= self._extract_attachment_ids(
                "%s %s" % ((menu.get("url") or ""), (menu.get("mega_menu_content") or ""))
            )
        referenced_ids |= self._extract_attachment_ids(
            "%s %s" % ((website_values.get("custom_code_head") or ""), (website_values.get("custom_code_footer") or ""))
        )
        if referenced_ids:
            attachments |= Attachment.search([("id", "in", list(referenced_ids))])

        serialized = [self._serialize_attachment(att) for att in attachments]
        serialized.sort(key=lambda item: item["source_id"])
        return serialized

    def _serialize_attachment(self, attachment):
        datas_value = attachment.datas if attachment.type == "binary" else False
        if isinstance(datas_value, bytes):
            datas_value = datas_value.decode()
        return {
            "source_id": attachment.id,
            "name": attachment.name,
            "type": attachment.type,
            "mimetype": attachment.mimetype,
            "public": attachment.public,
            "key": attachment.key,
            "url": attachment.url,
            "datas": datas_value,
            "res_model": attachment.res_model,
            "res_id": attachment.res_id,
            "res_field": attachment.res_field,
            "website_id": attachment.website_id.id if attachment.website_id else False,
        }

    def _parse_payload_file(self):
        binary = base64.b64decode(self.import_file)
        filename = (self.import_filename or "").lower()
        is_zip = filename.endswith(".zip") or binary[:2] == b"PK"
        if is_zip:
            with zipfile.ZipFile(io.BytesIO(binary), "r") as zip_file:
                json_name = next((name for name in zip_file.namelist() if name.endswith(".json")), None)
                if not json_name:
                    raise ValidationError(_("ZIP file does not contain a JSON payload."))
                content = zip_file.read(json_name)
        else:
            content = binary

        try:
            payload = json.loads(content.decode("utf-8"))
        except Exception as exc:
            raise ValidationError(_("Invalid payload file: %s") % exc) from exc

        required = {"website", "views", "pages", "menus", "assets", "attachments"}
        if not required.issubset(payload):
            raise ValidationError(_("Payload missing required sections: %s") % ", ".join(sorted(required - set(payload))))
        return payload

    def _import_payload(self, payload):
        website = self.website_id.sudo()
        self._import_website_values(website, payload["website"])
        view_map = self._import_views(website, payload.get("views", []))
        page_map = self._import_pages(website, payload.get("pages", []), view_map)
        menus_count = self._import_menus(website, payload.get("menus", []), page_map)
        assets_count = self._import_assets(website, payload.get("assets", []))
        attachment_map, attachment_count = self._import_attachments(website, payload.get("attachments", []), view_map, page_map)
        self._remap_website_references(website, attachment_map)
        self._remap_view_references(view_map, attachment_map)
        self._remap_menu_references(website, attachment_map)

        return {
            "views": len(view_map),
            "pages": len(page_map),
            "menus": menus_count,
            "assets": assets_count,
            "attachments": attachment_count,
        }

    def _import_website_values(self, website, values):
        write_vals = {
            "name": values.get("name"),
            "homepage_url": values.get("homepage_url"),
            "custom_code_head": values.get("custom_code_head"),
            "custom_code_footer": values.get("custom_code_footer"),
            "cookies_bar": bool(values.get("cookies_bar")),
            "auto_redirect_lang": bool(values.get("auto_redirect_lang", True)),
            "auth_signup_uninvited": values.get("auth_signup_uninvited") or "b2b",
            "cdn_activated": bool(values.get("cdn_activated")),
            "cdn_url": values.get("cdn_url"),
            "cdn_filters": values.get("cdn_filters"),
            "google_analytics_key": values.get("google_analytics_key"),
            "google_search_console": values.get("google_search_console"),
            "google_maps_api_key": values.get("google_maps_api_key"),
            "plausible_shared_key": values.get("plausible_shared_key"),
            "plausible_site": values.get("plausible_site"),
            "robots_txt": values.get("robots_txt"),
            "social_twitter": values.get("social_twitter"),
            "social_facebook": values.get("social_facebook"),
            "social_github": values.get("social_github"),
            "social_linkedin": values.get("social_linkedin"),
            "social_youtube": values.get("social_youtube"),
            "social_instagram": values.get("social_instagram"),
            "social_tiktok": values.get("social_tiktok"),
            "logo": values.get("logo") or False,
            "favicon": values.get("favicon") or False,
            "social_default_image": values.get("social_default_image") or False,
        }
        if not self.preserve_domain:
            write_vals["domain"] = values.get("domain")

        theme_module_name = values.get("theme_module")
        if theme_module_name:
            theme = self.env["ir.module.module"].sudo().search([("name", "=", theme_module_name)], limit=1)
            if theme:
                write_vals["theme_id"] = theme.id

        website.with_context(website_id=website.id).write(write_vals)

    def _import_views(self, website, views_payload):
        View = self.env["ir.ui.view"].sudo().with_context(active_test=False)
        source_id_map = {}
        key_map = {}
        payload_by_key = {}
        for view_data in views_payload:
            key = view_data.get("key")
            if key:
                payload_by_key[key] = view_data

        pending = list(views_payload)
        loops = 0
        while pending and loops < (len(views_payload) + 5):
            loops += 1
            next_pending = []
            progressed = False
            for view_data in pending:
                key = view_data.get("key")
                inherit_key = view_data.get("inherit_key")
                inherit_id = False
                if inherit_key:
                    inherit_id = self._resolve_inherit_view(website, inherit_key, key_map)
                    if not inherit_id and inherit_key in payload_by_key:
                        next_pending.append(view_data)
                        continue

                values = {
                    "name": view_data.get("name") or "Imported Website View",
                    "type": view_data.get("type") or "qweb",
                    "priority": view_data.get("priority") or 16,
                    "mode": view_data.get("mode") or "primary",
                    "active": bool(view_data.get("active", True)),
                    "track": bool(view_data.get("track")),
                    "visibility": view_data.get("visibility") or "",
                    "website_meta_title": view_data.get("website_meta_title"),
                    "website_meta_description": view_data.get("website_meta_description"),
                    "website_meta_keywords": view_data.get("website_meta_keywords"),
                    "website_meta_og_img": view_data.get("website_meta_og_img"),
                    "seo_name": view_data.get("seo_name"),
                    "arch_db": view_data.get("arch_db") or "",
                    "website_id": website.id,
                    "inherit_id": inherit_id,
                }
                if "visibility_password" in view_data:
                    values["visibility_password"] = view_data.get("visibility_password") or False
                if key:
                    values["key"] = key

                target = False
                if key:
                    target = View.search(
                        [("key", "=", key), ("website_id", "=", website.id)],
                        limit=1,
                    )

                if target:
                    if self.overwrite_views:
                        target.with_context(website_id=website.id).write(values)
                else:
                    if not key:
                        values["key"] = self._generate_unique_view_key(website, "website.imported_view")
                    target = View.with_context(website_id=website.id, no_cow=True).create(values)

                progressed = True
                source_id = str(view_data.get("source_id") or "")
                if source_id:
                    source_id_map[source_id] = target
                if key:
                    key_map[key] = target

            if not progressed and next_pending:
                # Break cycles or unresolved parents by creating without inherit_id,
                # then we will patch inherit_id in a second pass.
                for view_data in next_pending:
                    key = view_data.get("key")
                    values = {
                        "name": view_data.get("name") or "Imported Website View",
                        "type": view_data.get("type") or "qweb",
                        "priority": view_data.get("priority") or 16,
                        "mode": view_data.get("mode") or "primary",
                        "active": bool(view_data.get("active", True)),
                        "track": bool(view_data.get("track")),
                        "visibility": view_data.get("visibility") or "",
                        "website_meta_title": view_data.get("website_meta_title"),
                        "website_meta_description": view_data.get("website_meta_description"),
                        "website_meta_keywords": view_data.get("website_meta_keywords"),
                        "website_meta_og_img": view_data.get("website_meta_og_img"),
                        "seo_name": view_data.get("seo_name"),
                        "arch_db": view_data.get("arch_db") or "",
                        "website_id": website.id,
                    }
                    if "visibility_password" in view_data:
                        values["visibility_password"] = view_data.get("visibility_password") or False
                    if key:
                        values["key"] = key

                    target = False
                    if key:
                        target = View.search(
                            [("key", "=", key), ("website_id", "=", website.id)],
                            limit=1,
                        )
                    if target:
                        if self.overwrite_views:
                            target.with_context(website_id=website.id).write(values)
                    else:
                        if not key:
                            values["key"] = self._generate_unique_view_key(website, "website.imported_view")
                        target = View.with_context(website_id=website.id, no_cow=True).create(values)

                    source_id = str(view_data.get("source_id") or "")
                    if source_id:
                        source_id_map[source_id] = target
                    if key:
                        key_map[key] = target
                break

            pending = next_pending

        # Second pass to patch inherit_id for all views where possible.
        for view_data in views_payload:
            key = view_data.get("key")
            inherit_key = view_data.get("inherit_key")
            if not (key and inherit_key and key in key_map):
                continue
            inherit_target = self._resolve_inherit_view(website, inherit_key, key_map)
            if inherit_target and key_map[key].inherit_id.id != inherit_target:
                key_map[key].with_context(website_id=website.id).write({"inherit_id": inherit_target})

        if self.overwrite_views:
            imported_ids = [view.id for view in source_id_map.values()]
            stale_views = View.search([("website_id", "=", website.id), ("id", "not in", imported_ids)])
            stale_views.write({"active": False})

        return source_id_map

    def _resolve_inherit_view(self, website, inherit_key, key_map):
        if inherit_key in key_map:
            return key_map[inherit_key].id
        match = self.env["ir.ui.view"].sudo().with_context(active_test=False).search(
            [("key", "=", inherit_key), ("website_id", "in", (False, website.id))],
            order="website_id desc, id desc",
            limit=1,
        )
        return match.id if match else False

    def _generate_unique_view_key(self, website, base_key):
        View = self.env["ir.ui.view"].sudo().with_context(active_test=False)
        candidate = base_key
        index = 1
        while View.search_count([("key", "=", candidate), ("website_id", "in", (False, website.id))]):
            candidate = "%s_%s" % (base_key, index)
            index += 1
        return candidate

    def _import_pages(self, website, pages_payload, view_map):
        Page = self.env["website.page"].sudo().with_context(active_test=False, website_id=website.id)
        page_map = {}
        imported_ids = []
        for page_data in pages_payload:
            view_key = page_data.get("view_key")
            target_view = False
            if view_key:
                target_view = self.env["ir.ui.view"].sudo().with_context(active_test=False).search(
                    [("key", "=", view_key), ("website_id", "in", (False, website.id))],
                    order="website_id desc, id desc",
                    limit=1,
                )
            if not target_view:
                source_view_id = str(page_data.get("view_source_id") or "")
                target_view = view_map.get(source_view_id)
            if not target_view:
                continue

            vals = {
                "name": page_data.get("name") or "Imported Page",
                "url": self._normalize_url(page_data.get("url")),
                "website_id": website.id,
                "view_id": target_view.id,
                "website_indexed": bool(page_data.get("website_indexed", True)),
                "is_published": bool(page_data.get("is_published")),
                "date_publish": page_data.get("date_publish") or False,
                "header_overlay": bool(page_data.get("header_overlay")),
                "header_color": page_data.get("header_color"),
                "header_text_color": page_data.get("header_text_color"),
                "header_visible": bool(page_data.get("header_visible", True)),
                "footer_visible": bool(page_data.get("footer_visible", True)),
            }

            target_page = False
            key = page_data.get("key")
            if key:
                target_page = Page.search([("key", "=", key), ("website_id", "=", website.id)], limit=1)
            if not target_page:
                target_page = Page.search([("url", "=", vals["url"]), ("website_id", "=", website.id)], limit=1)

            if target_page:
                if self.overwrite_pages:
                    target_page.with_context(website_id=website.id).write(vals)
            else:
                target_page = Page.with_context(website_id=website.id, no_cow=True).create(vals)

            source_id = str(page_data.get("source_id") or "")
            if source_id:
                page_map[source_id] = target_page
            imported_ids.append(target_page.id)

        if self.overwrite_pages and imported_ids:
            stale_pages = Page.search([("website_id", "=", website.id), ("id", "not in", imported_ids)])
            stale_pages.unlink()

        return page_map

    def _import_menus(self, website, menus_payload, page_map):
        if not self.overwrite_menus:
            return 0

        Menu = self.env["website.menu"].sudo().with_context(active_test=False, website_id=website.id)
        root_menu = website.menu_id
        Menu.search([("website_id", "=", website.id), ("id", "!=", root_menu.id)]).unlink()

        payload_by_source = {str(item["source_id"]): item for item in menus_payload if item.get("source_id")}
        created = {}

        # Determine source root menu and update destination root with it.
        source_root = next((item for item in menus_payload if not item.get("parent_source_id")), False)
        if source_root:
            root_menu.write(
                {
                    "name": source_root.get("name") or root_menu.name,
                    "url": source_root.get("url") or root_menu.url,
                    "new_window": bool(source_root.get("new_window")),
                    "sequence": source_root.get("sequence") or root_menu.sequence,
                    "mega_menu_content": source_root.get("mega_menu_content") or False,
                    "mega_menu_classes": source_root.get("mega_menu_classes") or False,
                }
            )
            created[str(source_root["source_id"])] = root_menu

        pending = [item for item in menus_payload if str(item.get("source_id")) not in created]
        loops = 0
        while pending and loops < (len(menus_payload) + 5):
            loops += 1
            next_pending = []
            progressed = False
            for menu_data in pending:
                source_id = str(menu_data.get("source_id") or "")
                parent_source = str(menu_data.get("parent_source_id") or "")
                parent_menu = created.get(parent_source) if parent_source else root_menu
                if parent_source and not parent_menu:
                    next_pending.append(menu_data)
                    continue

                page_target = False
                page_url = self._normalize_url(menu_data.get("page_url")) if menu_data.get("page_url") else False
                if page_url:
                    page_target = self.env["website.page"].sudo().with_context(website_id=website.id).search(
                        [("url", "=", page_url), ("website_id", "=", website.id)],
                        limit=1,
                    )
                vals = {
                    "name": menu_data.get("name") or "Menu",
                    "url": menu_data.get("url") or "",
                    "new_window": bool(menu_data.get("new_window")),
                    "sequence": menu_data.get("sequence") or 10,
                    "parent_id": parent_menu.id if parent_menu else root_menu.id,
                    "website_id": website.id,
                    "page_id": page_target.id if page_target else False,
                    "mega_menu_content": menu_data.get("mega_menu_content") or False,
                    "mega_menu_classes": menu_data.get("mega_menu_classes") or False,
                }
                new_menu = Menu.create(vals)
                if source_id:
                    created[source_id] = new_menu
                progressed = True

            if not progressed:
                for menu_data in next_pending:
                    source_id = str(menu_data.get("source_id") or "")
                    vals = {
                        "name": menu_data.get("name") or "Menu",
                        "url": menu_data.get("url") or "",
                        "new_window": bool(menu_data.get("new_window")),
                        "sequence": menu_data.get("sequence") or 10,
                        "parent_id": root_menu.id,
                        "website_id": website.id,
                        "mega_menu_content": menu_data.get("mega_menu_content") or False,
                        "mega_menu_classes": menu_data.get("mega_menu_classes") or False,
                    }
                    new_menu = Menu.create(vals)
                    if source_id:
                        created[source_id] = new_menu
                break
            pending = next_pending

        return len(created)

    def _import_assets(self, website, assets_payload):
        Asset = self.env["ir.asset"].sudo().with_context(active_test=False)
        imported_ids = []
        for asset_data in assets_payload:
            key = asset_data.get("key")
            vals = {
                "name": asset_data.get("name") or "Imported Asset",
                "bundle": asset_data.get("bundle"),
                "directive": asset_data.get("directive") or "append",
                "path": asset_data.get("path"),
                "target": asset_data.get("target"),
                "active": bool(asset_data.get("active", True)),
                "sequence": asset_data.get("sequence") or 16,
                "website_id": website.id,
                "key": key or False,
            }
            target = False
            if key:
                target = Asset.search([("key", "=", key), ("website_id", "=", website.id)], limit=1)
            if target:
                if self.overwrite_assets:
                    target.write(vals)
            else:
                target = Asset.create(vals)
            imported_ids.append(target.id)

        if self.overwrite_assets:
            stale_assets = Asset.search([("website_id", "=", website.id), ("id", "not in", imported_ids)])
            stale_assets.unlink()

        return len(imported_ids)

    def _import_attachments(self, website, attachments_payload, view_map, page_map):
        if not self.overwrite_attachments:
            return {}, 0

        Attachment = self.env["ir.attachment"].sudo().with_context(active_test=False)
        Attachment.search([("website_id", "=", website.id)]).unlink()

        id_map = {}
        created_count = 0
        for att_data in attachments_payload:
            vals = {
                "name": att_data.get("name") or "Imported Attachment",
                "type": att_data.get("type") or "binary",
                "public": bool(att_data.get("public", True)),
                "mimetype": att_data.get("mimetype") or False,
                "key": att_data.get("key") or False,
                "website_id": website.id,
                "res_field": att_data.get("res_field") or False,
            }
            res_model = att_data.get("res_model")
            res_id = att_data.get("res_id")
            if res_model == "ir.ui.view":
                mapped = view_map.get(str(res_id or ""))
                if mapped:
                    vals["res_model"] = "ir.ui.view"
                    vals["res_id"] = mapped.id
            elif res_model == "website.page":
                mapped = page_map.get(str(res_id or ""))
                if mapped:
                    vals["res_model"] = "website.page"
                    vals["res_id"] = mapped.id
            elif res_model == "website":
                vals["res_model"] = "website"
                vals["res_id"] = website.id
            elif res_model and res_id:
                vals["res_model"] = res_model
                vals["res_id"] = res_id

            if vals["type"] == "binary":
                datas = att_data.get("datas")
                if not datas:
                    continue
                vals["datas"] = datas
            else:
                vals["url"] = att_data.get("url")

            new_attachment = Attachment.create(vals)
            created_count += 1
            source_id = str(att_data.get("source_id") or "")
            if source_id:
                id_map[source_id] = str(new_attachment.id)

        return id_map, created_count

    def _remap_website_references(self, website, attachment_map):
        if not attachment_map:
            return
        head = self._remap_attachment_references(website.custom_code_head, attachment_map)
        footer = self._remap_attachment_references(website.custom_code_footer, attachment_map)
        website.with_context(website_id=website.id).write(
            {
                "custom_code_head": head,
                "custom_code_footer": footer,
            }
        )

    def _remap_view_references(self, view_map, attachment_map):
        if not attachment_map:
            return
        for view in view_map.values():
            arch_db = self._remap_attachment_references(view.with_context(lang=None).arch_db, attachment_map)
            og_img = self._remap_attachment_references(view.website_meta_og_img, attachment_map)
            view.write({"arch_db": arch_db, "website_meta_og_img": og_img})

    def _remap_menu_references(self, website, attachment_map):
        if not attachment_map:
            return
        menus = self.env["website.menu"].sudo().search([("website_id", "=", website.id)])
        for menu in menus:
            menu.write(
                {
                    "url": self._remap_attachment_references(menu.url, attachment_map),
                    "mega_menu_content": self._remap_attachment_references(menu.mega_menu_content, attachment_map),
                }
            )

    def _extract_attachment_ids(self, raw_text):
        ids = set()
        if not raw_text:
            return ids

        path_regex = re.compile(r"/web/(?:image|content)/(?:ir\.attachment/)?(\d+)")
        for match in path_regex.finditer(raw_text):
            ids.add(int(match.group(1)))

        query_regex = re.compile(r"/web/(?:image|content)\?[^\"'\s<>]+")
        for match in query_regex.finditer(raw_text):
            parsed = urlparse(match.group(0))
            query_values = parse_qs(parsed.query)
            attachment_id = (query_values.get("id") or [False])[0]
            model_name = (query_values.get("model") or [False])[0]
            if attachment_id and (not model_name or model_name == "ir.attachment"):
                try:
                    ids.add(int(attachment_id))
                except ValueError:
                    continue
        return ids

    def _remap_attachment_references(self, raw_text, id_map):
        if not raw_text or not id_map:
            return raw_text

        path_regex = re.compile(r"(/web/(?:image|content)/(?:ir\.attachment/)?)(\d+)")

        def _replace_path(match):
            old_id = match.group(2)
            return "%s%s" % (match.group(1), id_map.get(old_id, old_id))

        remapped = path_regex.sub(_replace_path, raw_text)
        query_regex = re.compile(r"/web/(?:image|content)\?[^\"'\s<>]+")

        def _replace_query(match):
            fragment = match.group(0)
            parsed = urlparse(fragment)
            query_values = parse_qs(parsed.query, keep_blank_values=True)
            attachment_id = (query_values.get("id") or [False])[0]
            model_name = (query_values.get("model") or [False])[0]
            if not attachment_id or attachment_id not in id_map:
                return fragment
            if model_name and model_name != "ir.attachment":
                return fragment
            query_values["id"] = [id_map[attachment_id]]
            return urlunparse(parsed._replace(query=urlencode(query_values, doseq=True)))

        return query_regex.sub(_replace_query, remapped)

    def _normalize_url(self, url):
        value = (url or "/").strip()
        if not value:
            value = "/"
        if not value.startswith("/"):
            value = "/%s" % value
        return value
