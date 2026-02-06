from odoo import models, fields, tools


class ProductEfficiencySummary(models.Model):
    _name = 'product.efficiency.summary'
    _description = 'Product Efficiency Summary Report'
    _auto = False

    product_id = fields.Many2one('product.product', string='Item')

    avg_weight = fields.Float(string='Avg Weight')
    cavity = fields.Integer(string='No of Cavity')
    std_production = fields.Float(string='Std Production')
    std_cycle_time = fields.Float(string='Std Cycle Time')

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

                    pp.id AS product_id,

                    pt.weight AS avg_weight,
                    wcs.cavity AS cavity,

                    (wcs.cavity * 60) AS std_production,
                    0.0 AS std_cycle_time,

                    0.0 AS total_production_nos,
                    SUM(wcs.unit_waight) AS total_production_kg,

                    0.0 AS production_minutes,
                    0.0 AS production_hours,

                    0.0 AS actual_production_per_hour,
                    0.0 AS efficiency

                FROM work_center_shift wcs
                JOIN mrp_production mo ON mo.id = wcs.production_id
                JOIN product_product pp ON pp.id = mo.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id

                GROUP BY
                    pp.id,
                    pt.weight,
                    wcs.cavity
            )
        """)
