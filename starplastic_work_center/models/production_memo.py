from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductionMemo(models.Model):
    _name = 'production.memo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Production Memo'

    date = fields.Date(default=fields.Date.context_today)
    production_id = fields.Many2one('mrp.production', required=True)
    pmemo_number = fields.Char(string='P-Memo Number')

    workcenter_id = fields.Many2one('mrp.workcenter', string='Machine Name')
    product_id = fields.Many2one(related='production_id.product_id', store=True, readonly=True)
    production_qty = fields.Float(related='production_id.product_qty', store=True, readonly=True, string='Production Qty')
    lot_id = fields.Many2one('stock.lot', compute='_compute_lot', store=True, readonly=True, string='Batch Number')
    unit_weight = fields.Float(related='product_id.weight_gm', store=True, readonly=True, string='Product Weight (gm)')
    rm_type = fields.Many2one(
        'product.product',
        string='RM Type',
        domain="[('purchase_ok','=',True),('sale_ok','=',False)]",
    )
    colour = fields.Char(string='Colour')
    cavity = fields.Integer(string='Mould Cavity')

    rm_lines = fields.One2many(
        'production.memo.rm.line',
        'memo_id',
        string="Raw Material Details"
    )

    rm_required_qty = fields.Float(compute='_compute_rm_summary', store=True, string='RM Required (Kg)')
    rm_issued_qty = fields.Float(compute='_compute_rm_summary', store=True, string='RM Issued (Kg)')
    rm_return_qty = fields.Float(compute='_compute_rm_summary', store=True, string='RM Returned (Kg)')
    rm_to_be_made = fields.Float(compute='_compute_rm_summary', store=True, readonly=True, string='RM To Be Made (Kg)')

    rm_loss_qty = fields.Float(compute='_compute_loss', store=True, string='RM Loss (Kg)')
    rm_loss_percent = fields.Float(compute='_compute_loss', store=True, string='RM Loss (%)')

    fg_qty = fields.Float(compute='_compute_fg', store=True, string='FG Quantity')
    fg_weight = fields.Float(compute='_compute_fg', store=True, string='FG Weight (Kg)')
    yield_percent = fields.Float(compute='_compute_loss', store=True, string='Yield (%)')

    # --------------------------------------------------
    # RM SUMMARY
    # --------------------------------------------------
    @api.depends(
        'rm_lines.bom_qty',
        'rm_lines.issued_qty',
        'rm_lines.return_qty'
    )
    def _compute_rm_summary(self):
        for rec in self:
            rm_required = sum(rec.rm_lines.mapped('bom_qty'))
            rm_issued = sum(rec.rm_lines.mapped('issued_qty'))
            rm_returned = sum(rec.rm_lines.mapped('return_qty'))

            # Correct consumed quantity
            rm_consumed = rm_issued - rm_returned

            rec.rm_required_qty = rm_required
            rec.rm_issued_qty = rm_issued
            rec.rm_return_qty = rm_returned

            rec.rm_to_be_made = rm_required - rm_consumed


    # --------------------------------------------------
    # FG
    # ------------------------------------------------__
    @api.depends('production_id')
    def _compute_fg(self):
        for rec in self:
            fg_nos = sum(rec.production_id.move_finished_ids.move_line_ids.mapped('qty_done'))
            rec.fg_qty = fg_nos
            rec.fg_weight = (fg_nos * rec.unit_weight) / 1000 if rec.unit_weight else 0.0

    # --------------------------------------------------
    # LOSS + YIELD
    # --------------------------------------------------
    @api.depends('rm_required_qty', 'rm_issued_qty', 'rm_return_qty')
    def _compute_loss(self):
        for rec in self:
            rm_consumed = rec.rm_issued_qty - rec.rm_return_qty
            loss = rm_consumed - rec.rm_required_qty

            rec.rm_loss_qty = max(loss, 0.0)

            rec.rm_loss_percent = (
                (rec.rm_loss_qty / rec.rm_issued_qty) * 100
                if rec.rm_issued_qty else 0.0
            )

            # Yield = 100 − Loss %
            rec.yield_percent = 100.0 - rec.rm_loss_percent

    # --------------------------------------------------
    # LOT
    # --------------------------------------------------
    @api.depends('production_id.move_finished_ids.move_line_ids.lot_id')
    def _compute_lot(self):
        for rec in self:
            rec.lot_id = rec.production_id.move_finished_ids.move_line_ids[:1].lot_id

    # --------------------------------------------------
    # RETURN RAW MATERIAL (PRODUCTION → STOCK)
    # --------------------------------------------------
    def action_return_rm(self):
        self.ensure_one()
        mo = self.production_id

        if mo.state != 'done':
            raise UserError("Production Order must be completed before returning raw material.")

        production_location = mo.location_dest_id
        stock_location = mo.location_src_id

        total_returned = 0.0

        moves = mo.move_raw_ids.filtered(lambda m: m.state == 'done')

        if not moves:
            raise UserError("No raw material consumption found.")

        for move in moves:
            issued_qty = sum(move.move_line_ids.mapped('qty_done'))
            if issued_qty <= 0:
                continue

            total_returned += issued_qty

            return_move = self.env['stock.move'].create({
                'name': f"RM Return - {mo.name}",
                'product_id': move.product_id.id,
                'product_uom_qty': issued_qty,
                'product_uom': move.product_uom.id,
                'location_id': production_location.id,
                'location_dest_id': stock_location.id,
                'origin': mo.name,
                'company_id': mo.company_id.id,
            })

            return_move._action_confirm()
            return_move._action_assign()

            for ml in return_move.move_line_ids:
                ml.qty_done = issued_qty

            return_move._action_done()

        if total_returned == 0:
            raise UserError("No issued quantity available to return.")

        # Update the return_qty field in the corresponding rm_lines
        for move in moves:
            rm_line = self.rm_lines.filtered(lambda line: line.rm_type == move.product_id)
            if rm_line:
                rm_line.return_qty += sum(move.move_line_ids.mapped('qty_done'))

        self.message_post(
            body=f"<b>Raw Material Returned Successfully</b><br/>Returned Qty: {total_returned}"
        )

        return True


# ======================================================
# RM LINE
# ======================================================
class ProductionMemoRMLine(models.Model):
    _name = 'production.memo.rm.line'
    _description = 'Production Memo Raw Material Line'

    memo_id = fields.Many2one(
        'production.memo',
        ondelete='cascade',
        required=True
    )

    rm_type = fields.Many2one(
        'product.product',
        string='Raw Material',
        domain="[('purchase_ok','=',True),('sale_ok','=',False)]",
        required=True
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        required=True
    )

    bom_qty = fields.Float(string='RM Required (BOM)')
    issued_qty = fields.Float(string='RM Issued')
    return_qty = fields.Float(string='RM Returned')
    rm_to_be_made = fields.Float(
        compute='_compute_rm_to_be_made',
        store=True,
        string='RM To Be Made'
    )

    loss_qty = fields.Float(
        compute='_compute_loss_qty',
        store=True,
        string='Loss (Kg)'
    )

    @api.depends('issued_qty', 'return_qty', 'bom_qty')
    def _compute_loss_qty(self):
        for line in self:
            rm_consumed = line.issued_qty - line.return_qty
            loss = rm_consumed - line.bom_qty
            line.loss_qty = max(loss, 0.0)

    @api.depends('bom_qty', 'issued_qty', 'return_qty')
    def _compute_rm_to_be_made(self):
        for line in self:
            consumed = line.issued_qty - line.return_qty
            to_be_made = line.bom_qty - consumed
            line.rm_to_be_made = max(to_be_made, 0.0)
