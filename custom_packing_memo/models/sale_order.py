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
    
    workorder_count = fields.Integer(
        string='Work Orders',
        compute='_compute_workorder_count'
    )

    # def _compute_workorder_count(self):
    #     for order in self:
    #         order.workorder_count = self.env['mrp.workorder'].search_count([
    #             ('production_id.origin', '=', order.name)
    #         ])

    def _compute_workorder_count(self):
        data = self.env['mrp.workorder']._read_group([
            ('operation_id', 'in', self.ids),
            ('state', '=', 'done')], ['operation_id'], ['__count'])
        count_data = {operation.id: count for operation, count in data}
        for operation in self:
            operation.workorder_count = count_data.get(operation.id, 0)

    def action_view_workorders(self):
        self.ensure_one()
        workorders = self.env['mrp.workorder'].search([
            ('production_id.origin', '=', self.name)
        ])

        action_ref = False
        try:
            action_ref = self.env.ref('mrp.mrp_workorder_todo', False)
        except Exception:
            action_ref = False

        if action_ref:
            action = action_ref.read()[0]
        else:
            act = self.env['ir.actions.act_window'].search([
                ('res_model', '=', 'mrp.workorder')
            ], limit=1)
            if act:
                action = act.read()[0]
            else:
                action = {
                    'type': 'ir.actions.act_window',
                    'name': _('Work Orders'),
                    'res_model': 'mrp.workorder',
                    'view_mode': 'tree,form',
                }

        if len(workorders) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = workorders.id
        else:
            action['domain'] = [('id', 'in', workorders.ids)]

        return action
