from odoo import models, fields, tools


class RunningCavityReason(models.Model):
    _name = 'running.cavity.reason'
    _description = 'Running Cavity Reason'

    name = fields.Char(string='Reason')


class RunningCavityReasonWizard(models.TransientModel):
    _name = 'running.cavity.reason.wizard'
    _description = 'Running Cavity Reason Wizard'

    running_cavity_id = fields.Many2one('running.cavity.report', string='Running Cavity Report')
    reason_id = fields.Many2one('running.cavity.reason', string='Reason for Hiding')
    action = fields.Char(string='Action')


    def action_confirm(self):
        self.env['running.cavity.action.log'].create({
            'report_id': self.running_cavity_id.id,
            'reason_id': self.reason_id.id,
            'action_by': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}

class RunningCavityReport(models.Model):
    _name = 'running.cavity.report'
    _description = 'Running Cavity Report'
    _auto = False

    date = fields.Date()
    workorder_no = fields.Char("W.O. No")
    workcenter_id = fields.Many2one('mrp.workcenter', string="Machine")
    shift = fields.Char()
    product_id = fields.Many2one('product.product', string="Item")
    supervisor_one_id = fields.Many2one('res.users', string="Supervisor 1")
    supervisor_two_id = fields.Many2one('res.users', string="Supervisor 2")
    running_cavity = fields.Integer()
    mould_cavity = fields.Integer()
    action_state = fields.Selection(
        [('show', 'Show'), ('hide', 'Hide')],
        string='Action State'
    )

    def action_hide(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Acknowledge Cavity Action',
            'res_model': 'running.cavity.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_running_cavity_id': self.id,
            }
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'running_cavity_report')
        self.env.cr.execute("""
            CREATE VIEW running_cavity_report AS (
                SELECT
                    row_number() OVER() AS id,
                    mo.create_date AS date,
                    mo.name AS workorder_no,
                    NULL AS workcenter_id,
                    wc_shift.code AS shift,
                    mo.product_id,
                    wc_shift.supervisor_one_id AS supervisor_one_id,
                    wc_shift.supervisor_two_id AS supervisor_two_id,
                    wc_shift.cavity AS running_cavity,
                    wc_shift.cavity AS mould_cavity
                FROM mrp_production mo
                JOIN work_center_shift wc_shift ON wc_shift.production_id = mo.id
                JOIN product_product pp ON pp.id = mo.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
            )
        """)

class RunningCavityActionLog(models.Model):
    _name = 'running.cavity.action.log'

    report_id = fields.Integer()
    reason_id = fields.Many2one('running.cavity.reason')
    action = fields.Char()
    action_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    date = fields.Datetime(default=fields.Datetime.now)
