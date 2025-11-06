from odoo import api, models, fields

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string="Suitable Machine"
    )
    batch_number = fields.Char('Batch Number')
    expected_delivery_date = fields.Datetime('Expected Delivery Date')
    customer_po_number = fields.Char('CO Number')
    customer_order_quantity = fields.Float('CO Quantity')
    actual_delivery_date = fields.Datetime('Actual Delivery Date')
    remark = fields.Text('Remark')
    produced_quantity = fields.Float('Produced Quantity')
    remaining_quantity = fields.Float('Remaining Quantity')
    planned_start_date = fields.Datetime('Planned Start Date')
    planned_end_date = fields.Datetime('Planned End Date')
    creation_date = fields.Datetime('W.O Date')

    @api.model
    def create(self, vals):
        """Assign creation_date automatically on record creation."""
        if not vals.get('creation_date'):
            vals['creation_date'] = fields.Datetime.now()
        return super(MrpWorkorder, self).create(vals)


class JobPartyWork(models.Model):
    _name = 'job.party.work'
    _description = 'Job Party Work'
    
    name = fields.Char('Job Party Name')
    work_type = fields.Selection([
        ('inward', 'Inward'),
        ('outword', 'Outword')], string='Type')
    remark = fields.Text('Remark')
    # party_ids = fields.One2many(
    #     'stock.picking',
    #     'party_id',
    #     string='Related Pickings'
    # )