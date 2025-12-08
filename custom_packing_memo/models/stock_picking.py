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
    internal_batch_number = fields.Char(string='Internal Batch Number', readonly=True, copy=False)
    mfi_value = fields.Float(string='MFI Value')
    bags_type = fields.Char(string='Bags Type')
    number_of_bags = fields.Integer(string='Number of Bags')
    particulars = fields.Text(string='Particulars')
    remarks = fields.Text(string='Remarks')
    # party_id = fields.Many2one(
    #     'job.party.work',
    #     string='Job Party',
    #     ondelete='restrict',
    # )

    batch_number = fields.Char(string='Batch Number')
    removal_type = fields.Selection([
        ('normal', 'Normal'),
        ('other', 'Other')
    ], string='Removal Type', default='normal')

    @api.model
    def create(self, vals):
        """Auto-generate Internal Batch Number like R001-25-00001"""
        picking = super(StockPicking, self).create(vals)

        # Only generate if not already set
        if not picking.internal_batch_number:
            # --- Step 1: Get Raw Material Code from first product in move lines ---
            raw_material_code = False
            if picking.move_ids_without_package:
                first_move = picking.move_ids_without_package[0]
                if first_move.product_id and first_move.product_id.default_code:
                    raw_material_code = first_move.product_id.default_code.strip()

            # If no default code, fallback to RM00
            raw_material_code = raw_material_code or 'RM00'

            # --- Step 2: Get current year (2 digits) ---
            year = datetime.now().strftime('%y')

            # --- Step 3: Create prefix like R001-25 ---
            prefix = f"{raw_material_code}-{year}"

            # --- Step 4: Find last existing internal batch number for same prefix ---
            last_batch = self.search([
                ('internal_batch_number', 'like', f"{prefix}%")
            ], order='id desc', limit=1)

            if last_batch and last_batch.internal_batch_number:
                try:
                    last_seq = int(last_batch.internal_batch_number.split('-')[-1])
                    next_seq = str(last_seq + 1).zfill(5)
                except Exception:
                    next_seq = '00001'
            else:
                next_seq = '00001'

            # --- Step 5: Construct final batch number ---
            picking.internal_batch_number = f"{prefix}-{next_seq}"

        return picking
