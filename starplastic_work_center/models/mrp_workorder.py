from odoo import api, models, fields

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'


    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string="Suitable Machine"
    )
    batch_number = fields.Char('Batch Number')
    expected_delivery_date = fields.Datetime('Expected Delivery Date')
