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

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    party_id = fields.Many2one('job.party.work', string='Party Name')
    product_id = fields.Many2one('product.product', string='Product')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _datetime_from(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_from, time.min)
        )

    def _datetime_to(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_to, time.max)
        )

    def _base_domain(self):
        """Domain for moves inside the selected period."""
        self.ensure_one()
        dt_from = self._datetime_from()
        dt_to = self._datetime_to()

        domain = [
            ('state', '=', 'done'),
            ('date', '>=', dt_from),
            ('date', '<=', dt_to),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.party_id:
            domain.append(('party_id', '=', self.party_id.id))
        return domain

    def _opening_domain(self):
        """Domain for moves strictly before date_from."""
        self.ensure_one()
        dt_from = self._datetime_from()

        domain = [
            ('state', '=', 'done'),
            ('date', '<', dt_from),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.party_id:
            domain.append(('party_id', '=', self.party_id.id))
        return domain

    def _compute_opening_balance(self):
        """Opening balance = net internal IN - OUT before date_from."""
        self.ensure_one()
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

    # ------------------------------------------------------------------
    # Main action
    # ------------------------------------------------------------------

    def action_show_report(self):
        self.ensure_one()
        report_env = self.env['rm.grade.wise.stock.report']
        Move = self.env['stock.move']

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"

        # 1) Starting balance (not shown as separate row)
        balance = self._compute_opening_balance()

        # 2) Detail rows
        moves = Move.search(self._base_domain(), order='date, id')

        for mv in moves:
            qty = mv.product_uom_qty

            received = 0.0
            issued = 0.0

            # generic internal in/out logic
            if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                received = qty
            elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                issued = qty

            balance += (received - issued)

            report_env.create({
                'computation_key': computation_key,
                'date': mv.date.date(),
                'particulars': mv.picking_id.origin or 'Production',
                'product_id': mv.product_id.id,
                'batch': getattr(mv, 'batch_no', '') or '',
                'grade': getattr(mv.product_id, 'grade', '') or '',
                'vendor_id': mv.partner_id.id
                            or (mv.picking_id.party_id.id if mv.picking_id else False),
                'invoice_no': getattr(mv.picking_id, 'invoice_ref', '') or '',
                'received_qty': received,
                'pmemo_no': mv.reference or (mv.picking_id.name if mv.picking_id else ''),
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
