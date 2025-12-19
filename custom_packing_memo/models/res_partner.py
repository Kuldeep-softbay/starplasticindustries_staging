# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


# =========================================================
# CUSTOMER (res.partner)
# =========================================================
class ResPartner(models.Model):
    _inherit = 'res.partner'

    package_type_id = fields.Many2one(
        'stock.package.type',
        string='Preferred Package Type',
        help='Default package type to be used for this customer'
    )

    default_package_qty = fields.Float(
        string='Default Package Quantity',
        help='Default quantity per package for this customer'
    )


# =========================================================
# SALE ORDER
# =========================================================
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_update_lines_package(self):
        """
        When customer changes, update package type on all existing lines
        """
        for order in self:
            for line in order.order_line:
                line.package_type_id = order.partner_id.package_type_id


# =========================================================
# SALE ORDER LINE
# =========================================================
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    package_type_id = fields.Many2one(
        'stock.package.type',
        string='Package Type'
    )

    @api.onchange('product_id')
    def _onchange_product_set_package_type(self):
        """
        When product is selected, auto-fill package type from customer
        """
        for line in self:
            if line.order_id and line.order_id.partner_id:
                line.package_type_id = line.order_id.partner_id.package_type_id


# =========================================================
# STOCK MOVE (SAFE COMPUTE, NO RELATED)
# =========================================================
class StockMove(models.Model):
    _inherit = 'stock.move'

    package_type_id = fields.Many2one(
        'stock.package.type',
        string='Package Type',
        compute='_compute_package_type',
        store=True
    )

    @api.depends('sale_line_id.package_type_id')
    def _compute_package_type(self):
        for move in self:
            move.package_type_id = move.sale_line_id.package_type_id
