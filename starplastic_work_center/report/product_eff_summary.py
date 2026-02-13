from odoo import models, fields, tools


class ProductEfficiencySummary(models.Model):
    _name = 'product.efficiency.summary'
    _description = 'Product Efficiency Summary Report'
    _auto = False
    _order = 'date desc'

    date = fields.Date(string='Date')

    product_id = fields.Many2one('product.product', string='Item')

    avg_weight = fields.Float(string='Avg Weight')
    cavity = fields.Integer(string='No of Cavity')

    std_production = fields.Float(string='Std Production / Hour')
    std_cycle_time = fields.Float(string='Std Cycle Time (Sec)')

    total_production_nos = fields.Float(string='Total Production Nos')
    total_production_kg = fields.Float(string='Total Production KG')

    production_minutes = fields.Float(string='Production Minutes')
    production_hours = fields.Float(string='Production Hours')

    actual_production_per_hour = fields.Float(
        string='Actual Production Nos / Hour'
    )

    efficiency = fields.Float(string='Efficiency (%)')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'product_efficiency_summary')
        self.env.cr.execute("""
            CREATE VIEW product_efficiency_summary AS (
                SELECT
                    row_number() OVER () AS id,

                    DATE(whe.create_date) AS date,

                    pp.id AS product_id,

                    pt.weight AS avg_weight,
                    mo.cavity AS cavity,

                    wo.duration_expected AS std_cycle_time,

                    /* Standard Production Per Hour */
                    CASE
                        WHEN wo.duration_expected IS NOT NULL
                             AND wo.duration_expected != 0
                             AND mo.cavity IS NOT NULL
                             AND mo.cavity != 0
                        THEN
                            (3600.0 / wo.duration_expected) * mo.cavity
                        ELSE 0
                    END AS std_production,

                    SUM(whe.produced_qty_number) AS total_production_nos,
                    SUM(whe.produced_weight_kg) AS total_production_kg,

                    /* Production Minutes */
                    SUM(
                        (whe.produced_qty_number * wo.duration_expected)
                        / NULLIF(mo.cavity, 0)
                    ) / 60.0 AS production_minutes,

                    /* Production Hours */
                    SUM(
                        (whe.produced_qty_number * wo.duration_expected)
                        / NULLIF(mo.cavity, 0)
                    ) / 3600.0 AS production_hours,

                    /* Actual Production Per Hour */
                    CASE
                        WHEN SUM(
                            (whe.produced_qty_number * wo.duration_expected)
                            / NULLIF(mo.cavity, 0)
                        ) > 0
                        THEN
                            SUM(whe.produced_qty_number) /
                            (
                                SUM(
                                    (whe.produced_qty_number * wo.duration_expected)
                                    / NULLIF(mo.cavity, 0)
                                ) / 3600.0
                            )
                        ELSE 0
                    END AS actual_production_per_hour,

                    /* Efficiency % */
                    CASE
                        WHEN wo.duration_expected IS NOT NULL
                             AND wo.duration_expected != 0
                             AND mo.cavity IS NOT NULL
                             AND mo.cavity != 0
                        THEN
                            (
                                (
                                    SUM(whe.produced_qty_number) /
                                    NULLIF(
                                        (
                                            SUM(
                                                (whe.produced_qty_number * wo.duration_expected)
                                                / NULLIF(mo.cavity, 0)
                                            ) / 3600.0
                                        ), 0
                                    )
                                )
                                /
                                ((3600.0 / wo.duration_expected) * mo.cavity)
                            ) * 100
                        ELSE 0
                    END AS efficiency

                FROM work_center_hourly_entry whe

                LEFT JOIN mrp_production mo
                    ON mo.id = whe.production_id

                LEFT JOIN mrp_workorder wo
                    ON wo.production_id = mo.id

                LEFT JOIN product_product pp
                    ON pp.id = mo.product_id

                LEFT JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id

                GROUP BY
                    DATE(whe.create_date),
                    pp.id,
                    pt.weight,
                    mo.cavity,
                    wo.duration_expected
            )
        """)
