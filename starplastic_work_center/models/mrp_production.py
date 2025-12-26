from odoo import api, fields, models, _
import re
import logging
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    batch_number = fields.Char('Batch Number')
    expected_delivery_date = fields.Date('Expected Delivery Date')
    warehouse_verified = fields.Boolean('Warehouse Verified', default=False)
    hourly_entry_count = fields.Integer(string='Hourly Entries', compute='_compute_hourly_entry_count')

    sale_order_qty = fields.Float(
        string='C.O Quantity',
        compute='_compute_customer_order',
        store=True
    )

    customer_po_number = fields.Char(
        string='C.O Number',
        compute='_compute_customer_order',
        store=True
    )

    @api.depends('origin', 'product_id')
    def _compute_customer_order(self):
        for mo in self:
            qty = 0.0
            po_number = False

            if mo.origin:
                match = re.search(r'\bS\d+\b', mo.origin)
                if match:
                    so = self.env['sale.order'].search(
                        [('name', '=', match.group(0))],
                        limit=1
                    )
                    if so:
                        solines = so.order_line.filtered(
                            lambda l: l.product_id == mo.product_id
                        )
                        qty = sum(solines.mapped('product_uom_qty'))
                        if solines:
                            po_number = solines[0].co_number
            mo.sale_order_qty = qty
            mo.customer_po_number = po_number

    def action_view_shifts(self):
        self.ensure_one()
        try:
            action = self.env.ref('starplastic_work_center.action_wc_shift').read()[0]
        except Exception as e:
            _logger.warning("Shift action not found, using inline action. Details: %s", e)
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Shifts',
                'res_model': 'work.center.shift',
                'view_mode': 'list,form',
            }
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = {'default_production_id': self.id, 'search_default_production_id': self.id}
        return action

    def _compute_hourly_entry_count(self):
        if not self.ids:
            for rec in self:
                rec.hourly_entry_count = 0
            return

        groups = self.env['work.center.hourly.entry'].read_group(
            domain=[('production_id', 'in', self.ids)],
            fields=['production_id'],
            groupby=['production_id'],
        )
        counts = {}
        for g in groups:
            if g.get('production_id'):
                prod_id = g['production_id'][0]
                cnt = g.get('__count', 0)
                if cnt == 0:
                    cnt = g.get('production_id_count', 0)
                counts[prod_id] = cnt

        for rec in self:
            rec.hourly_entry_count = counts.get(rec.id, 0)

    def action_view_hourly_entries(self):
        self.ensure_one()
        try:
            action = self.env.ref('starplastic_work_center.action_work_center_hourly_entry_master').read()[0]
        except Exception as e:
            _logger.warning("Hourly entries action not found, using inline action. Details: %s", e)
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Hourly Entries',
                'res_model': 'work.center.hourly.entry',
                'view_mode': 'list,form',
            }
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = {'default_production_id': self.id}
        return action