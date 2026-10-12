# License AGPL-3. Original customization: Avannubo.
from odoo import fields, models


class aleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    image = fields.Image(related='product_id.image_128', depends=['product_id.image_128', 'product_id.image_variant_128', 'product_id.product_tmpl_id.image_128'], string='Image', readonly=True, store=False, compute_sudo=False, help='Shows the current product image as a thumbnail in document lines and reports.\nChanges to the product image are reflected here; no historical copy is stored.')
