from odoo import api, fields, models


class ReorderPlanningWizard(models.TransientModel):
    _name = 'reorder.planning.wizard'
    _description = 'Wizard to compute reorder planning'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    months = fields.Integer(string='Analysis Period', default=3)
    safety_factor = fields.Float(string='Safety Margin (%)', default=20.0)
    product_category_id = fields.Many2one('product.category', string='Product Category')
    min_avg_threshold = fields.Float(string='Minimum Monthly Consumption', default=0.0)

    def _default_end_date(self):
        return fields.Date.context_today(self)

    end_date = fields.Date(string='End Date', default=_default_end_date)

    def action_compute(self):
        """
        Compute and store reorder planning results, then open the result view.

        Always show ONLY the data computed in this run (no old records).
        """
        self.ensure_one()

        # Build product domain using selected product category (and its children)
        product_domain_for_products = []
        if self.product_category_id:
            product_domain_for_products.append(
                ('categ_id', 'child_of', self.product_category_id.id)
            )

        # Execute main computation logic in reorder.planning model
        res = self.env['reorder.planning'].compute_and_store(
            months=self.months,
            safety_factor=self.safety_factor,
            product_domain=product_domain_for_products,
            end_date=self.end_date,
            company_id=None,
            min_avg_threshold=self.min_avg_threshold,
        )

        try:
            action = self.env.ref('reorder_planning.action_reorder_analysis').read()[0]
        except Exception:
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Reorder Planning',
                'res_model': 'reorder.planning',
                'view_mode': 'list,pivot,graph',
                'target': 'current',
            }

        # Extract newly created IDs and computation date from compute_and_store result
        created_ids = []
        comp_dt_str = False
        if isinstance(res, dict):
            created_ids = res.get('ids', []) or []
            comp_dt_str = res.get('computation_date')

        # Always restrict to **this run only**
        if created_ids:
            # Show only the records just created
            action['domain'] = [('id', 'in', created_ids)]
        elif comp_dt_str:
            # No records created (e.g. everything filtered by min_avg_threshold)
            # → show an empty result for this computation_date
            action['domain'] = [('computation_date', '=', comp_dt_str)]
        else:
            # Fallback: show nothing, but never old data
            action['domain'] = [('id', '=', 0)]

        action['res_model'] = 'reorder.planning'
        return action
