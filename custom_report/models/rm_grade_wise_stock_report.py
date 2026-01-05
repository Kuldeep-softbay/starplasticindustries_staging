from odoo import api, fields, models, _
from datetime import datetime, time


class RmGradeWiseStockReport(models.Model):
    _name = 'rm.grade.wise.stock.report'
    _description = 'RM Grade Wise Stock Report'
    _order = 'date, id'

    computation_key = fields.Char(index=True)

    date = fields.Date(string='Date')
    particulars = fields.Char(string='Particulars')
    product_id = fields.Many2one('product.product', string='Product')
    batch = fields.Char(string='Batch')
    grade = fields.Char(string='Grade')
    vendor_id = fields.Many2one('res.partner', string='Vendor/Supplier')
    invoice_no = fields.Char(string='Invoice No')
    received_qty = fields.Float(string='Received')
    pmemo_no = fields.Char(string='P.Memo No')
    issue_qty = fields.Float(string='Issue')
    balance_qty = fields.Float(string='Balance')


class RmGradeWiseStockWizard(models.TransientModel):
    _name = 'rm.grade.wise.stock.wizard'
    _description = 'RM Grade Wise Stock Wizard'

    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    party_id = fields.Many2one('job.party.work', string='Party Name')
    product_id = fields.Many2one('product.product', string='Product')

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _datetime_from(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_from, time.min)
        )

    def _datetime_to(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_to, time.max)
        )

    def _base_domain(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', self._datetime_from()),
            ('date', '<=', self._datetime_to()),

            # Raw Material only
            ('product_id.product_tmpl_id.purchase_ok', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', False),

            # Must affect internal stock
            '|',
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),

            # Manufacturing or Picking (clean data)
            # '|',
            # ('raw_material_production_id', '!=', False),
            # ('picking_id', '!=', False),
        ]

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        if self.party_id:
            domain.append(('party_id', '=', self.party_id.id))

        return domain



    def _opening_domain(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'done'),
            ('date', '<', self._datetime_from()),

            # Raw Material only
            ('product_id.product_tmpl_id.purchase_ok', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', False),

            # Must affect internal stock
            '|',
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
        ]

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        if self.party_id:
            domain.append(('party_id', '=', self.party_id.id))

        return domain

    def _compute_opening_balance(self):
        Move = self.env['stock.move']
        moves = Move.search(self._opening_domain())

        opening = 0.0
        for mv in moves:
            qty = mv.product_uom_qty
            if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                opening += qty
            elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                opening -= qty
        return opening

    # ------------------------------------------------------------
    # Main Action
    # ------------------------------------------------------------

    def action_show_report(self):
        self.ensure_one()
        report_env = self.env['rm.grade.wise.stock.report']
        Move = self.env['stock.move']

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"
        balance = self._compute_opening_balance()

        moves = Move.search(self._base_domain(), order='date, id')

        for mv in moves:
            qty = mv.product_uom_qty
            received = issued = 0.0

            # --------------------------------------------------
            # RM RECEIPT (Purchase / Return / FG Unbuild)
            # --------------------------------------------------
            if (
                mv.location_dest_id.usage == 'internal'
                and mv.location_id.usage not in ('internal', 'production')
            ):
                received = qty

            # --------------------------------------------------
            # RM ISSUE TO MANUFACTURING (MOST IMPORTANT FIX)
            # --------------------------------------------------
            elif (
                mv.location_id.usage == 'internal'
            ):
                issued = qty

            # # --------------------------------------------------
            # # RM ISSUE TO CUSTOMER / SCRAP
            # # --------------------------------------------------
            # elif (
            #     mv.location_id.usage == 'internal'
            #     and mv.location_dest_id.usage in ('customer', 'scrap')
            # ):
                issued = qty
            balance += (received - issued)

            report_env.create({
                'computation_key': computation_key,
                'date': mv.date.date(),
                'particulars': mv.picking_id.origin or mv.picking_id.name,
                'product_id': mv.product_id.id,
                'batch': mv.picking_id.internal_batch_number or '',
                'grade': getattr(mv.product_id, 'grade', '') or '',
                'vendor_id': mv.partner_id.id,
                'invoice_no': getattr(mv.picking_id, 'invoice_ref', '') or '',
                'received_qty': received,
                'pmemo_no': mv.picking_id.name,
                'issue_qty': issued,
                'balance_qty': balance,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Grade Wise Stock Report'),
            'res_model': 'rm.grade.wise.stock.report',
            'view_mode': 'list',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }
