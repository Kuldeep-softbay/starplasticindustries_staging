from odoo import api, fields, models, _
from datetime import datetime


class FgStoreReport(models.Model):
    _name = 'fg.store.report'
    _description = 'FG Stock Report'
    _order = 'date, id'

    # Used to isolate one wizard run from another
    computation_key = fields.Char(string='Computation Key', index=True)

    date = fields.Date(string='Date')
    partner_id = fields.Many2one('res.partner', string='Party')
    wo_no = fields.Char(string='W.O No')
    pmemo = fields.Char(string='Pmemo')
    challan_no = fields.Char(string='Challan No.')
    unit_weight = fields.Float(string='Unit Weight')
    received_qty = fields.Float(string='Received')
    issued_qty = fields.Float(string='Issued')
    balance_qty = fields.Float(string='Balance')

    product_id = fields.Many2one('product.product', string='Item Name')
    stock_type = fields.Selection(
        [
            ('fg', 'Finished Goods'),
            ('rm', 'Raw Material'),
            ('cons', 'Consumable'),
        ],
        string='Stock Type',
    )


class FgStoreReportWizard(models.TransientModel):
    _name = 'fg.store.report.wizard'
    _description = 'FG Stock Report Wizard'

    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.context_today(self))
    partner_id = fields.Many2one('res.partner', string='Party')
    product_id = fields.Many2one('product.product', string='Item Name')
    stock_type = fields.Selection(
        [
            ('fg', 'Finished Goods'),
            ('rm', 'Raw Material'),
            ('cons', 'Consumable'),
        ],
        string='Stock Type',
    )

    def _build_domain(self):
        """Build domain for stock moves or your custom table."""
        self.ensure_one()
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        # stock_type is custom, adapt as needed
        return domain

    def action_show_report(self):
        self.ensure_one()

        # 1) Clean previous run for this user (optional, you can change logic)
        report_env = self.env['fg.store.report']

        # Use a unique key for this run
        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"

        # 2) Compute data and create fg.store.report lines
        # ------------------------------------------------------------------
        # EXAMPLE using stock.move (you can replace with your own SQL / model)
        domain = self._build_domain()
        moves = self.env['stock.move'].search(domain, order='date, id')

        balance = 0.0
        for mv in moves:
            # Decide received/issued based on locations or picking type
            received = 0.0
            issued = 0.0

            # Example logic: incoming to FG location = received, outgoing from FG location = issued
            # You MUST adapt 'usage' / location_ids to your real FG locations.
            if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                received = mv.product_uom_qty
            elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                issued = mv.product_uom_qty

            balance += (received - issued)

            report_env.create({
                'computation_key': computation_key,
                'date': mv.date.date(),
                'partner_id': mv.partner_id.id or (mv.picking_id.partner_id.id if mv.picking_id else False),
                'wo_no': mv.origin,  # you can map to your W.O field
                'pmemo': mv.reference or '',  # adapt
                'challan_no': mv.picking_id.name if mv.picking_id else '',
                'unit_weight': mv.product_id.weight or 0.0,
                'received_qty': received,
                'issued_qty': issued,
                'balance_qty': balance,
                'product_id': mv.product_id.id,
                'stock_type': self.stock_type,
            })

        # If you want an explicit "Opening balance" row, create one before loop:
        # report_env.create({ ... 'date': self.date_from, 'pmemo': 'Opening balance', 'balance_qty': opening_balance })

        # 3) Open tree view filtered by computation_key
        action = {
            'type': 'ir.actions.act_window',
            'name': _('FG Stock Report'),
            'res_model': 'fg.store.report',
            'view_mode': 'list',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }
        return action
