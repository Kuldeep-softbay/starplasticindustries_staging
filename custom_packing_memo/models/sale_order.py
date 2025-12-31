from odoo import api, fields, models, _
from collections import defaultdict

class SaleOrder(models.Model):
    _inherit = "sale.order"

    exp_dis_date = fields.Date(string="Expected Dispatch Date")
    exp_packing_date = fields.Date(string="Expected Packing Date")
    actual_packing_date = fields.Date(string="Actual Packing Date")
    remark = fields.Char(string="Remark")
    packing_details = fields.Html(
        string="Packing Details",
        sanitize=True
    )
    @api.onchange('partner_id')
    def _onchange_partner_id_set_packing_details(self):
        """
        When customer is selected, populate Packing Details
        from Customer Internal Notes (comment).
        """
        for order in self:
            if order.partner_id and order.partner_id.comment:
                order.packing_details = order.partner_id.comment
            else:
                order.packing_details = False

    def get_packing_memo_payload(self):
        self.ensure_one()

        details = []
        totals = defaultdict(float)

        co_numbers = self.order_line.mapped("co_number")
        co_numbers = [c for c in co_numbers if c]

        if not co_numbers:
            return {
                "details": [],
                "summary": [],
            }

        workorders = self.env["mrp.workorder"].search([
            ("customer_po_number", "in", co_numbers)
        ])

        for wo in workorders:
            batch_number = wo.batch_number or ""
            qty = wo.qty_production or wo.production_id.product_qty
            product = wo.product_id or wo.production_id.product_id

            # ---------- DETAILS ----------
            details.append({
                "batch_number": batch_number,
                "product_display_name": product.display_name,
                "default_code": product.default_code or "",
                "qty": qty,
            })

            # ---------- SUMMARY KEY = (product, batch) ----------
            totals[(product.id, batch_number)] += qty

        summary = []
        for (product_id, batch_number), qty in totals.items():
            product = self.env["product.product"].browse(product_id)

            summary.append({
                "batch_number": batch_number,
                "product_display_name": product.display_name,
                "default_code": product.default_code or "",
                "qty": qty,
            })

        return {
            "details": details,
            "summary": summary,
        }

    def write(self, vals):
        res = super().write(vals)

        if 'exp_dispatch_date' in vals:
            for order in self:
                pickings = order.picking_ids.filtered(
                    lambda p: p.state not in ('done', 'cancel')
                    and p.picking_type_code == 'outgoing'
                )
                pickings.write({
                    'exp_dispatch_date': order.exp_dispatch_date,
                })

        return res
