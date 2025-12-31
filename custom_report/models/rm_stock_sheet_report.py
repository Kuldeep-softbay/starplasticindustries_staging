# -*- coding: utf-8 -*-
from odoo import fields, models, _
from datetime import datetime, time
import logging

_logger = logging.getLogger(__name__)


# =========================================================
# REPORT MODEL
# =========================================================
class RmStockSheetReport(models.Model):
    _name = 'rm.stock.sheet.report'
    _description = 'RM Stock Sheet Report'
    _order = 'party_id, location_id, product_id, grade, batch, id'

    computation_key = fields.Char(index=True)

    date = fields.Date(string='Date')
    party_id = fields.Many2one('job.party.work', string='Party')
    location_id = fields.Many2one('stock.location', string='Location')

    # ✅ PRODUCT VARIANT (CORRECT FK)
    product_id = fields.Many2one('product.product', string='Raw Material')

    grade = fields.Char(string='RM Grade')
    mfi = fields.Char(string='MFI')
    batch = fields.Char(string='Batch')

    bag_qty = fields.Float(string='Bag')
    kgs = fields.Float(string='Kgs')
    total_kgs = fields.Float(string='Total Kg')
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        domain="[('purchase_ok', '=', True), ('sale_ok', '=', False)]",
    )


# =========================================================
# WIZARD
# =========================================================
class RmStockSheetWizard(models.TransientModel):
    _name = 'rm.stock.sheet.wizard'
    _description = 'RM Stock Sheet Wizard'

    date = fields.Date(
        string='As On Date',
        required=True,
        default=fields.Date.context_today,
    )
    party_id = fields.Many2one('job.party.work', string='Party')

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]",
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        domain="[('purchase_ok', '=', True), ('sale_ok', '=', False)]",
    )

    # -----------------------------------------------------
    # HELPERS
    # -----------------------------------------------------
    def _datetime_to(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date, time.max)
        )

    def _base_domain_move_line(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'done'),
            ('date', '<=', self._datetime_to()),
        ]

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        if self.product_tmpl_id:
            domain.append(('product_id.product_tmpl_id', '=', self.product_tmpl_id.id))

        if self.party_id:
            domain.append(('move_id.party_id', '=', self.party_id.id))

        return domain

    # -----------------------------------------------------
    # MAIN ACTION
    # -----------------------------------------------------
    def action_show_report(self):
        self.ensure_one()

        Report = self.env['rm.stock.sheet.report']
        MoveLine = self.env['stock.move.line']

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"

        Report.search([('computation_key', '=', computation_key)]).unlink()

        move_lines = MoveLine.search(
            self._base_domain_move_line(),
            order='date, id'
        )

        aggregated = {}

        for ml in move_lines:
            product = ml.product_id
            tmpl = product.product_tmpl_id

            # RAW MATERIAL ONLY
            if not (tmpl.purchase_ok and not tmpl.sale_ok):
                continue

            qty = ml.qty_done or 0.0
            if not qty:
                continue

            delta = 0.0
            location = False

            if self.location_id:
                loc = self.location_id
                if ml.location_dest_id == loc:
                    delta = qty
                    location = loc
                elif ml.location_id == loc:
                    delta = -qty
                    location = loc
                else:
                    continue
            else:
                if ml.location_dest_id.usage == 'internal':
                    delta = qty
                    location = ml.location_dest_id
                elif ml.location_id.usage == 'internal':
                    delta = -qty
                    location = ml.location_id
                else:
                    continue

            if abs(delta) < 0.00001:
                continue

            party = ml.move_id.party_id or False

            # SAFE READS
            grade = product.display_name
            picking = ml.move_id.picking_id

            mfi = picking.mfi_value if picking and hasattr(picking, 'mfi_value') else ''
            batch = picking.supplier_batch_number if picking and hasattr(picking, 'supplier_batch_number') else ''
            bag_qty = picking.number_of_bags if picking and hasattr(picking, 'number_of_bags') else 0.0

            key = (
                party.id if party else False,
                location.id if location else False,
                tmpl.id,
                product.id,
                grade,
                batch,
                mfi,
            )

            if key not in aggregated:
                aggregated[key] = {
                    'party': party,
                    'location': location,
                    'product_tmpl': tmpl.id,
                    'product': product.id,
                    'grade': grade,
                    'mfi': mfi,
                    'batch': batch,
                    'bag_qty': 0.0,
                    'kgs': 0.0,
                }

            aggregated[key]['bag_qty'] += bag_qty
            aggregated[key]['kgs'] += delta

        # CREATE REPORT LINES
        for data in aggregated.values():
            if abs(data['kgs']) < 0.00001:
                continue

            Report.create({
                'computation_key': computation_key,
                'date': self.date,
                'party_id': data['party'].id if data['party'] else False,
                'location_id': data['location'].id if data['location'] else False,
                'product_tmpl_id': data['product_tmpl'],
                'product_id': data['product'],
                'grade': data['grade'],
                'mfi': data['mfi'],
                'batch': data['batch'],
                'bag_qty': data['bag_qty'],
                'kgs': data['kgs'],
                'total_kgs': data['kgs'],
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Stock Sheet Report'),
            'res_model': 'rm.stock.sheet.report',
            'view_mode': 'list',
            'domain': [('computation_key', '=', computation_key)],
            'target': 'current',
        }
