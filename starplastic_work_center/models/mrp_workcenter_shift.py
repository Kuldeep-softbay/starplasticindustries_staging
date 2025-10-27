from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WCShiftTemplate(models.Model):
    _name = 'wc.shift.template'
    _description = 'Shift Template (8-hour patterns)'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    code = fields.Selection(
        [('A', 'A'), ('B', 'B'), ('C', 'C')],
        required=True,
        help="Short code for the shift (A/B/C)."
    )
    start_hour = fields.Integer(string='Start Hour (0-23)', required=True)
    duration_hours = fields.Integer(string='Duration (hours)', default=8, required=True)
    sequence = fields.Integer(default=10, help="Ordering in lists")

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Shift code must be unique.'),
    ]

    @api.constrains('start_hour', 'duration_hours')
    def _check_shift_hours(self):
        for rec in self:
            if rec.duration_hours != 8:
                raise ValidationError(_("Shift duration must be exactly 8 hours."))
            if rec.start_hour < 0 or rec.start_hour > 23:
                raise ValidationError(_("Start hour must be between 0 and 23."))

    @api.onchange('code')
    def _onchange_shift_code(self):
        """Set start hour based on shift code"""
        if self.code == 'A':
            self.start_hour = 6  # 6 AM - 2 PM
        elif self.code == 'B':
            self.start_hour = 14  # 2 PM - 10 PM
        elif self.code == 'C':
            self.start_hour = 22  # 10 PM - 6 AM

    @api.constrains('code', 'start_hour')
    def _check_shift_time_validity(self):
        for rec in self:
            if rec.code == 'A' and rec.start_hour != 6:
                raise ValidationError(_("Shift A must start at 6 AM"))
            elif rec.code == 'B' and rec.start_hour != 14:
                raise ValidationError(_("Shift B must start at 2 PM"))
            elif rec.code == 'C' and rec.start_hour != 22:
                raise ValidationError(_("Shift C must start at 10 PM"))

    @api.depends('code')
    def _compute_start_hour(self):
        """Automatically set start hour based on shift code"""
        for rec in self:
            if rec.code == 'A':
                rec.start_hour = 6  # 6 AM to 2 PM
            elif rec.code == 'B':
                rec.start_hour = 14  # 2 PM to 10 PM
            elif rec.code == 'C':
                rec.start_hour = 22  # 10 PM to 6 AM

    def get_time_keys(self):
        """Return 8 time keys for the shift."""
        self.ensure_one()
        keys = []
        start = self.start_hour
        for i in range(8):  # 8-hour shift
            hour = (start + i) % 24
            next_hour = (hour + 1) % 24
            key = f"{hour:02d}-{next_hour:02d}"
            keys.append(key)
        return keys


class WCShift(models.Model):
    _name = 'work.center.shift'
    _description = 'Work Center Shift Instance'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(compute='_compute_name', store=True)
    production_id = fields.Many2one('mrp.production', required=True, tracking=True, ondelete='cascade')
    date = fields.Date(required=True, tracking=True)
    template_id = fields.Many2one('wc.shift.template', required=True, tracking=True)
    supervisor_one_id = fields.Many2one('res.users', string='Supervisor One', tracking=True)
    supervisor_two_id = fields.Many2one('res.users', string='Supervisor Two', tracking=True)

    # Setup fields
    mold_id = fields.Many2one('product.product', string='Running Mold', tracking=True)
    cavity = fields.Integer(string='Cavity', required=True, tracking=True)
    cycle_time_sec = fields.Float(string='Cycle Time (sec)', required=True, tracking=True)

    # Auto-target per hour from setup
    hourly_target_qty = fields.Float(string='Hourly Target (units/hr)', compute='_compute_hourly_target', store=True)

    # Links
    entry_ids = fields.One2many('work.center.hourly.entry', 'shift_id', string='Hourly Entries')

    # State (optional lifecycle for shift)
    state = fields.Selection(
        [('draft', 'Draft'), ('generated', 'Generated'), ('done', 'Done')],
        default='draft', required=True, tracking=True
    )

    _sql_constraints = [
        # Prevent duplicate shift per MO+date+template
        ('uniq_mo_date_template', 'unique(production_id, date, template_id)',
         'A shift already exists for this MO, date, and template.')
    ]

    @api.depends('production_id', 'date', 'template_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.production_id:
                parts.append(rec.production_id.name)
            if rec.date:
                parts.append(rec.date.strftime('%Y-%m-%d'))
            if rec.template_id and rec.template_id.code:
                parts.append(f"Shift {rec.template_id.code}")
            rec.name = " - ".join(parts) if parts else "Shift"

    @api.depends('cavity', 'cycle_time_sec')
    def _compute_hourly_target(self):
        for rec in self:
            target = 0.0
            if rec.cavity and rec.cycle_time_sec:
                # units per hour = (3600 / cycle_time_sec) * cavity
                target = round((3600.0 / rec.cycle_time_sec) * rec.cavity, 0)
            rec.hourly_target_qty = target

    def action_done(self):
        self.write({'state': 'done'})