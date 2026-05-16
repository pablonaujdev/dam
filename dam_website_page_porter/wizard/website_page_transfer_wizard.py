import base64
import io
import json
import re
import zipfile
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WebsitePageTransferWizard(models.TransientModel):
    _name = "website.page.transfer.wizard"
    _description = "Website Page Export/Import"

    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        default=lambda self: self._default_website_id(),
    )
    page_id = fields.Many2one("website.page", string="Page to Export")
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
    target_page_id = fields.Many2one("website.page", string="Target Page (optional)")
    overwrite_existing = fields.Boolean(string="Overwrite Existing Page", default=True)
    create_if_missing = fields.Boolean(string="Create Page if Missing", default=True)
    log_message = fields.Text(string="Result", readonly=True)

    @api.model
    def _default_website_id(self):
        website = self.env["website"].get_current_website(fallback=False)
        if website:
            return website.id
        return self.env["website"].search([], limit=1).id

    @api.onchange("website_id")
    def _onchange_website_id(self):
        for wizard in self:
            if wizard.page_id and wizard.page_id.website_id and wizard.page_id.website_id != wizard.website_id:
                wizard.page_id = False
            if wizard.target_page_id and wizard.target_page_id.website_id and wizard.target_page_id.website_id != wizard.website_id:
                wizard.target_page_id = False

    def action_export_page(self):
        self.ensure_one()
        if not self.page_id:
            raise UserError(_("Select a page to export."))

        page = self.page_id.with_context(website_id=self.website_id.id)
        payload = self._build_export_payload(page)
        payload_json = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

        extension = "json"
        output_bytes = payload_json
        if self.export_format == "zip":
            extension = "zip"
            out = io.BytesIO()
            with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr("website_page_payload.json", payload_json)
            output_bytes = out.getvalue()

        filename = self._build_filename(page.url, extension)
        self.write(
            {
                "export_file": base64.b64encode(output_bytes),
                "export_filename": filename,
                "log_message": _(
                    "Export completed: %(name)s (%(count)s attachments).",
                    name=filename,
                    count=len(payload.get("attachments", [])),
                ),
            }
        )
        return self._reload_wizard_action()

    def action_import_page(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Upload a file to import."))

        payload = self._parse_import_payload()
        page, created = self._import_payload(payload)
        self.write(
            {
                "log_message": _(
                    "Import completed. Page %(mode)s: %(url)s",
                    mode="created" if created else "updated",
                    url=page.url,
                )
            }
        )
        return self._reload_wizard_action()

    def _reload_wizard_action(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Website Page Export/Import"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _build_export_payload(self, page):
        page.ensure_one()
        website = self.website_id
        view = page.view_id.with_context(website_id=website.id)
        arch_db = view.with_context(lang=None).arch_db or ""
        attachments = self._get_export_attachments(page, arch_db)

        return {
            "meta": {
                "tool": "dam_website_page_porter",
                "format_version": 1,
                "exported_at": fields.Datetime.to_string(fields.Datetime.now()),
            },
            "website": {
                "name": website.name,
                "source_website_id": page.website_id.id or False,
            },
            "page": {
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
            },
            "view": {
                "name": view.name,
                "key": view.key,
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
                "arch_db": arch_db,
            },
            "menus": [
                {
                    "name": menu.name,
                    "url": menu.url,
                    "sequence": menu.sequence,
                    "new_window": menu.new_window,
                }
                for menu in page.menu_ids.filtered(lambda m: m.website_id == website)
            ],
            "attachments": [self._serialize_attachment(attachment) for attachment in attachments],
        }

    def _get_export_attachments(self, page, arch_db):
        Attachment = self.env["ir.attachment"].sudo().with_context(active_test=False)
        website_id = self.website_id.id
        attachments = Attachment.search(
            [
                ("res_model", "=", "ir.ui.view"),
                ("res_id", "=", page.view_id.id),
                ("website_id", "in", (False, website_id)),
            ]
        )

        referenced_ids = self._extract_attachment_ids("%s %s" % (arch_db or "", page.view_id.website_meta_og_img or ""))
        if referenced_ids:
            attachments |= Attachment.search(
                [
                    ("id", "in", list(referenced_ids)),
                    ("website_id", "in", (False, website_id)),
                ]
            )
        return attachments.filtered(lambda att: att.type in ("binary", "url"))

    def _serialize_attachment(self, attachment):
        datas_value = attachment.datas if attachment.type == "binary" else False
        if isinstance(datas_value, bytes):
            datas_value = datas_value.decode()
        return {
            "id": attachment.id,
            "name": attachment.name,
            "type": attachment.type,
            "mimetype": attachment.mimetype,
            "public": attachment.public,
            "key": attachment.key,
            "url": attachment.url,
            "datas": datas_value,
        }

    def _parse_import_payload(self):
        binary = base64.b64decode(self.import_file)
        filename = (self.import_filename or "").lower()
        is_zip = filename.endswith(".zip") or binary[:2] == b"PK"
        if is_zip:
            with zipfile.ZipFile(io.BytesIO(binary), "r") as zip_file:
                json_name = next((name for name in zip_file.namelist() if name.endswith(".json")), None)
                if not json_name:
                    raise ValidationError(_("ZIP file does not include a JSON payload."))
                content = zip_file.read(json_name)
        else:
            content = binary

        try:
            payload = json.loads(content.decode("utf-8"))
        except Exception as exc:
            raise ValidationError(_("Invalid payload file: %s") % exc) from exc

        required_keys = {"page", "view"}
        if not required_keys.issubset(payload):
            raise ValidationError(_("Payload must include: %s") % ", ".join(sorted(required_keys)))
        return payload

    def _import_payload(self, payload):
        website = self.website_id
        page_payload = payload["page"]
        view_payload = payload["view"]
        menus_payload = payload.get("menus", [])
        has_menus_key = "menus" in payload
        attachments_payload = payload.get("attachments", [])

        target_page = self.target_page_id.with_context(website_id=website.id)
        source_url = self._normalize_page_url(page_payload.get("url"))
        if not target_page and source_url:
            target_page = self.env["website.page"].with_context(website_id=website.id).search(
                [
                    ("url", "=", source_url),
                    "|",
                    ("website_id", "=", False),
                    ("website_id", "=", website.id),
                ],
                order="website_id desc, id desc",
                limit=1,
            )

        if target_page and not self.overwrite_existing:
            raise UserError(_("Target page already exists and overwrite is disabled."))

        if not target_page and not self.create_if_missing:
            raise UserError(_("No target page was found and create-if-missing is disabled."))

        created = False
        if target_page:
            if not target_page.website_id:
                target_page.view_id.with_context(website_id=website.id).sudo().write({"name": target_page.view_id.name})
                target_page = self.env["website.page"].with_context(website_id=website.id).sudo().search(
                    [("key", "=", target_page.key), ("website_id", "=", website.id)],
                    limit=1,
                ) or self.env["website.page"].with_context(website_id=website.id).sudo().search(
                    [("url", "=", source_url), ("website_id", "=", website.id)],
                    limit=1,
                )
                if not target_page:
                    raise UserError(_("Could not resolve a website-specific page for import."))
            view = target_page.view_id.with_context(website_id=website.id)
        else:
            view_vals = self._prepare_view_values(view_payload, website, create_mode=True)
            view = self.env["ir.ui.view"].with_context(website_id=website.id, no_cow=True).sudo().create(view_vals)
            page_vals = self._prepare_page_values(page_payload)
            page_vals.update({"website_id": website.id, "view_id": view.id})
            target_page = self.env["website.page"].with_context(website_id=website.id, no_cow=True).sudo().create(page_vals)
            created = True

        id_map = self._import_attachments(attachments_payload, website, view)
        arch_db = self._remap_attachment_references(view_payload.get("arch_db"), id_map)
        website_meta_og_img = self._remap_attachment_references(view_payload.get("website_meta_og_img"), id_map)

        view_values = self._prepare_view_values(
            {**view_payload, "arch_db": arch_db, "website_meta_og_img": website_meta_og_img},
            website,
            create_mode=False,
        )
        page_values = self._prepare_page_values(page_payload)

        view.with_context(website_id=website.id).sudo().write(view_values)
        target_page.with_context(website_id=website.id).sudo().write(page_values)

        if has_menus_key:
            target_page.menu_ids.filtered(lambda m: m.website_id == website).sudo().unlink()
            for menu_data in menus_payload:
                self.env["website.menu"].sudo().create(
                    {
                        "name": menu_data.get("name") or target_page.name,
                        "url": target_page.url,
                        "sequence": menu_data.get("sequence") or 10,
                        "new_window": bool(menu_data.get("new_window")),
                        "parent_id": website.menu_id.id,
                        "page_id": target_page.id,
                        "website_id": website.id,
                    }
                )

        return target_page, created

    def _prepare_view_values(self, view_payload, website, create_mode=False):
        inherit_key = view_payload.get("inherit_key")
        inherit_id = False
        if inherit_key:
            inherit_id = self.env["ir.ui.view"].with_context(active_test=False).search(
                [
                    ("key", "=", inherit_key),
                    ("website_id", "in", (False, website.id)),
                ],
                order="website_id desc, id desc",
                limit=1,
            ).id

        values = {
            "name": view_payload.get("name") or "Imported Page View",
            "type": view_payload.get("type") or "qweb",
            "priority": view_payload.get("priority") or 16,
            "mode": view_payload.get("mode") or "primary",
            "active": bool(view_payload.get("active", True)),
            "track": bool(view_payload.get("track")),
            "visibility": view_payload.get("visibility") or "",
            "website_meta_title": view_payload.get("website_meta_title"),
            "website_meta_description": view_payload.get("website_meta_description"),
            "website_meta_keywords": view_payload.get("website_meta_keywords"),
            "website_meta_og_img": view_payload.get("website_meta_og_img"),
            "seo_name": view_payload.get("seo_name"),
            "arch_db": view_payload.get("arch_db") or "",
            "website_id": website.id,
            "inherit_id": inherit_id,
        }

        if create_mode:
            values["key"] = self._get_available_view_key(view_payload.get("key"), website)
        elif view_payload.get("key"):
            values["key"] = view_payload.get("key")

        if "visibility_password" in view_payload:
            values["visibility_password"] = view_payload.get("visibility_password") or False
        return values

    def _get_available_view_key(self, key, website):
        base_key = key or "website.imported_page"
        View = self.env["ir.ui.view"].sudo().with_context(active_test=False)
        candidate = base_key
        suffix = 1
        while View.search_count([("key", "=", candidate), ("website_id", "in", (False, website.id))]):
            candidate = "%s-%s" % (base_key, suffix)
            suffix += 1
        return candidate

    def _prepare_page_values(self, page_payload):
        date_publish = page_payload.get("date_publish")
        return {
            "name": page_payload.get("name") or "Imported Page",
            "url": self._normalize_page_url(page_payload.get("url")),
            "website_indexed": bool(page_payload.get("website_indexed", True)),
            "is_published": bool(page_payload.get("is_published")),
            "date_publish": date_publish or False,
            "header_overlay": bool(page_payload.get("header_overlay")),
            "header_color": page_payload.get("header_color"),
            "header_text_color": page_payload.get("header_text_color"),
            "header_visible": bool(page_payload.get("header_visible", True)),
            "footer_visible": bool(page_payload.get("footer_visible", True)),
        }

    def _import_attachments(self, attachments_payload, website, view):
        Attachment = self.env["ir.attachment"].sudo().with_context(active_test=False)
        Attachment.search(
            [
                ("res_model", "=", "ir.ui.view"),
                ("res_id", "=", view.id),
                ("website_id", "in", (False, website.id)),
            ]
        ).unlink()

        id_map = {}
        for attachment_data in attachments_payload:
            source_id = str(attachment_data.get("id") or "")
            values = {
                "name": attachment_data.get("name") or "Imported Attachment",
                "type": attachment_data.get("type") or "binary",
                "public": bool(attachment_data.get("public", True)),
                "mimetype": attachment_data.get("mimetype") or False,
                "key": attachment_data.get("key") or False,
                "website_id": website.id,
                "res_model": "ir.ui.view",
                "res_id": view.id,
            }
            if values["type"] == "binary":
                datas_value = attachment_data.get("datas")
                if not datas_value:
                    continue
                values["datas"] = datas_value
            else:
                values["url"] = attachment_data.get("url")

            attachment = Attachment.create(values)
            if source_id:
                id_map[source_id] = str(attachment.id)
        return id_map

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

        def _path_replace(match):
            original_id = match.group(2)
            return "%s%s" % (match.group(1), id_map.get(original_id, original_id))

        remapped = path_regex.sub(_path_replace, raw_text)

        query_regex = re.compile(r"/web/(?:image|content)\?[^\"'\s<>]+")

        def _query_replace(match):
            url_fragment = match.group(0)
            parsed = urlparse(url_fragment)
            query_values = parse_qs(parsed.query, keep_blank_values=True)
            current_id = (query_values.get("id") or [False])[0]
            model_name = (query_values.get("model") or [False])[0]
            if not current_id or current_id not in id_map:
                return url_fragment
            if model_name and model_name != "ir.attachment":
                return url_fragment
            query_values["id"] = [id_map[current_id]]
            new_query = urlencode(query_values, doseq=True)
            return urlunparse(parsed._replace(query=new_query))

        return query_regex.sub(_query_replace, remapped)

    def _normalize_page_url(self, url):
        clean_url = (url or "/").strip()
        if not clean_url:
            clean_url = "/"
        if not clean_url.startswith("/"):
            clean_url = "/%s" % clean_url
        return clean_url

    def _build_filename(self, page_url, extension):
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (page_url or "page").strip("/"))
        slug = slug or "home"
        return "website_page_%s.%s" % (slug, extension)
