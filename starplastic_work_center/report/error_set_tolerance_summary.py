from odoo import models, fields, tools


class ErrorSetToleranceSummary(models.Model):
    _name = 'error.set.tolerance.summary'
    _description = 'Error Set Tolerance Summary'
    _auto = False

    date = fields.Date()
    workorder_no = fields.Char()
    machine_id = fields.Many2one('mrp.workcenter')

    shift_id = fields.Many2one(
        'work.center.shift',
    )

    shift_display = fields.Char(
        compute='_compute_shift_display',
        store=False
    )

    product_id = fields.Many2one('product.product', string='Item')

    production_kg_workshop = fields.Float()
    production_kg_store = fields.Float()
    difference_kg = fields.Float()
    difference_percent = fields.Float()

    action = fields.Char(string='Action')
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action_by = fields.Many2one('res.users')

    def _compute_shift_display(self):
        for rec in self:
            if rec.shift_id and rec.shift_id.name:
                rec.shift_display = rec.shift_id.name.split('-')[-1].strip()
            else:
                rec.shift_display = False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'error_set_tolerance_summary')
        self.env.cr.execute("""
            CREATE VIEW error_set_tolerance_summary AS (
                SELECT
                    row_number() OVER() AS id,
                    wcs.date AS date,
                    mo.name AS workorder_no,
                    wo.workcenter_id AS machine_id,
                    wcs.id AS shift_id,
                    wcs.mold_id AS product_id,

                    wcs.unit_waight AS production_kg_workshop,
                    wcs.unit_waight AS production_kg_store,

                    (wcs.unit_waight - wcs.unit_waight) AS difference_kg,

                    CASE
                        WHEN wcs.unit_waight = 0 THEN 0
                        ELSE 0
                    END AS difference_percent,

                    est_log.action AS action,
                    est_log.reason_id AS reason_id,
                    est_log.action_by AS action_by

                FROM work_center_shift wcs
                JOIN mrp_production mo ON mo.id = wcs.production_id
                JOIN mrp_workorder wo ON wo.production_id = mo.id
                LEFT JOIN error_set_tolerance_action_log est_log
                    ON est_log.report_id = wcs.id
            )
        """)
