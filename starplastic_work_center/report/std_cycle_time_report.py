from odoo import models, fields, tools

class StdCycleTimeReasonWizard(models.Model):
    _name = 'std.cycle.time.reason.wizard'
    _description = 'Standard Cycle Time Reason Wizard'

    std_cycle_time_id = fields.Many2one('std.cycle.time.report', string='Standard Cycle Time Report')
    reason_id = fields.Many2one('running.cavity.reason', string='Reason for Hiding')
    action = fields.Char(string='Action')

    def action_confirm(self):
        self.ensure_one()
        report_record = self.std_cycle_time_id
        # report_record.reason_id = self.reason_id
        return {'type': 'ir.actions.act_window_close'}
    
class StdCycleTimeHidden(models.Model):
    _name = 'std.cycle.time.hidden'
    _description = 'Hidden Std Cycle Time Lines'

    report_key = fields.Char(index=True)
    reason_id = fields.Many2one('running.cavity.reason')


class StdCycleTimeReport(models.Model):
    _name = 'std.cycle.time.report'
    _description = 'Standard Cycle Time Report'
    _auto = False

    date = fields.Date()
    workorder_no = fields.Char()
    machine_id = fields.Many2one('mrp.workcenter')
    shift_id = fields.Many2one('work.center.shift')
    shift_display = fields.Char(
        compute='_compute_shift_display',
        store=False,
    )
    product_id = fields.Many2one('product.product')
    supervisor_one_id = fields.Many2one('res.users')
    supervisor_two_id = fields.Many2one('res.users')
    set_cycle_time = fields.Float()
    std_cycle_time = fields.Float()
    tolerance = fields.Float()
    hourly_target = fields.Float()
    report_key = fields.Char()
    is_hidden = fields.Boolean(compute='_compute_hidden')

    def _compute_shift_display(self):
        for rec in self:
            if rec.shift_id and rec.shift_id.name:
                rec.shift_display = rec.shift_id.name.split('-')[-1].strip()
            else:
                rec.shift_display = False

    def _compute_hidden(self):
        Hide = self.env['running.cavity.hide.log']
        for rec in self:
            rec.is_hidden = bool(Hide.search([('report_key', '=', rec.report_key)], limit=1))

    def action_hide(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Acknowledge Std Cycle Time Action',
            'res_model': 'std.cycle.time.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_std_cycle_time_id': self.id,
            }
        }
    
    def action_confirm(self):
        self.ensure_one()

        key = self.std_cycle_time_id.report_key
        Hide = self.env['running.cavity.hide.log']

        if not Hide.search([('report_key', '=', key)], limit=1):
            Hide.create({
                'report_key': key,
                'reason_id': self.reason_id.id,
            })

        return {'type': 'ir.actions.act_window_close'}


    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'std_cycle_time_report')
        self.env.cr.execute("""
            CREATE VIEW std_cycle_time_report AS (
                SELECT
                    row_number() OVER() AS id,
                    CONCAT(wcs.date, '-', mo.name, '-', wo.workcenter_id) AS report_key,
                    wcs.date AS date,
                    mo.name AS workorder_no,
                    wo.workcenter_id AS machine_id,
                    wcs.id AS shift_id,
                    wcs.mold_id AS product_id,
                    wcs.supervisor_one_id AS supervisor_one_id,
                    wcs.supervisor_two_id AS supervisor_two_id,
                    wcs.cycle_time_sec AS set_cycle_time,
                    wcs.cycle_time_sec AS std_cycle_time,
                    0.0 AS tolerance,
                    wcs.hourly_target_qty AS hourly_target
                FROM work_center_shift wcs
                JOIN mrp_production mo ON mo.id = wcs.production_id
                JOIN mrp_workorder wo ON wo.production_id = mo.id
            )
        """)


class RunningCavityHideLog(models.Model):
    _name = 'running.cavity.hide.log'
    _description = 'Running Cavity Hidden Records'

    report_key = fields.Char(required=True, index=True)
    reason_id = fields.Many2one('running.cavity.reason', required=True)
    hidden_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    hidden_on = fields.Datetime(default=fields.Datetime.now)






