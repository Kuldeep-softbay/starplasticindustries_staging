# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date


# =========================================================
# MASTER: DISPATCH DELAY REASON
# =========================================================
class DispatchDelayReason(models.Model):
    _name = 'dispatch.delay.reason'
    _description = 'Dispatch Delay Reason'
    _order = 'name'

    name = fields.Char(string='Reason', required=True)
    active = fields.Boolean(default=True)


# =========================================================
# EXTEND STOCK PICKING
# =========================================================
class StockPicking(models.Model):
    _inherit = 'stock.picking'


    is_dispatch_delayed = fields.Boolean(
        string='Dispatch Delayed',
        compute='_compute_dispatch_delay',
        store=True
    )

    delay_reason_id = fields.Many2one(
        'dispatch.delay.reason',
        string='Delay Reason'
    )
    delay_acknowledged = fields.Boolean(
        string="Dispatch Delay Acknowledged",
        default=False
    )

    delay_reason = fields.Text(
        string="Dispatch Delay Reason"
    )

    delay_remark = fields.Text(string='Delay Remark')

    @api.depends('exp_dispatch_date', 'dispatch_date', 'state')
    def _compute_dispatch_delay(self):
        today = fields.Datetime.today()
        for rec in self:
            exp_date = rec.exp_dispatch_date
            if isinstance(exp_date, fields.Datetime):
                exp_date = exp_date.date()

            rec.is_dispatch_delayed = bool(
                exp_date
                and exp_date < today
                and not rec.dispatch_date
                and rec.state not in ('done', 'cancel')
            )

    # -----------------------------------------------------
    # BLOCK VALIDATION WITHOUT REASON
    # -----------------------------------------------------
    def button_validate(self):
        for rec in self:
            if rec.is_dispatch_delayed and not rec.delay_reason_id:
                raise ValueError(
                    _("Dispatch is delayed. Please select a Delay Reason before validation.")
                )
        return super().button_validate()
    

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        res = super().fields_view_get(view_id, view_type, toolbar, submenu)

        if view_type == 'form' and self.env.context.get('active_id'):
            picking = self.browse(self.env.context['active_id'])
            if picking.exists() and picking.is_dispatch_delayed and not picking.delay_reason_id:
                res['toolbar'] = res.get('toolbar', {})
                res['toolbar']['action'] = [{
                    'name': _('Dispatch Delay Reason'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'stock.picking',
                    'view_mode': 'form',
                    'views': [
                        (self.env.ref('custom_report.view_dispatch_delay_popup').id, 'form')
                    ],
                    'res_id': picking.id,
                    'target': 'new',
                }]
        return res


# =========================================================
# REPORT MODEL (SQL VIEW)
# =========================================================
class DispatchDelaySummary(models.Model):
    _name = 'dispatch.delay.summary'
    _description = 'Dispatch Delay Summary'
    _auto = False
    _order = 'exp_dispatch_date desc'

    picking_id = fields.Many2one('stock.picking', string='Delivery Order')
    picking_name = fields.Char(string='Delivery No')
    partner_id = fields.Many2one('res.partner', string='Customer Name')
    remarks = fields.Text(string='Remarks')
    total_qty = fields.Float(string='Total Qty')
    action_taken = fields.Char(string='Action By')
    action = fields.Char(string='Action')
    exp_dispatch_date = fields.Date(string='Exp Dispatch Date')
    dispatch_date = fields.Date(string='Dispatch Date')
    delay_reason_id = fields.Many2one('dispatch.delay.reason', string='Delay Reason')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('confirmed', 'Waiting Another Operation'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status')

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS dispatch_delay_summary CASCADE;
        """)
        self.env.cr.execute("""
            CREATE VIEW dispatch_delay_summary AS (
                SELECT
                    sp.id AS id,
                    sp.id AS picking_id,
                    sp.name AS picking_name,
                    sp.partner_id AS partner_id,
                    sp.remarks AS remarks,
                    0.0::float AS total_qty,
                    ''::varchar AS action_taken,
                    ''::varchar AS action,
                    sp.scheduled_date::date AS exp_dispatch_date,
                    sp.date_done::date AS dispatch_date,
                    sp.delay_reason_id,
                    sp.state
                FROM stock_picking sp
                WHERE
                    sp.scheduled_date IS NOT NULL
                    AND sp.scheduled_date::date < CURRENT_DATE
                    AND sp.state NOT IN ('done', 'cancel')
            )
        """)
