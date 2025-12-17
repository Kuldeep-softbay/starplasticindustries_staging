from odoo import api, fields, models
from datetime import timedelta
import math


class ReorderPlanning(models.Model):
    _name = 'reorder.planning'
    _description = 'Stored Reorder Planning'
    _order = 'computation_date desc'

    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id', store=True)
    categ_id = fields.Many2one('product.category', related='product_id.categ_id', store=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', store=True)
    sum_last_n = fields.Float('Historical Consumption')
    avg_month = fields.Float('Average Monthly Consumption')
    on_hand_qty = fields.Float('On-Hand Quantity')
    reorder_point = fields.Float('Reorder Point')
    required_qty = fields.Float('Quantity to Replenish')
    suggested_qty = fields.Float('Suggested Order Quantity')
    lead_time_days = fields.Float('Lead Time (Days)')
    computation_date = fields.Datetime(index=True, default=fields.Datetime.now)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        index=True,
        default=lambda self: self.env.company
    )

    # ---------------------------------------------------------------------
    # 1. PURCHASE LEAD TIME (PO Order → Incoming Picking Done)
    # ---------------------------------------------------------------------
    def _get_avg_purchase_lead_time(self, product, start_str, end_str):
        """Average (Incoming Picking Done Date - PO date_approve/date_order)
        based on purchase.order.line and related incoming pickings.
        """
        POL = self.env['purchase.order.line'].sudo()
        lines = POL.search([
            ('product_id', '=', product.id),
            ('order_id.state', 'in', ('purchase', 'done')),
            ('order_id.date_approve', '>=', start_str),
            ('order_id.date_approve', '<=', end_str),
        ], order='id desc', limit=100)

        lead_times = []

        for line in lines:
            po = line.order_id
            po_date = po.date_approve or po.date_order
            if not po_date:
                continue

            # All incoming pickings linked to this PO
            pickings = po.picking_ids.filtered(
                lambda p: p.state == 'done' and p.picking_type_code == 'incoming'
            )

            if not pickings:
                continue

            # Earliest done date among incoming pickings
            grn_dates = (
                pickings.mapped('date_done')
                or pickings.mapped('scheduled_date')
                or pickings.mapped('date')
            )
            grn_date = grn_dates and min(grn_dates) or False

            if not grn_date:
                continue

            delta_days = (grn_date - po_date).total_seconds() / 86400.0
            if delta_days >= 0:
                lead_times.append(delta_days)

        # Fallback: old stock.move based approach if no lines found
        if not lead_times:
            Move = self.env['stock.move'].sudo()
            move_domain = [
                ('state', '=', 'done'),
                ('date', '>=', start_str),
                ('date', '<=', end_str),
                ('product_id', '=', product.id),
                ('picking_id.picking_type_code', '=', 'incoming'),
            ]
            moves = Move.search(move_domain, order='date desc', limit=50)
            PurchaseOrder = self.env['purchase.order'].sudo()

            for m in moves:
                po = False

                if 'purchase_line_id' in m._fields and m.purchase_line_id:
                    po = m.purchase_line_id.order_id

                if not po and 'purchase_id' in m.picking_id._fields and m.picking_id.purchase_id:
                    po = m.picking_id.purchase_id

                if not po and m.picking_id.origin:
                    po = PurchaseOrder.search([('name', '=', m.picking_id.origin)], limit=1)

                if not po:
                    continue

                po_date = po.date_approve or po.date_order
                grn_date = m.date
                if po_date and grn_date:
                    delta_days = (grn_date - po_date).total_seconds() / 86400.0
                    if delta_days >= 0:
                        lead_times.append(delta_days)

        return sum(lead_times) / len(lead_times) if lead_times else False

    # ---------------------------------------------------------------------
    # 2. MANUFACTURING LEAD TIME (MO Start → MO Finished)
    # ---------------------------------------------------------------------
    def _get_avg_manufacturing_lead_time(self, product, start_str, end_str):
        """
        Average manufacturing lead time:

        From:
            MO start (date_start / date_planned_start / date_finished)
        To:
            Customer delivery (OUTGOING picking done date) for the SAME product
            linked to that MO / Sale Order.

        Steps:
        - Find done MOs for the product in the given date range
        - For each MO, locate related OUTGOING pickings (deliveries)
        - Filter pickings that actually deliver this product
        - Compute (delivery_date - mo_start_date) in days
        - Return average of all such deltas
        """
        Production = self.env['mrp.production'].sudo()
        Picking = self.env['stock.picking'].sudo()

        # MOs in the period (using date_finished as reference)
        domain = [
            ('state', '=', 'done'),
            ('product_id', '=', product.id),
            ('date_finished', '>=', start_str),
            ('date_finished', '<=', end_str),
        ]
        mos = Production.search(domain, order='date_finished desc', limit=50)
        lead_times = []

        for mo in mos:
            # 1) Start date of manufacturing
            start = mo.date_start or mo.date_planned_start or mo.date_finished
            if not start:
                continue

            deliveries = Picking.browse()

            # 2) Best link: procurement group on MO
            if mo.procurement_group_id:
                deliveries = Picking.search([
                    ('group_id', '=', mo.procurement_group_id.id),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', '=', 'done'),
                ])

            # 3) Fallback: via sale_line_id → sale.order → picking_ids
            if not deliveries and 'sale_line_id' in mo._fields and mo.sale_line_id:
                so = mo.sale_line_id.order_id
                deliveries = so.picking_ids.filtered(
                    lambda p: p.state == 'done' and p.picking_type_code == 'outgoing'
                )

            # 4) Fallback: via origin text (SO name, MO name, etc.)
            if not deliveries and mo.origin:
                deliveries = Picking.search([
                    ('origin', '=', mo.origin),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', '=', 'done'),
                ])

            if not deliveries:
                continue

            # 5) Keep only deliveries that actually move this product
            deliveries = deliveries.filtered(
                lambda p: any(
                    mv.product_id.id == product.id
                    for mv in p.move_ids_without_package
                )
            )
            if not deliveries:
                continue

            # 6) Get the earliest delivery date among those pickings
            deliv_dates = (
                deliveries.mapped('date_done')
                or deliveries.mapped('scheduled_date')
                or deliveries.mapped('date')
            )
            finish = deliv_dates and min(deliv_dates) or False
            if not finish:
                continue

            # 7) Compute lead time in days (delivery - MO start)
            delta_days = (finish - start).total_seconds() / 86400.0
            if delta_days >= 0:
                lead_times.append(delta_days)

        return sum(lead_times) / len(lead_times) if lead_times else False


    # ---------------------------------------------------------------------
    # Helper: determine category type (fg / rm / cons) using category name
    # ---------------------------------------------------------------------
    def _get_category_type_from_name(self, categ):
        """
        Decide if category behaves like:
        - 'rm'   → Raw Material
        - 'cons' → Consumable
        - 'fg'   → Finished Good (default)
        """
        if not categ:
            return 'fg'

        name = (categ.display_name or categ.name or '').strip().lower()

        if name in ('raw material', 'rm') or name.startswith('rm '):
            return 'rm'
        if name in ('consumable',) or name.startswith('cons'):
            return 'cons'
        if name in ('finished good', 'finished goods', 'fg'):
            return 'fg'

        # Default if nothing matches
        return 'fg'

    # ---------------------------------------------------------------------
    # 3. MAIN COMPUTE FUNCTION
    # ---------------------------------------------------------------------
    @api.model
    def compute_and_store(
        self,
        months=3,
        safety_factor=20.0,
        product_domain=None,
        end_date=None,
        company_id=None,
        min_avg_threshold=0.0
    ):
        Product = self.env['product.product'].sudo().with_context(prefetch_fields=False)

        # End date
        end_dt = fields.Datetime.to_datetime(end_date or fields.Datetime.now())
        try:
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
        except Exception:
            pass

        # Start date = N months before
        start_dt = end_dt - timedelta(days=30 * months)
        start_str = fields.Datetime.to_string(start_dt)
        end_str = fields.Datetime.to_string(end_dt)
        comp_dt_str = fields.Datetime.to_string(end_dt)

        # Product domain
        prod_domain = [('active', '=', True)]
        if product_domain:
            prod_domain += product_domain
        if company_id:
            prod_domain.append(('product_tmpl_id.company_id', '=', company_id))

        products = Product.search(prod_domain)
        StockMove = self.env['stock.move'].sudo()

        new_records = []
        product_ids_for_create = []

        for p in products:

            # ---------------------------------------------------------
            # Get past consumption
            # ---------------------------------------------------------
            moves = StockMove.search([
                ('state', '=', 'done'),
                ('date', '>=', start_str),
                ('date', '<=', end_str),
                ('product_id', '=', p.id)
            ])

            qty_sum = 0.0
            for m in moves:
                try:
                    qty_in_prod_uom = m.product_uom._compute_quantity(m.product_uom_qty, p.uom_id)
                except Exception:
                    qty_in_prod_uom = m.product_uom_qty
                qty_sum += qty_in_prod_uom

            avg_month = qty_sum / max(1.0, float(months))

            # Skip slow products
            if avg_month < float(min_avg_threshold or 0.0):
                continue

            # ---------------------------------------------------------
            # LEAD TIME BASED ON CATEGORY TYPE (rm / cons / fg)
            # ---------------------------------------------------------
            effective_reorder_type = self._get_category_type_from_name(p.categ_id)

            purchase_lt = self._get_avg_purchase_lead_time(p, start_str, end_str)
            mrp_lt = self._get_avg_manufacturing_lead_time(p, start_str, end_str)

            # Normalize values → convert None/False to 0
            purchase_lt = purchase_lt or 0
            mrp_lt = mrp_lt or 0
            default_lt = p.product_tmpl_id.reorder_lead_time or 0

            # RM & Consumable → prefer purchase lead time
            if effective_reorder_type in ('rm', 'cons'):
                lead_time = math.ceil(
                    purchase_lt if purchase_lt > 0 else (
                        mrp_lt if mrp_lt > 0 else default_lt
                    )
                )
            else:
                # Finished Goods → prefer manufacturing lead time
                lead_time = math.ceil(
                    mrp_lt if mrp_lt > 0 else (
                        purchase_lt if purchase_lt > 0 else default_lt
                    )
                )
            # if lead_time <= 1:
            #     lead_time = 1

            # ---------------------------------------------------------
            # ROP & suggested qty formulas
            # ---------------------------------------------------------
            onhand = p.qty_available
            min_order = p.product_tmpl_id.reorder_min_qty or 0.0
            lot_size = p.product_tmpl_id.reorder_lot_size or 1.0

            safety_stock = math.ceil(avg_month * (safety_factor / 100.0))
            reorder_point = math.ceil((lead_time / 30.0) * avg_month + safety_stock)
            required_qty = max(0.0, reorder_point - onhand)

            suggested = 0.0
            if required_qty > 0:
                rounding = p.uom_id.rounding or 1.0
                if lot_size < rounding:
                    lot_size = rounding
                multiplier = math.ceil(required_qty / lot_size)
                suggested = multiplier * lot_size

                if min_order and suggested < min_order:
                    suggested = min_order

                suggested = math.ceil(suggested / rounding) * rounding

            # ---------------------------------------------------------
            # Store result record
            # ---------------------------------------------------------
            new_records.append({
                'product_id': p.id,
                'sum_last_n': qty_sum,
                'avg_month': math.ceil(avg_month),
                'on_hand_qty': onhand,
                'reorder_point': reorder_point,
                'required_qty': required_qty,
                'suggested_qty': suggested,
                'lead_time_days': lead_time,
                'computation_date': comp_dt_str,
                'company_id': p.company_id.id if p.company_id else (company_id or self.env.company.id),
            })

            product_ids_for_create.append(p.id)

        # -------------------------------------------------------------
        # Remove existing records (old results) then create new ones
        # -------------------------------------------------------------
        created_ids = []
        if new_records:
            company_filter = company_id or self.env.company.id

            # Delete ALL previous records for this company
            # (so only the latest computation is kept)
            existing_domain = [
                ('company_id', '=', company_filter),
            ]
            existing = self.sudo().search(existing_domain)
            if existing:
                existing.sudo().unlink()

            # Now create fresh results
            created = self.sudo().create(new_records)
            created_ids = created.ids

        return {'ids': created_ids, 'computation_date': comp_dt_str}


