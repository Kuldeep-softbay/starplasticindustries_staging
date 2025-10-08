from odoo import api, models, fields
from odoo.exceptions import ValidationError


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    name = fields.Char(string="Mould Name", required=True)
    workcenter_ids = fields.Many2many(
        'mrp.workcenter',
        'workcenter_id',
        string="Suitable Machines"
    )

    cavity = fields.Integer(string="Cavity", default=1, help="Number of cavities")
    standard_cycle_time = fields.Float(string="Std Cycle Time")
    standard_cycle_time_hourly = fields.Float(
        string="Std Cycle Time band for hourly entery")
    standard_production_per_hour = fields.Float(
        string="Std Production per Hour")
    cycle_time_tolerance = fields.Float(string="Cycle Time Tolerance (%)")

    @api.constrains('cavity', 'standard_cycle_time', 'cycle_time_tolerance')
    def _check_positive_values(self):
        for rec in self:
            if rec.cavity is not None and rec.cavity < 1:
                raise ValidationError("Cavity must be at least 1.")
            if rec.standard_cycle_time is not None and rec.standard_cycle_time < 0:
                raise ValidationError("Standard cycle time must be non-negative.")
            if rec.cycle_time_tolerance is not None and rec.cycle_time_tolerance < 0:
                raise ValidationError("Cycle time tolerance must be non-negative.")
