from odoo import api, fields, models, _
from datetime import datetime, time
import logging

_logger = logging.getLogger(__name__)


class RmRequiredAvailableReport(models.Model):
    _name = 'rm.required.available.report'
    _description = 'RM Required and Available Report'
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

    location_id = fields.Many2one('stock.location', string='Location')
    raw_type = fields.Char(string='Raw Type')


class RmRequiredAvailableWizard(models.TransientModel):
    _name = 'rm.required.available.wizard'
    _description = 'RM Required and Available Wizard'

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
    partner_id = fields.Many2one('res.partner', string='Party Name')
    raw_type = fields.Char(string='Raw Type')
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]",
    )
    product_id = fields.Many2one('product.product', string='Particular / Product')

    # ------------------------------------------------------------------
    # Helpers (same style as RM Real Store Book)
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
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])

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
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])

        return domain

    def _compute_opening_balance(self):
        """Opening balance from moves before date_from."""
        self.ensure_one()
        Move = self.env['stock.move']
        domain = self._opening_domain()
        moves = Move.search(domain)

        _logger.info(
            "RM Required & Available: opening_domain=%s, moves=%s",
            domain, len(moves)
        )

        opening = 0.0
        for mv in moves:
            qty = mv.product_uom_qty

            if self.location_id:
                if mv.location_dest_id == self.location_id:
                    opening += qty
                elif mv.location_id == self.location_id:
                    opening -= qty
            else:
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
        report_env = self.env['rm.required.available.report']
        Move = self.env['stock.move']

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"

        # 1) Opening balance (not shown as line)
        opening_balance = self._compute_opening_balance()

        # 2) Detail moves in range
        domain = self._base_domain()
        moves = Move.search(domain, order='date, id')

        _logger.info(
            "RM Required & Available: main_domain=%s, moves=%s",
            domain, len(moves)
        )

        balance = opening_balance
        for mv in moves:
            qty = mv.product_uom_qty

            received = 0.0
            issue = 0.0

            if self.location_id:
                if mv.location_dest_id == self.location_id:
                    received = qty
                elif mv.location_id == self.location_id:
                    issue = qty
            else:
                if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                    received = qty
                elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                    issue = qty

            balance += (received - issue)

            report_env.create({
                'computation_key': computation_key,
                'date': mv.date.date(),
                'particulars': mv.picking_id.origin or 'Production',
                'product_id': mv.product_id.id,
                'batch': getattr(mv, 'batch_no', '') or '',
                'grade': getattr(mv.product_id, 'grade', '') or '',
                'vendor_id': mv.partner_id.id
                            or (mv.picking_id.partner_id.id if mv.picking_id else False),
                'invoice_no': getattr(mv.picking_id, 'invoice_ref', '') or '',
                'received_qty': received,
                'pmemo_no': mv.reference or (mv.picking_id.name if mv.picking_id else ''),
                'issue_qty': issue,
                'balance_qty': balance,
                'location_id': self.location_id.id,
                'raw_type': self.raw_type,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Required and Available Report'),
            'res_model': 'rm.required.available.report',
            'view_mode': 'list',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }
