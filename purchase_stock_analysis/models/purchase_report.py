from odoo import api, fields, models
from odoo import tools
from datetime import timedelta

class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    opening_stock = fields.Float(string="Opening Stock", compute="_compute_stock_fields")
    purchase_qty = fields.Float(string="Purchase", compute="_compute_stock_fields")
    issue_qty = fields.Float(string="Issue", compute="_compute_stock_fields")
    closing_stock = fields.Float(string="Closing Stock", compute="_compute_stock_fields")

    @api.depends("product_id", "qty_ordered", "company_id", "date_order")
    def _compute_stock_fields(self):
        StockMove = self.env["stock.move"].sudo()
        for rec in self:
            purchase = rec.qty_ordered or 0.0
            current_on_hand = 0.0
            if rec.product_id:
                ctx = {}
                if rec.company_id:
                    ctx["force_company"] = rec.company_id.id
                current_on_hand = rec.product_id.with_context(**ctx).qty_available or 0.0

            opening = max(0.0, current_on_hand - purchase)

            issue = 0.0
            if rec.product_id:
                if getattr(rec, "date_order", False):
                    start_dt = rec.date_order
                else:
                    start_dt = fields.Datetime.now() - timedelta(days=30)
                start_date = fields.Datetime.to_string(start_dt)
                end_date = fields.Datetime.to_string(fields.Datetime.now())

                move_domain = [
                    ('state', '=', 'done'),
                    ('product_id', '=', rec.product_id.id),
                    ('date', '>=', start_date),
                    ('date', '<=', end_date),
                    ('location_id.usage', '=', 'internal'),
                    ('location_dest_id.usage', '!=', 'internal'),
                ]
                moves = StockMove.search(move_domain)
                total_out = 0.0
                for m in moves:
                    try:
                        qty_in_prod_uom = m.product_uom._compute_quantity(m.product_uom_qty, rec.product_id.uom_id)
                    except Exception:
                        qty_in_prod_uom = m.product_uom_qty
                    total_out += qty_in_prod_uom
                issue = total_out

            closing = max(0.0, current_on_hand - issue)

            rec.opening_stock = float(opening)
            rec.purchase_qty = float(purchase)
            rec.issue_qty = float(issue)
            rec.closing_stock = float(closing)
