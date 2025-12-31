from odoo import models, fields, tools


class PurchaseMonthlyReport(models.Model):
    _name = 'purchase.monthly.report'
    _description = 'Purchase Monthly Stock Report'
    _auto = False
    _rec_name = 'product_tmpl_id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        readonly=True
    )

    opening_stock = fields.Float(readonly=True)
    purchase_qty = fields.Float(readonly=True)
    issue_qty = fields.Float(readonly=True)
    closing_stock = fields.Float(readonly=True)

    month = fields.Date(string='Month', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW purchase_monthly_report AS (
                SELECT
                    row_number() OVER () AS id,
                    pt.id AS product_tmpl_id,
                    date_trunc('month', sm.date) AS month,

                    /* Opening Stock */
                    SUM(
                        CASE
                            WHEN sm.date < date_trunc('month', sm.date)
                            THEN sm.product_uom_qty *
                                CASE
                                    WHEN src.usage = 'internal' THEN -1
                                    WHEN dest.usage = 'internal' THEN 1
                                    ELSE 0
                                END
                            ELSE 0
                        END
                    ) AS opening_stock,

                    /* Purchase Qty */
                    SUM(
                        CASE
                            WHEN src.usage = 'supplier'
                            AND dest.usage = 'internal'
                            AND sm.date >= date_trunc('month', sm.date)
                            AND sm.date < date_trunc('month', sm.date) + INTERVAL '1 month'
                            THEN sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS purchase_qty,

                    /* Issue Qty */
                    SUM(
                        CASE
                            WHEN src.usage = 'internal'
                            AND dest.usage != 'internal'
                            AND sm.date >= date_trunc('month', sm.date)
                            AND sm.date < date_trunc('month', sm.date) + INTERVAL '1 month'
                            THEN sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS issue_qty,

                    /* Closing Stock */
                    SUM(
                        sm.product_uom_qty *
                        CASE
                            WHEN dest.usage = 'internal' THEN 1
                            WHEN src.usage = 'internal' THEN -1
                            ELSE 0
                        END
                    ) AS closing_stock

                FROM stock_move sm
                JOIN product_product pp ON sm.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN stock_location src ON sm.location_id = src.id
                JOIN stock_location dest ON sm.location_dest_id = dest.id

                WHERE sm.state = 'done'
                AND pt.purchase_ok = TRUE
                AND pt.sale_ok = FALSE

                GROUP BY pt.id, date_trunc('month', sm.date)
            )
        """)

