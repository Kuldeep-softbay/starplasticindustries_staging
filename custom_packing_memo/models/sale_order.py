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
        selections = self.env.context.get('packing_memo_selections', {})
        if not selections:
            return {'details': [], 'summary': []}

        details = []
        summary_map = defaultdict(float)

        for lot_id_str, qty in selections.items():
            lot = self.env['stock.lot'].browse(int(lot_id_str))
            product = lot.product_id

            details.append({
                'lot_name': lot.name,
                'product_display_name': product.display_name,
                'default_code': product.default_code,
                'qty': qty,
            })

            summary_map[(lot.name, product.id)] += qty

        summary = [{
            'lot_name': lot_name,
            'product_display_name': self.env['product.product'].browse(prod_id).display_name,
            'default_code': self.env['product.product'].browse(prod_id).default_code,
            'qty': total_qty,
        } for (lot_name, prod_id), total_qty in summary_map.items()]

        return {
            'details': details,
            'summary': summary,
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
