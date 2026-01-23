from odoo import models, fields, tools

class RunningCavitySummary(models.Model):
    _name = 'running.cavity.summary'
    _description = 'Running Cavity Summary'
    _auto = False

    date = fields.Date()
    workorder_no = fields.Char()
    machine_id = fields.Many2one('mrp.workcenter')
    shift = fields.Char()
    product_id = fields.Many2one('product.product', string='Item')
    supervisor_one_id = fields.Many2one('res.users')
    supervisor_two_id = fields.Many2one('res.users')
    running_cavity = fields.Integer()
    mould_cavity = fields.Integer()
    action = fields.Char(string='Action')
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action_by = fields.Many2one('res.users')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'running_cavity_summary')
        self.env.cr.execute("""
            CREATE VIEW running_cavity_summary AS (
                SELECT
                    row_number() OVER() AS id,
                    wcs.date AS date,
                    mo.name AS workorder_no,
                    wo.workcenter_id AS machine_id,
                    wcs.code AS shift,
                    wcs.mold_id AS product_id,
                    wcs.supervisor_one_id AS supervisor_one_id,
                    wcs.supervisor_two_id AS supervisor_two_id,
                    wcs.cavity AS running_cavity,
                    NULL::integer AS mould_cavity,
                    NULL::varchar AS action,
                    NULL::integer AS reason_id,
                    NULL::integer AS action_by
                FROM work_center_shift wcs
                JOIN mrp_production mo ON mo.id = wcs.production_id
                JOIN mrp_workorder wo ON wo.production_id = mo.id
            )
        """)

