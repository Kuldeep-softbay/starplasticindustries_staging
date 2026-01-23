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

    unit_weight = fields.Float(string="Unit Weight")
    total_kg = fields.Float(string="Total KG")
    total_pcs = fields.Integer(
        string="Total PCS",
        compute="_compute_total_pcs",
        store=True
    )
    unit_weight_kg = fields.Float(
        string="Unit Weight (KG)",
        compute="_compute_unit_weight_kg",
        store=True)

    pmemo_ids = fields.One2many(
        'production.memo',
        'production_id',
        string='Production Memos'
    )
    pmemo_count = fields.Integer(
        compute='_compute_pmemo_count',
        string='P-Memo Count'
    )

    def _compute_pmemo_count(self):
        for rec in self:
            rec.pmemo_count = len(rec.pmemo_ids)

    # --------------------------------
    # Convert Unit Weight Gram → KG
    # --------------------------------
    @api.depends('unit_weight')
    def _compute_unit_weight_kg(self):
        for rec in self:
            rec.unit_weight_kg = rec.unit_weight / 1000 if rec.unit_weight else 0.0

    @api.depends('total_kg', 'unit_weight_kg')
    def _compute_total_pcs(self):
        for rec in self:
            # unit_weight_kg = rec.product_id.product_tmpl_id.weight or 0.0
            if rec.unit_weight_kg > 0:
                rec.total_pcs = int(rec.total_kg / rec.unit_weight_kg)
            else:
                rec.total_pcs = 0

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

    def action_open_pmemo(self):
        self.ensure_one()
        workorder = self.env['mrp.workorder'].search([('production_id', '=', self.id)], limit=1)
        routing_workcenter = workorder.workcenter_id if workorder else None

        # Fetch the routing line associated with the workcenter
        routing_line = self.env['mrp.routing.workcenter'].search([('workcenter_ids', 'in', routing_workcenter.id)], limit=1) if routing_workcenter else None
        print(routing_line)

        # Get the raw material used in the production of the product
        raw_material = self.bom_id.bom_line_ids[0].product_id if self.bom_id.bom_line_ids else None

        # Ensure cavity is fetched correctly, default to 0 if not found
        mould_cavity = routing_line.cavity if routing_line and hasattr(routing_line, 'cavity') else 0

        return {
            'type': 'ir.actions.act_window',
            'name': 'Production Memo',
            'res_model': 'production.memo',
            'view_mode': 'list,form',
            'domain': [('production_id', '=', self.id)],
            'context': {
                'default_production_id': self.id,
                'default_workcenter_id': routing_workcenter.id if routing_workcenter else False,
                'default_rm_type': raw_material.id if raw_material else False,
                'default_mould_cavity': mould_cavity,
                'default_product_id': self.product_id.id,
                'default_unit_weight': self.product_id.weight_gm,
                'default_lot_id': self.move_finished_ids.mapped('move_line_ids.lot_id')[0].id if self.move_finished_ids.mapped('move_line_ids.lot_id') else False,
                'default_production_qty': self.product_qty,
            }
        }
