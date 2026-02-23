from odoo import models, fields, api
from odoo.exceptions import UserError

class MrpRmReturnLine(models.Model):
    _name = 'mrp.rm.return.line'
    _description = 'RM Return Line'

    production_id = fields.Many2one(
        'mrp.production',
        ondelete='cascade'
    )

    date = fields.Date(
        string="Return Date",
        default=fields.Date.context_today,
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string="Raw Material",
        required=True,
        domain="[('id', 'in', allowed_product_ids)]"
    )

    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', store=True)


    allowed_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_allowed_products'
    )

    location_id = fields.Many2one('stock.location', required=True)
    quantity = fields.Float(required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    @api.depends('production_id')
    def _compute_allowed_products(self):
        for rec in self:
            if rec.production_id:
                rec.allowed_product_ids = rec.production_id.move_raw_ids.mapped('product_id')
            else:
                rec.allowed_product_ids = False

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ['quantity', 'state']):
            for rec in self:
                if rec.production_id:
                    rec.production_id._compute_rm_return_qty()
                    rec.production_id._compute_pmemo()
        return res

    def create(self, vals):
        record = super().create(vals)
        if record.production_id:
            record.production_id._compute_rm_return_qty()
            record.production_id._compute_pmemo()
        return record
