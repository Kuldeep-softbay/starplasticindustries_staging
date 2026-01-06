from odoo import api, fields, models, _
from datetime import datetime

class ProductTemplate(models.Model):
    _inherit = "product.product"

    batch_number = fields.Char(string='Batch Number', help="Batch number associated with the product.")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    invoice_number = fields.Char(string="Invoice Number")
    rm_add_date = fields.Date(string="Date")
    row_type = fields.Selection([
        ('hd_injection', 'HD Injection'),
        ('injection', 'Injection'),
        ('hd_blowing', 'HD Blowing'),
        ('other', 'Other')
    ], string='Row Type', default='other')
    supplier_batch_number = fields.Char(string='Supplier Batch Number')
    internal_batch_number = fields.Char(
        string='Internal Batch Number',
        readonly=True,
        copy=False,
        compute='_compute_internal_batch_number',
        store=True,
    )
    mfi_value = fields.Float(string='MFI Value')
    bags_type = fields.Char(string='Bags Type')
    number_of_bags = fields.Integer(string='Number of Bags')
    particulars = fields.Text(string='Particulars')
    remarks = fields.Text(string='Remarks')
    party_id = fields.Many2one('job.party.work', string='Party')

    batch_number = fields.Char(string='Batch Number')
    removal_type = fields.Selection([
        ('normal', 'Normal'),
        ('other', 'Other')
    ], string='Removal Type', default='normal')

    total_product_qty = fields.Float(
    string='Total Quantity',
    compute='_compute_total_product_qty',
    readonly=True)
    actual_dispatch_date = fields.Date(
        string='Actual Despatch Date',
        help="The date when the picking was completed.")
    exp_dis_date = fields.Date(
        string="Expected Dispatch Date",
        tracking=True,
    )
    rejection_reason_id = fields.Many2one(
        'rejection.reason',
        string='Rejection Reason'
    )
    packing_memo_count = fields.Integer(
        compute='_compute_packing_memo_count'
    )

    def _compute_packing_memo_count(self):
        for picking in self:
            picking.packing_memo_count = self.env[
                'packing.memo'
            ].search_count([
                ('picking_id', '=', picking.id)
            ])

    def action_open_packing_memo_wizard(self):
        sale_id = False
        if self.origin:
            sale = self.env['sale.order'].search([('name', '=', self.origin)], limit=1)
            if sale:
                sale_id = sale.id

        ctx = {'default_picking_id': self.id}
        if sale_id:
            ctx['default_sale_id'] = sale_id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'packing.memo.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_sale_id': sale_id,
            }
        }

    @api.depends('move_ids.product_qty')
    def _compute_total_product_qty(self):
        for picking in self:
            picking.total_product_qty = sum(picking.move_ids.mapped('product_qty'))

    @api.depends(
        'picking_type_id.code',
        'move_ids_without_package.product_id',
        'move_ids_without_package.product_id.default_code'
    )
    def _compute_internal_batch_number(self):
        for picking in self:
            if picking.internal_batch_number:
                continue

            if not picking.picking_type_id or picking.picking_type_id.code != 'incoming':
                continue

            raw_material_code = 'RM00'

            if picking.move_ids_without_package:
                first_move = picking.move_ids_without_package[0]
                product = first_move.product_id

                if product and product.default_code:
                    raw_material_code = product.default_code.strip()[:4]

            year = datetime.now().strftime('%y')

            prefix = f"{raw_material_code}{year}"

            last = self.search(
                [('internal_batch_number', 'ilike', f"{prefix}%")],
                order='id desc',
                limit=1
            )

            if last and last.internal_batch_number:
                try:
                    last_seq = int(last.internal_batch_number[-4:])
                    next_seq = str(last_seq + 1).zfill(4)
                except ValueError:
                    next_seq = '0001'
            else:
                next_seq = '0001'

            picking.internal_batch_number = f"{prefix}{next_seq}"
