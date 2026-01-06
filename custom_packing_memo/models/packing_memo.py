from odoo import models, fields, api


class PackingMemo(models.Model):
    _name = 'packing.memo'
    _description = 'Packing Memo'
    _order = 'id desc'

    name = fields.Char(default='New', copy=False)
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        required=True
    )
    sale_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True
    )
    line_ids = fields.One2many(
        'packing.memo.line',
        'memo_id',
        string='Products'
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'packing.memo'
            ) or 'New'
        return super().create(vals)


class PackingMemoLine(models.Model):
    _name = 'packing.memo.line'
    _description = 'Packing Memo Line'

    memo_id = fields.Many2one(
        'packing.memo',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        required=True
    )
    quantity = fields.Float(required=True)
