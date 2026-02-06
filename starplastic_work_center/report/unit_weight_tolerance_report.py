from odoo import models, fields, tools

class UnitWeightToleranceWizard(models.TransientModel):
    _name = 'unit.weight.tolerance.wizard'
    _description = 'Unit Weight Tolerance Wizard'

    unit_weight_tolerance_id = fields.Many2one('unit.weight.tolerance.report', string='Unit Weight Tolerance Report')
    reason_id = fields.Many2one('running.cavity.reason', string='Reason for Hiding')
    action = fields.Char(string='Action')


    def action_confirm(self):
        self.env['unit.weight.tolerance.action.log'].create({
            'report_id': self.unit_weight_tolerance_id.id,
            'reason_id': self.reason_id.id,
            'action_by': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}

class UnitWeightToleranceReport(models.Model):
    _name = 'unit.weight.tolerance.report'
    _description = 'Unit Weight Tolerance Report'
    _auto = False

    date = fields.Date(string='Date')
    workorder_no = fields.Char(string='W.O No')
    machine_id = fields.Many2one('mrp.workcenter', string='Machine')
    shift_id = fields.Many2one('work.center.shift', string='Shift')
    shift_display = fields.Char(
        compute='_compute_shift_display',
        store=False,
    )
    product_id = fields.Many2one('product.product', string='Item')

    supervisor_one_id = fields.Many2one('res.users', string='Supervisor 1')
    supervisor_two_id = fields.Many2one('res.users', string='Supervisor 2')

    time = fields.Char(string='Time')

    actual_weight = fields.Float(string='Actual Weight')
    std_weight = fields.Float(string='Std Weight')

    tolerance = fields.Float(string='Tolerance (+/-)')
    action = fields.Char(string='Action')

    def _compute_shift_display(self):
        for rec in self:
            if rec.shift_id and rec.shift_id.name:
                rec.shift_display = rec.shift_id.name.split('-')[-1].strip()
            else:
                rec.shift_display = False

    def action_hide(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Acknowledge Unit Weight Tolerance',
            'res_model': 'unit.weight.tolerance.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_unit_weight_tolerance_id': self.id,
            }
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'unit_weight_tolerance_report')
        self.env.cr.execute("""
            CREATE VIEW unit_weight_tolerance_report AS (
                SELECT
                    row_number() OVER () AS id,

                    wcs.date AS date,
                    mo.name AS workorder_no,
                    wo.workcenter_id AS machine_id,
                    wcs.id AS shift_id,
                    wcs.mold_id AS product_id,

                    wcs.supervisor_one_id AS supervisor_one_id,
                    wcs.supervisor_two_id AS supervisor_two_id,

                    ''::varchar AS time,

                    wcs.unit_waight AS actual_weight,
                    pt.weight AS std_weight,

                    (wcs.unit_waight - pt.weight) AS tolerance,

                    ''::varchar AS action

                FROM work_center_shift wcs
                JOIN mrp_production mo
                    ON mo.id = wcs.production_id
                JOIN mrp_workorder wo
                    ON wo.production_id = mo.id
                JOIN product_product pp
                    ON pp.id = wcs.mold_id
                JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id
            )
        """)

class UnitWeightToleranceActionLog(models.Model):
    _name = 'unit.weight.tolerance.action.log'
    _description = 'Unit Weight Tolerance Action Log'

    report_id = fields.Integer()
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action = fields.Char()
    action_by = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user
    )
    date = fields.Datetime(default=fields.Datetime.now)

