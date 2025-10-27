from odoo import api, fields, models

class WorkCenterShift(models.Model):
    _name = 'work.center.shift'
    _description = 'Work Center Shift'
    _order = 'date desc, id desc'

    name = fields.Char('Name', compute='_compute_name', store=True)
    date = fields.Date('Shift Date', required=True, default=fields.Date.context_today)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center')
    production_id = fields.Many2one('mrp.production', string='Production Order')
    supervisor_one_id = fields.Many2one('res.users', string='Supervisor One')
    supervisor_two_id = fields.Many2one('res.users', string='Supervisor Two')
    running_mold = fields.Char('Running Mold')
    cavity = fields.Integer('Cavity')
    cycle_time = fields.Float('Cycle Time (sec)')
    hourly_target = fields.Float('Hourly Target', compute='_compute_hourly_target', store=True)

    slot_ids = fields.One2many('work.center.shift.slot', 'shift_id', string='Hour Slots')

    @api.depends('date', 'workcenter_id')
    def _compute_name(self):
        for rec in self:
            wc = rec.workcenter_id.display_name if rec.workcenter_id else ''
            rec.name = f"{rec.date or ''} {wc}".strip()

    @api.depends('cavity', 'cycle_time')
    def _compute_hourly_target(self):
        for rec in self:
            rec.hourly_target = (3600.0 / rec.cycle_time) * rec.cavity if rec.cavity and rec.cycle_time else 0.0


class WorkCenterShiftSlot(models.Model):
    _name = 'work.center.shift.slot'
    _description = 'Work Center Shift Slot'
    _order = 'sequence, id'

    shift_id = fields.Many2one('work.center.shift', string='Shift', required=True, ondelete='cascade')
    name = fields.Char('Slot', required=True, help='E.g., 08-09')
    sequence = fields.Integer('Sequence', default=10)
    start_time = fields.Float('Start (h)', help='Optional; decimal hours 8.0 = 08:00')
    end_time = fields.Float('End (h)', help='Optional; decimal hours 9.0 = 09:00')