from odoo import models, fields, tools


class ProductionDelayReasonWizard(models.TransientModel):
    _name = 'production.delay.reason.wizard'
    _description = 'Production Delay Reason Wizard'

    production_delay_id = fields.Many2one(
        'production.delay.report', string='Production Delay Report', required=True
    )
    reason_id = fields.Many2one(
        'running.cavity.reason', string='Reason', required=True
    )

    def action_confirm(self):
        self.env['production.delay.action.log'].create({
            'report_id': self.production_delay_id.id,
            'reason_id': self.reason_id.id,
            'action_by': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}

class ProductionDelayReport(models.Model):
    _name = 'production.delay.report'
    _description = 'Production Delay Report'
    _auto = False

    wo_date = fields.Date(string='W.O Date')
    wo_no = fields.Char(string='W.O No')

    machine_id = fields.Many2one('mrp.workcenter', string='Machine')
    product_id = fields.Many2one('product.product', string='Item')

    qty = fields.Float(string='Qty')

    planned_start_date = fields.Datetime(string='Planned Start Date')
    actual_start_date = fields.Datetime(string='Actual Start Date')

    exp_delivery_date = fields.Date(string='Exp. Delivery Date')
    production_close_date = fields.Date(string='Production Close Date')
    production_end_date = fields.Datetime(string='Production End Date')

    production_delay = fields.Integer(string='Production Delay (Min)')

    def action_hide(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Acknowledge Production Delay',
            'res_model': 'production.delay.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_delay_id': self.id,
            }
        }

    def action_report_delay(self):
        return self.action_hide()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'production_delay_report')

        self.env.cr.execute("""
            CREATE VIEW production_delay_report AS (
                SELECT
                    row_number() OVER () AS id,

                    wo.date_start::date AS wo_date,
                    mp.name AS wo_no,

                    wo.workcenter_id AS machine_id,
                    mp.product_id AS product_id,

                    mp.product_qty AS qty,

                    NULL::timestamp AS planned_start_date,
                    wo.date_start AS actual_start_date,

                    wo.date_finished::date AS exp_delivery_date,
                    wo.date_finished::date AS production_close_date,
                    wo.date_finished AS production_end_date,

                    0 AS production_delay

                FROM mrp_workorder wo
                JOIN mrp_production mp ON mp.id = wo.production_id
                WHERE wo.date_start IS NOT NULL
            )
        """)


class ProductionDelayActionLog(models.Model):
    _name = 'production.delay.action.log'
    _description = 'Production Delay Action Log'

    report_id = fields.Integer()
    reason_id = fields.Many2one('running.cavity.reason')
    action_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    date = fields.Datetime(default=fields.Datetime.now)
