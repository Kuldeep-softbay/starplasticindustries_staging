from odoo import models, fields, tools

class RMLossReport(models.Model):
    _name = 'rm.loss.report'
    _description = 'RM Loss Report'
    _auto = False
    _rec_name = 'pmemo_number'

    date = fields.Date()
    product_id = fields.Many2one('product.product', string='Item')
    rm_type = fields.Many2one('product.product', string='RM Type')
    colour = fields.Char(string='Color')
    pmemo_number = fields.Char(string='P-Memo No')
    lot_id = fields.Many2one('stock.lot', string='Batch No')
    loss_kg = fields.Float(string='Loss (Kg)')
    loss_percent = fields.Float(string='Loss (%)')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'rm_loss_report')
        self.env.cr.execute("""
            CREATE VIEW rm_loss_report AS (
                SELECT
                    row_number() OVER() AS id,
                    pm.date AS date,
                    pm.product_id AS product_id,
                    pm.rm_type AS rm_type,
                    pm.colour AS colour,
                    pm.pmemo_number AS pmemo_number,
                    pm.lot_id AS lot_id,
                    pm.rm_loss_qty AS loss_kg,
                    pm.rm_loss_percent AS loss_percent
                FROM production_memo pm
                LEFT JOIN mrp_production mo ON mo.id = pm.production_id
            )
        """)
