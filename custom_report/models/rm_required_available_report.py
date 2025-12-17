# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, time
import logging

_logger = logging.getLogger(__name__)


# =========================================================
# EXTEND STOCK MOVE (ADD PARTY_ID)
# =========================================================
class StockMove(models.Model):
    _inherit = 'stock.move'

    party_id = fields.Many2one(
        'job.party.work',
        string='Party',
        index=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            # From Picking
            if not move.party_id and move.picking_id and hasattr(move.picking_id, 'party_id'):
                move.party_id = move.picking_id.party_id.id

            # From Production
            if not move.party_id and move.raw_material_production_id and hasattr(
                move.raw_material_production_id, 'party_id'
            ):
                move.party_id = move.raw_material_production_id.party_id.id
        return moves


# =========================================================
# REPORT MODEL
# =========================================================
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
    vendor_id = fields.Many2one('job.party.work', string='Party')
    invoice_no = fields.Char(string='Invoice No')

    received_qty = fields.Float(string='Received')
    issue_qty = fields.Float(string='Issue')
    balance_qty = fields.Float(string='Balance')

    # ✅ REQUIRED FIELDS
    rm_required_qty = fields.Float(
        string='RM Required',
        compute='_compute_rm_values',
        store=True
    )
    rm_available_qty = fields.Float(
        string='RM Available',
        compute='_compute_rm_values',
        store=True
    )
    difference_qty = fields.Float(
        string='Difference',
        compute='_compute_rm_values',
        store=True
    )

    location_id = fields.Many2one('stock.location', string='Location')

    @api.depends('issue_qty', 'balance_qty')
    def _compute_rm_values(self):
        for rec in self:
            rec.rm_required_qty = rec.issue_qty or 0.0
            rec.rm_available_qty = rec.balance_qty or 0.0
            rec.difference_qty = rec.rm_required_qty - rec.rm_available_qty

# =========================================================
# WIZARD
# =========================================================
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

    party_id = fields.Many2one(
        'job.party.work',
        string='Party',
        required=False  # ✅ OPTIONAL
    )
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]",
    )

    # -----------------------------------------------------
    # DATE HELPERS
    # -----------------------------------------------------
    def _datetime_from(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_from, time.min)
        )

    def _datetime_to(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_to, time.max)
        )

    # -----------------------------------------------------
    # DOMAINS
    # -----------------------------------------------------
    def _base_domain(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', self._datetime_from()),
            ('date', '<=', self._datetime_to()),
        ]

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # ✅ OPTIONAL PARTY FILTER
        # if self.party_id:
        #     domain.append(('party_id', '=', self.party_id.id))

        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])

        return domain

    def _opening_domain(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'done'),
            ('date', '<', self._datetime_from()),
        ]

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # ✅ OPTIONAL PARTY FILTER
        if self.party_id:
            domain.append(('party_id', '=', self.party_id.id))

        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])

        return domain

    # -----------------------------------------------------
    # OPENING BALANCE
    # -----------------------------------------------------
    def _compute_opening_balance(self):
        Move = self.env['stock.move']
        opening = 0.0

        for mv in Move.search(self._opening_domain()):
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

    # -----------------------------------------------------
    # MAIN ACTION
    # -----------------------------------------------------
    def action_show_report(self):
        self.ensure_one()
        Move = self.env['stock.move']
        Report = self.env['rm.required.available.report']

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"

        balance = self._compute_opening_balance()

        for mv in Move.search(self._base_domain(), order='date, id'):
            qty = mv.product_uom_qty
            received = issue = 0.0

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

            Report.create({
                'computation_key': computation_key,
                'date': mv.date.date(),
                'particulars': mv.picking_id.origin or 'Stock Move',
                'product_id': mv.product_id.id,
                'batch': getattr(mv, 'batch_no', '') or '',
                'grade': getattr(mv.product_id, 'grade', '') or '',
                'vendor_id': mv.party_id.id if mv.party_id else False,
                'invoice_no': getattr(mv.picking_id, 'invoice_ref', '') or '',
                'received_qty': received,
                'issue_qty': issue,
                'balance_qty': balance,
                'location_id': self.location_id.id if self.location_id else False,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Required and Available Report'),
            'res_model': 'rm.required.available.report',
            'view_mode': 'list',
            'domain': [('computation_key', '=', computation_key)],
        }
