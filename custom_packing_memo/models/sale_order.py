from odoo import api, fields, models, _
from collections import defaultdict

class SaleOrder(models.Model):
    _inherit = "sale.order"

    exp_dispatch_date = fields.Date(string="Expected Dispatch Date")
    exp_packing_date = fields.Date(string="Expected Packing Date")
    actual_packing_date = fields.Date(string="Actual Packing Date")
    remark = fields.Char(string="Remark")
    packing_details = fields.Text(string="Packing Details")

    def get_packing_memo_payload(self):
        """Build a data payload for the QWeb template based on sale order lines."""
        self.ensure_one()
        details = []
        totals = defaultdict(float)

        for line in self.order_line:
            qty = line.product_uom_qty
            details.append({
                "batch_number": line.product_id.batch_number or "",
                "product_display_name": line.product_id.display_name,
                "default_code": line.product_id.default_code or "",
                "qty": qty,
            })
            totals[line.product_id.id] += qty

        summary = []
        products = self.env["product.product"].browse(list(totals.keys()))
        for prod in products:
            summary.append({
                "product_display_name": prod.display_name,
                "default_code": prod.default_code or "",
                "qty": float(totals[prod.id]),
            })

        details.sort(key=lambda d: d["product_display_name"])
        summary.sort(key=lambda s: s["product_display_name"])

        return {
            "details": details,
            "summary": summary,
        }
