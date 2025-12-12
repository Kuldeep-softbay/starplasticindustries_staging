from odoo import api, fields, models, _
from datetime import datetime

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

    @api.depends(
        'move_ids_without_package.product_id',
        'move_ids_without_package.product_id.default_code'
    )
    def _compute_internal_batch_number(self):
        for picking in self:
            if picking.internal_batch_number:
                continue

            raw_material_code = False
            if picking.move_ids_without_package:
                first_move = picking.move_ids_without_package[0]
                if first_move.product_id and first_move.product_id.default_code:
                    raw_material_code = first_move.product_id.default_code.strip()

            raw_material_code = raw_material_code or 'RM00'

            # two-digit year
            year = datetime.now().strftime('%y')

            # prefix without separators to match requested format (e.g. R00125)
            prefix = f"{raw_material_code}{year}"

            # search last record with same prefix and extract last sequence
            last = self.search(
                [('internal_batch_number', 'ilike', f"{prefix}%")],
                order='id desc',
                limit=1
            )

            if last and last.internal_batch_number:
                # assume last 5 chars are numeric sequence
                try:
                    last_seq = int(last.internal_batch_number[-5:])
                    next_seq = str(last_seq + 1).zfill(5)
                except Exception:
                    next_seq = '00001'
            else:
                next_seq = '00001'

            picking.internal_batch_number = f"{prefix}{next_seq}"
