from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    reorder_lead_time = fields.Integer(string='Reorder Lead Time (days)', default=7,
                                       help='Default lead time in days used to compute reorder point')
    reorder_min_qty = fields.Float(string='Min Order Qty', default=0.0,
                                   help='Minimum order quantity suggested')
    reorder_lot_size = fields.Float(string='Lot Size / Order Multiple', default=1.0,
                                    help='Round up suggested orders to multiples of this value')
