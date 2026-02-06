from odoo import models, fields, tools


class MrpProductionShiftReport(models.Model):
    _name = "mrp.production.shift.report"
    _description = "Production Shift Report"
    _auto = False

    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine", readonly=True)
    machine_name = fields.Char(string="Machine Name", readonly=True)
    shift_id = fields.Many2one(
        'work.center.shift'
    )

    shift_display = fields.Char(
        compute="_compute_shift_display",
        store=False
    )
    cavity = fields.Char(string="Cavity", readonly=True)
    downtime_minutes = fields.Float(string="Downtime (Min)", readonly=True)

    reason_id = fields.Many2one(
        "wc.downtime.reason", string="Downtime Reason", readonly=True
    )
    sub_reason_id = fields.Many2one(
        "wc.downtime.subreason", string="Downtime Sub Reason", readonly=True
    )
    explanation = fields.Char(string="Explanation", readonly=True)

    date = fields.Date(string="Date", readonly=True)

    def _compute_shift_display(self):
        for rec in self:
            if rec.shift_id and rec.shift_id.name:
                # Example name: "WH/MO/00004 - 2026-01-23 - Shift B"
                rec.shift_display = rec.shift_id.name.split('-')[-1].strip()
            else:
                rec.shift_display = False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE VIEW mrp_production_shift_report AS (
                SELECT
                    row_number() OVER () AS id,

                    wc.id AS workcenter_id,
                    wc.name AS machine_name,

                    wc_shift.id AS shift_id,
                    wc_shift.name AS shift_display,

                    wo.name AS cavity,

                    EXTRACT(EPOCH FROM (mp.date_end - mp.date_start)) / 60
                        AS downtime_minutes,

                    NULL::integer AS reason_id,
                    NULL::integer AS sub_reason_id,
                    NULL::varchar AS explanation,

                    DATE(mp.date_start) AS date

                FROM mrp_workcenter_productivity mp

                JOIN mrp_workorder wo
                    ON wo.id = mp.workorder_id

                JOIN mrp_production mo
                    ON mo.id = wo.production_id

                JOIN work_center_shift wc_shift
                    ON wc_shift.production_id = mo.id

                JOIN mrp_workcenter wc
                    ON wc.id = wo.workcenter_id
            )
        """)
