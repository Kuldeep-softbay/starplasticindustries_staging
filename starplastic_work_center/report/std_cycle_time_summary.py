from odoo import models, fields, tools

class StdCycleTimeSummary(models.Model):
    _name = 'std.cycle.time.summary'
    _description = 'Standard Cycle Time Summary'
    _auto = False

    date = fields.Date()
    workorder_no = fields.Char()
    machine_id = fields.Many2one('mrp.workcenter')
    shift = fields.Char()
    product_id = fields.Many2one('product.product')
    supervisor_one_id = fields.Many2one('res.users')
    supervisor_two_id = fields.Many2one('res.users')
    set_cycle_time = fields.Float()
    std_cycle_time = fields.Float()
    tolerance = fields.Float()
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action = fields.Char(string='Action')
    action_by = fields.Many2one('res.users', string='Action By')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'std_cycle_time_summary')
        self.env.cr.execute("""
            CREATE VIEW std_cycle_time_summary AS (
                SELECT
                    row_number() OVER() AS id,
                    wcs.date AS date,
                    mo.name AS workorder_no,
                    wo.workcenter_id AS machine_id,
                    wcs.code AS shift,
                    wcs.mold_id AS product_id,
                    wcs.supervisor_one_id AS supervisor_one_id,
                    wcs.supervisor_two_id AS supervisor_two_id,
                    wcs.cycle_time_sec AS set_cycle_time,
                    wcs.cycle_time_sec AS std_cycle_time,
                    0.0 AS tolerance,
                    NULL::integer AS reason_id,
                    NULL::varchar AS action,
                    NULL::integer AS action_by
                FROM work_center_shift wcs
                JOIN mrp_production mo ON mo.id = wcs.production_id
                JOIN mrp_workorder wo ON wo.production_id = mo.id
            )
        """)
