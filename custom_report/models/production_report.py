# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, time
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    batch_number = fields.Char(
        string='Batch Number',
        required=True,
        index=True
    )


class ProductionReportLine(models.Model):
    _name = 'production.report.line'
    _description = 'Production Report Line'
    _order = 'date, id'

    computation_key = fields.Char(index=True)

    date = fields.Date(string='Date')
    particulars = fields.Char(string='Particulars')

    product_id = fields.Many2one('product.product', string='Item Name')
    batch = fields.Char(string='Batch No')

    total_production = fields.Float(string='Total Production')
    total_dispatch = fields.Float(string='Total Dispatch')
    total_reject = fields.Float(string='Rejection')
    balance = fields.Float(string='Stock')


class ProductionReportWizard(models.TransientModel):
    _name = 'production.report.wizard'
    _description = 'Production Report Wizard'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )

    workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Batch Number',
        domain="[('production_id.product_id', '=', product_id)]",
        help="Select Batch Number from Work Orders",
        required=True
    )
    batch_number = fields.Char(
        related='workorder_id.batch_number',
        string='Batch Number',
        readonly=True
    )

    def action_show_report(self):
        self.ensure_one()

        Report = self.env['production.report.line']
        Move = self.env['stock.move']
        Scrap = self.env['stock.scrap']

        computation_key = (
            f"{self.env.uid}-"
            f"{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        wo = self.workorder_id
        mo = wo.production_id

        if not mo:
            raise UserError(_("Selected Work Order has no Manufacturing Order"))

        product = self.product_id
        batch = wo.batch_number or ''
        production_qty = mo.qty_produced or 0.0
        dispatch_moves = Move.search([
            ('state', '=', 'done'),
            ('production_id', '=', mo.id),
            ('product_id', '=', product.id),
            ('location_dest_id.usage', '=', 'customer'),
        ])

        dispatch_qty = sum(dispatch_moves.mapped('product_uom_qty'))
        scrap_moves = Scrap.search([
            ('production_id', '=', mo.id),
            ('state', '=', 'done'),
        ])

        reject_qty = sum(scrap_moves.mapped('scrap_qty'))
        balance = production_qty - dispatch_qty - reject_qty

        Report.create({
            'computation_key': computation_key,
            'date': mo.date_finished.date()
                    if mo.date_finished
                    else fields.Date.context_today(self),
            'particulars': 'Batch Wise Production',
            'product_id': product.id,
            'batch': batch,
            'total_production': production_qty,
            'total_dispatch': dispatch_qty,
            'total_reject': reject_qty,
            'balance': balance,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Report'),
            'res_model': 'production.report.line',
            'view_mode': 'list,form',
            'domain': [('computation_key', '=', computation_key)],
            'target': 'current',
        }
