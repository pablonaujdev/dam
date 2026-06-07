from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    jh_product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Productos",
        compute="_compute_jh_product_ids",
        readonly=True,
    )

    @api.depends("move_ids_without_package.product_id")
    def _compute_jh_product_ids(self):
        for picking in self:
            picking.jh_product_ids = (
                picking.move_ids_without_package.mapped("product_id")
            )