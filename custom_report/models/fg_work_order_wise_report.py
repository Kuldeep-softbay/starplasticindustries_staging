# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime

class FgWorkOrderWiseLine(models.Model):
    _name = 'fg.work.order.wise.line'
    _description = 'FG Work Order Wise Report Line'
    _order = 'wo_no, id'

    computation_key = fields.Char(index=True)
    party_id = fields.Many2one('job.party.work', string='Party')
    product_id = fields.Many2one('product.product', string='Item')
    wo_id = fields.Many2one('mrp.production', string='W.O. No')
    wo_no = fields.Char(string='W.O. No (name)', compute='_compute_wo_no', store=True)
    actual_stock = fields.Float(string='Actual Stock')
    stock_available_for_packing = fields.Float(string='Stock Available for Packing')
    unit_weight = fields.Float(string='Unit Weight')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    location_id = fields.Many2one('stock.location', string='Location')

    @api.depends('wo_id')
    def _compute_wo_no(self):
        for rec in self:
            rec.wo_no = rec.wo_id.name if rec.wo_id else ''


class FgWorkOrderWiseWizard(models.TransientModel):
    _name = 'fg.work.order.wise.wizard'
    _description = 'FG Work Order Wise Wizard'

    party_id = fields.Many2one('job.party.work', string='Party')
    product_id = fields.Many2one('product.product', string='Item')
    wo_id = fields.Many2one('mrp.production', string='W.O No')
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain="[('usage','=','internal')]")

    def _compute_product_stock(self, product):
        """Return (actual_stock, available_for_packing, unit_weight) for a product.
        Simple heuristic; change to your business rules if needed.
        """
        if not product:
            return 0.0, 0.0, 0.0
        actual = float(product.qty_available or 0.0)
        outgoing = float(getattr(product, 'outgoing_qty', 0.0) or 0.0)
        available_for_packing = actual - outgoing
        if available_for_packing < 0:
            available_for_packing = 0.0
        unit_weight = float(getattr(product, 'product_weight_sale', None) or getattr(product, 'weight', 0.0) or 0.0)
        return actual, available_for_packing, unit_weight

    def action_show_report(self):
        """Create report lines and open tree view filtered by computation_key."""
        self.ensure_one()
        ReportLine = self.env['fg.work.order.wise.line']
        computation_key = f"{self.env.uid}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        ProdModel = self.env['mrp.production']

        # Helper: choose an order field that exists on mrp.production
        order_field = 'id desc'
        if 'date_start' in ProdModel._fields:
            order_field = 'date_start desc'
        elif 'create_date' in ProdModel._fields:
            order_field = 'create_date desc'

        # 1) If a specific WO chosen, just use it
        if self.wo_id:
            productions = ProdModel.browse(self.wo_id.id)
        else:
            # 2) Build domain based on product / partner
            prod_domain = []
            if self.product_id:
                prod_domain.append(('product_id', '=', self.product_id.id))

            if self.party_id:
                # If mrp.production has a direct sale_order_id relation, use it (safe check)
                if 'sale_order_id' in ProdModel._fields:
                    # domain: sale_order.partner == partner OR origin contains partner name
                    partner_dom = ['|', ('sale_order_id.party_id', '=', self.party_id.id),
                                       ('origin', 'ilike', (self.party_id.name or ''))]
                    if prod_domain:
                        prod_domain = ['&', *prod_domain, *partner_dom]
                    else:
                        prod_domain = partner_dom
                else:
                    # Fallback: find sale orders of partner and match production.origin to sale names
                    Sale = self.env['sale.order']
                    sales = Sale.search([('party_id', '=', self.party_id.id)])
                    if sales:
                        origin_names = sales.mapped('name')
                        partner_dom = [('origin', 'in', origin_names)]
                        if prod_domain:
                            prod_domain = ['&', *prod_domain, *partner_dom]
                        else:
                            prod_domain = partner_dom
                    else:
                        # last fallback: origin contains partner name
                        partner_dom = [('origin', 'ilike', (self.party_id.name or ''))]
                        if prod_domain:
                            prod_domain = ['&', *prod_domain, *partner_dom]
                        else:
                            prod_domain = partner_dom

            # 3) Execute search (if no filters, limit to last 200 to avoid huge output — adjust if you want)
            if prod_domain:
                productions = ProdModel.search(prod_domain, order=order_field)
            else:
                productions = ProdModel.search([], limit=200, order=order_field)

        # 4) If nothing found but product provided, create a single product-level line
        if not productions and self.product_id and not self.wo_id:
            actual, avail, unit_weight = self._compute_product_stock(self.product_id)
            ReportLine.create({
                'computation_key': computation_key,
                'party_id': self.party_id.id or False,
                'product_id': self.product_id.id,
                'wo_id': False,
                'actual_stock': actual,
                'stock_available_for_packing': avail,
                'unit_weight': unit_weight,
                'location_id': self.location_id.id if self.location_id else False,
            })
        else:
            # 5) Create a line per production
            for prod in productions:
                product = prod.product_id
                actual, avail, unit_weight = self._compute_product_stock(product)
                # Determine party: prefer wizard party if provided, else try to fetch from production linked sale_order
                party_id = False
                if self.party_id:
                    party_id = self.party_id.id
                else:
                    # safe access to sale_order_id if present
                    if 'sale_order_id' in ProdModel._fields and getattr(prod, 'sale_order_id', False):
                        party = prod.sale_order_id.party_id
                        party_id = party.id if party else False
                    else:
                        party_id = False

                ReportLine.create({
                    'computation_key': computation_key,
                    'party_id': party_id,
                    'product_id': product.id or False,
                    'wo_id': prod.id,
                    'actual_stock': actual,
                    'stock_available_for_packing': avail,
                    'unit_weight': unit_weight,
                    'location_id': self.location_id.id if self.location_id else False,
                })

        # 6) Open the result list
        return {
            'type': 'ir.actions.act_window',
            'name': _('FG Work Order Wise Report'),
            'res_model': 'fg.work.order.wise.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }
