from odoo import api, fields, models, tools

class BatchClosingReport(models.Model):
    _name = "batch.closing.report"
    _description = "Batch Closing Report"
    _auto = False
    _order = "wo_date desc"

    lot_id = fields.Many2one('stock.lot')
    wo_date = fields.Date(string="W.O Date")
    product_id = fields.Many2one('product.product', string="Item")

    black_spot = fields.Float(string="Black Spot")
    cut_pcs = fields.Float(string="Cut PCS")
    short_qty = fields.Float(string="Short Quantity")

    wo_qty = fields.Float(string="W.O Quantity")
    production_qty = fields.Float(string="Production Quantity")
    dispatch_qty = fields.Float(string="Dispatch Quantity")

    month = fields.Char(string="Month")


    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'batch_closing_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW batch_closing_report AS (
                SELECT
                    row_number() OVER() AS id,

                    lot.id AS lot_id,
                    pp.id AS product_id,

                    mo.date_start::date AS wo_date,
                    TO_CHAR(mo.date_start, 'YYYY-MM') AS month,

                    /* Scrap */
                    COALESCE((
                        SELECT SUM(scrap_qty)
                        FROM stock_scrap s
                        WHERE s.lot_id = lot.id
                    ), 0) AS black_spot,

                    0.0 AS cut_pcs,
                    0.0 AS short_qty,

                    COALESCE(mo.wo_qty, 0) AS wo_qty,
                    COALESCE(mo.production_qty, 0) AS production_qty,

                    /* Dispatch */
                    COALESCE((
                        SELECT SUM(sml.quantity)
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sm.id = sml.move_id
                        JOIN stock_picking sp ON sp.id = sm.picking_id
                        WHERE sml.lot_id = lot.id
                        AND sp.state = 'done'
                        AND sp.picking_type_id IN (
                            SELECT id FROM stock_picking_type WHERE code = 'outgoing'
                        )
                    ), 0) AS dispatch_qty,

                    /* ✅ ONLY INTERNAL STOCK */
                    COALESCE((
                        SELECT SUM(sq.quantity)
                        FROM stock_quant sq
                        JOIN stock_location sl ON sl.id = sq.location_id
                        WHERE sq.lot_id = lot.id
                        AND sl.usage = 'internal'
                    ), 0) AS remaining_qty

                FROM stock_lot lot

                LEFT JOIN product_product pp
                    ON pp.id = lot.product_id

                LEFT JOIN LATERAL (
                    SELECT mo.*
                    FROM mrp_production mo
                    JOIN stock_move sm ON sm.production_id = mo.id
                    JOIN stock_move_line sml ON sml.move_id = sm.id
                    WHERE sml.lot_id = lot.id
                    LIMIT 1
                ) mo ON TRUE

                /* ✅ FINAL FILTER */
                WHERE COALESCE((
                    SELECT SUM(sq.quantity)
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id = sq.location_id
                    WHERE sq.lot_id = lot.id
                    AND sl.usage = 'internal'
                ), 0) = 0
            )
        """)

