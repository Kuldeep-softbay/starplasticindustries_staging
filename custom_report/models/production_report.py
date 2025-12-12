# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, time

class ProductionReportLine(models.Model):
    _name = 'production.report.line'
    _description = 'Production Report Line'
    _order = 'date, id'

    computation_key = fields.Char(index=True)
    date = fields.Date(string='Date')
    particulars = fields.Char(string='Particulars')
    product_id = fields.Many2one('product.product', string='Product')
    batch = fields.Char(string='Batch')
    batch_lot_id = fields.Many2one('stock.production.lot', string='Batch Lot')
    total_production = fields.Float(string='Production')
    total_dispatch = fields.Float(string='Dispatch')
    total_reject = fields.Float(string='Rejection')
    balance = fields.Float(string='Balance')
    location_id = fields.Many2one('stock.location', string='Location')
    pmemo_no = fields.Char(string='P.Memo No')
    reference = fields.Char(string='Reference')


class ProductionReportWizard(models.TransientModel):
    _name = 'production.report.wizard'
    _description = 'Production Report Wizard'

    date_from = fields.Date(string='Date From', required=True,
                            default=lambda s: fields.Date.context_today(s))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda s: fields.Date.context_today(s))
    product_id = fields.Many2one('product.product', string='Product')
    lot_id = fields.Many2one('stock.location', string='Batch / Lot')
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain="[('usage','=','internal')]", help="Internal location to consider")

    def _dt_from(self):
        return fields.Datetime.to_datetime(datetime.combine(self.date_from, time.min))

    def _dt_to(self):
        return fields.Datetime.to_datetime(datetime.combine(self.date_to, time.max))

    def _domain_moves_before(self):
        dom = [('state', '=', 'done'),
               ('date', '<', self._dt_from())]
        if self.product_id:
            dom.append(('product_id', '=', self.product_id.id))
        if self.location_id:
            dom.extend(['|', ('location_id', '=', self.location_id.id),
                              ('location_dest_id', '=', self.location_id.id)])
        if self.lot_id:
            dom.append(('lot_id', '=', self.lot_id.id))
        return dom

    def _domain_moves_period(self):
        dom = [('state', '=', 'done'),
               ('date', '>=', self._dt_from()),
               ('date', '<=', self._dt_to())]
        if self.product_id:
            dom.append(('product_id', '=', self.product_id.id))
        if self.location_id:
            dom.extend(['|', ('location_id', '=', self.location_id.id),
                              ('location_dest_id', '=', self.location_id.id)])
        if self.lot_id:
            dom.append(('lot_id', '=', self.lot_id.id))
        return dom

    def action_show_report(self):
        """Generate simple aggregated lines per (product, batch) within the period and open list view.
        This is intentionally simple and uses stock.move aggregation by lot/product.
        """
        self.ensure_one()
        Move = self.env['stock.move']
        Report = self.env['production.report.line']

        computation_key = f"{self.env.uid}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"

        # opening balance (aggregate moves before date_from)
        # opening_map = {}
        # moves_before = Move.search(self._domain_moves_before())
        # for mv in moves_before:
        #     key = (mv.product_id.id, mv.lot_id.id or mv.lot_name or '')
        #     qty = mv.product_uom_qty or 0.0
        #     # treat moves into internal as +, out as -
        #     if self.location_id:
        #         if mv.location_dest_id == self.location_id:
        #             opening_map[key] = opening_map.get(key, 0.0) + qty
        #         elif mv.location_id == self.location_id:
        #             opening_map[key] = opening_map.get(key, 0.0) - qty
        #     else:
        #         if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
        #             opening_map[key] = opening_map.get(key, 0.0) + qty
        #         elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
        #             opening_map[key] = opening_map.get(key, 0.0) - qty

        # moves inside period
        # moves_period = Move.search(self._domain_moves_period(), order='date, id')
        # agg = {}
        # for mv in moves_period:
        #     key = (mv.product_id.id, mv.lot_id.id or mv.lot_name or '')
        #     if key not in agg:
        #         agg[key] = {
        #             'production': 0.0,
        #             'dispatch': 0.0,
        #             'reject': 0.0,
        #             'product_id': mv.product_id.id,
        #             'lot_id': mv.lot_id.id if mv.lot_id else False,
        #             'batch_name': mv.lot_id.name if mv.lot_id else (mv.lot_name or ''),
        #             'last_date': mv.date.date() if mv.date else self.date_to,
        #         }
        #     qty = mv.product_uom_qty or 0.0
        #     # classify by location usage: incoming to internal -> production/receipt, outgoing from internal -> dispatch
        #     if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
        #         agg[key]['production'] += qty
        #     elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
        #         agg[key]['dispatch'] += qty
        #     else:
        #         # internal->internal or other — ignore for this simple report
        #         pass

        # optionally include scraps if stock.scrap exists
        # Scrap = self.env.get('stock.scrap')
        # if Scrap:
        #     scraps = Scrap.search([('date_scrap', '>=', self._dt_from()), ('date_scrap', '<=', self._dt_to())] + (self.product_id and [('product_id', '=', self.product_id.id)] or []))
        #     for s in scraps:
        #         key = (s.product_id.id, s.lot_id.id or s.lot_name or '')
        #         if key not in agg:
        #             agg[key] = {
        #                 'production': 0.0,
        #                 'dispatch': 0.0,
        #                 'reject': 0.0,
        #                 'product_id': s.product_id.id,
        #                 'lot_id': s.lot_id.id if s.lot_id else False,
        #                 'batch_name': s.lot_id.name if s.lot_id else (s.lot_name or ''),
        #                 'last_date': s.date_scrap and s.date_scrap.date() or self.date_to,
        #             }
        #         agg[key]['reject'] += s.quantity

        # create report lines
        # created = []
        # for key, vals in agg.items():
        #     opening = opening_map.get(key, 0.0)
        #     prod = vals['production']
        #     disp = vals['dispatch']
        #     rej = vals['reject']
        #     balance = opening + prod - disp - rej

        #     rec = Report.create({
        #         'computation_key': computation_key,
        #         'date': vals.get('last_date') or self.date_to,
        #         'particulars': 'Batch summary',
        #         'product_id': vals.get('product_id'),
        #         'batch': vals.get('batch_name'),
        #         'batch_lot_id': vals.get('lot_id'),
        #         'total_production': prod,
        #         'total_dispatch': disp,
        #         'total_reject': rej,
        #         'balance': balance,
        #         'location_id': self.location_id.id if self.location_id else False,
        #     })
        #     created.append(rec.id)

        # include pure-opening-only batches (no moves in period)
        # for key, opening in opening_map.items():
        #     if key not in agg:
        #         rec = Report.create({
        #             'computation_key': computation_key,
        #             'date': self.date_from,
        #             'particulars': 'Opening balance',
        #             'product_id': key[0],
        #             'batch': key[1] or '',
        #             'batch_lot_id': False,
        #             'total_production': 0.0,
        #             'total_dispatch': 0.0,
        #             'total_reject': 0.0,
        #             'balance': opening,
        #             'location_id': self.location_id.id if self.location_id else False,
        #         })
        #         created.append(rec.id)

        # open the list view filtered by our computation_key
        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Report'),
            'res_model': 'production.report.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }
