from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class WorkCenterHourlyEntry(models.Model):
    _name = 'work.center.hourly.entry'
    _description = 'Work Center Hourly Entry'
    _order = 'production_id, id'

    production_id = fields.Many2one('mrp.production', string='Production Order', ondelete='cascade', tracking=True)

    def _fmt_ampm(self, hour_24):
        suffix = "AM" if hour_24 < 12 else "PM"
        hour_12 = 12 if hour_24 % 12 == 0 else hour_24 % 12
        return f"{hour_12} {suffix}"
    
    def _selection_hour_slots(self):
        """Return selection options. If shift_id present in context, return only that shift's slots;
        otherwise return all 24 slots so the field is always selectable."""
        ctx = self.env.context or {}
        shift_id = ctx.get('default_shift_id') or ctx.get('shift_id')

        def all_slots():
            slots = []
            for h in range(24):
                next_h = (h + 1) % 24
                key = f"{h:02d}-{next_h:02d}"
                label = f"{self._fmt_ampm(h)} - {self._fmt_ampm(next_h)}"
                slots.append((key, label))
            return slots

        if not shift_id:
            return all_slots()

        shift = self.env['work.center.shift'].browse(shift_id)
        if not shift.exists() or not shift.template_id:
            return all_slots()

        start_hour = shift.template_id.start_hour
        duration = shift.template_id.duration_hours or 8
        slots = []
        for i in range(duration):
            hour = (start_hour + i) % 24
            next_hour = (hour + 1) % 24
            key = f"{hour:02d}-{next_hour:02d}"
            label = f"{self._fmt_ampm(hour)} - {self._fmt_ampm(next_hour)}"
            slots.append((key, label))
        return slots

    @api.onchange('shift_id')
    def _onchange_shift_id(self):
        """When shift is selected, set time to first available slot of that shift if current time is invalid;
        clear time if no shift."""
        if not self.shift_id or not self.shift_id.template_id:
            self.time = False
            return
        keys = self.shift_id.template_id.get_time_keys()
        if not keys:
            self.time = False
            return
        if self.time not in keys:
            # set to first valid slot to guide user
            self.time = keys[0]
        return {'domain': {'time': []}}  # Clear any existing domain

    time = fields.Selection(
        selection='_selection_hour_slots',
        string='Hour Slot',
        required=True,
        tracking=True
    )

    production_id = fields.Many2one('mrp.production', string='Production Order', ondelete='cascade', tracking=True)
    shift_id = fields.Many2one('work.center.shift', string='Shift', ondelete='cascade', index=True)
    target_qty = fields.Float('Target Quantity', tracking=True)

    operator_one_id = fields.Many2one('res.users', string='Operator One', tracking=True)
    operator_two_id = fields.Many2one('res.users', string='Operator Two', tracking=True)

    shut_down = fields.Boolean(string='Shut Down', default=False, tracking=True)

    unit_weight = fields.Float('Unit Weight')

    reason_line_ids = fields.One2many(
        'work.center.hourly.entry.reason.line',
        'hourly_entry_id',
        string='Downtime Reasons',
    )

    produced_weight_kg = fields.Float('Produced kg', tracking=True)
    produced_qty_number = fields.Float('Produced Nos', tracking=True)
    reject_weight_kg = fields.Float('Rejection kg', tracking=True)
    reject_qty_number = fields.Float('Rejection Nos', tracking=True)
    rejection_reason = fields.Char('Rejection Reason', tracking=True)
    actual_cycle_time = fields.Float('Actual Cycle Time (sec)', tracking=True)
    qc_check = fields.Boolean('Product Quality Check', tracking=True)

    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done')],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    @api.constrains('shut_down', 'reason_line_ids')
    def _check_downtime_requirements(self):
        for rec in self:
            if rec.shut_down and not rec.reason_line_ids:
                raise ValidationError(_("Please add at least one downtime reason (Has Downtime is checked)."))

    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def action_confirm(self):
        for rec in self:
            if rec.shut_down and not rec.reason_line_ids:
                raise ValidationError(_("Cannot confirm: add at least one downtime reason."))
        self.write({'state': 'confirmed'})

    def action_done(self):
        for rec in self:
            if rec.shut_down and not rec.reason_line_ids:
                raise ValidationError(_("Cannot mark done: add at least one downtime reason."))
        self.write({'state': 'done'})

    @api.model
    def create(self, vals):
        # Auto-assign the next available slot if not provided
        if not vals.get('time'):
            # Use context or vals to get production_id and shift_id
            production_id = vals.get('production_id') or self._context.get('default_production_id')
            shift_id = vals.get('shift_id') or self._context.get('default_shift_id')
            slots = self.with_context(default_production_id=production_id, default_shift_id=shift_id)._selection_hour_slots()
            if slots:
                vals['time'] = slots[0][0]
        return super().create(vals)

    @api.onchange('shift_id', 'time')
    def _onchange_shift_time(self):
        """Validate and filter time slots based on shift"""
        if self.shift_id and self.shift_id.template_id:
            valid_slots = self.shift_id.template_id.get_time_keys()
            if self.time and self.time not in valid_slots:
                self.time = False
                return {
                    'warning': {
                        'title': 'Invalid Time Slot',
                        'message': 'Selected time slot is not within shift hours.'
                    }
                }
    
    @api.constrains('shift_id', 'time')
    def _check_time_slot(self):
        """Ensure time slot is within shift hours"""
        for rec in self:
            if rec.shift_id and rec.shift_id.template_id and rec.time:
                valid_slots = rec.shift_id.template_id.get_time_keys()
                if rec.time not in valid_slots:
                    raise ValidationError(_("Selected time slot must be within shift hours."))

                # Check for duplicate entries
                domain = [
                    ('shift_id', '=', rec.shift_id.id),
                    ('time', '=', rec.time),
                    ('id', '!=', rec.id)
                ]
                if rec.production_id:
                    domain.append(('production_id', '=', rec.production_id.id))
                
                if self.search_count(domain):
                    raise ValidationError(_("This time slot is already taken for this shift."))

class WorkCenterHourlyEntryReasonLine(models.Model):
    _name = 'work.center.hourly.entry.reason.line'
    _description = 'Hourly Entry Reason (Persistent)'
    _order = 'id'

    hourly_entry_id = fields.Many2one(
        'work.center.hourly.entry',
        string='Hourly Entry',
        required=True,
        ondelete='cascade',
    )
    reason_id = fields.Many2one('wc.downtime.reason', string='Reason')
    duration_minutes = fields.Float('Duration (min)')
    sub_reason_id = fields.Many2one(
        'wc.downtime.subreason',
        string='Sub Reason',
        domain="[('reason_id','=',reason_id)]",
    )
    actual_time_minutes = fields.Float('Actual Time (min)')