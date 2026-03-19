# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, time

# ==========================================================
# REPORT MODEL
# ==========================================================
class RmGradeWiseStockReport(models.Model):
    _name = 'rm.grade.wise.stock.report'
    _description = 'RM Grade Wise Stock Report'
    _order = 'date, id'

    computation_key = fields.Char(index=True)

    date = fields.Date()
    particulars = fields.Char()

    product_id = fields.Many2one('product.product', string='Product')
    rm_type = fields.Many2one('product.template', string='RM Type')

    batch = fields.Char(string='Internal Batch No')

    rm_grade_name = fields.Char(string='RM Grade')

    vendor_id = fields.Many2one('res.partner', string='Vendor')
    invoice_no = fields.Char()

    received_qty = fields.Float()
    issue_qty = fields.Float()
    balance_qty = fields.Float()
    pmemo_no = fields.Char()


# ==========================================================
# WIZARD
# ==========================================================
class RmGradeWiseStockWizard(models.TransientModel):
    _name = 'rm.grade.wise.stock.wizard'
    _description = 'RM Grade Wise Stock Wizard'

    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)

    party_id = fields.Many2one('job.party.work', string='Party')

    rm_type = fields.Many2one(
        'product.template',
        string='RM Type',
        domain="[('purchase_ok','=',True),('sale_ok','=',False)]"
    )

    rm_grade = fields.Many2one(
        'product.template.attribute.value',
        string='RM Grade',
        domain="[('id','in',available_grade_ids)]",
        context={'rm_grade_only': True}
    )

    available_grade_ids = fields.Many2many(
        'product.template.attribute.value',
        compute='_compute_available_grades',
        store=False
    )

    @api.depends('rm_type')
    def _compute_available_grades(self):
        for wizard in self:
            if not wizard.rm_type:
                wizard.available_grade_ids = [(6, 0, [])]
                continue
            values = wizard.rm_type.product_variant_ids.mapped(
                'product_template_variant_value_ids'
            )
            wizard.available_grade_ids = [(6, 0, values.ids)]


    # ------------------------------------------------------
    # DATETIME HELPERS
    # ------------------------------------------------------
    def _datetime_from(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_from, time.min)
        )

    def _datetime_to(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_to, time.max)
        )

    def _get_grade_name(self, product):
        if not product:
            return ''

        tmpl = product.product_tmpl_id

        grade_lines = tmpl.attribute_line_ids.filtered(
            lambda l: 'grade' in l.attribute_id.name.lower()
        )

        return ", ".join(grade_lines.mapped('value_ids.name'))

    # ------------------------------------------------------
    # DOMAIN
    # ------------------------------------------------------
    def _base_domain(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', self._datetime_from()),
            ('date', '<=', self._datetime_to()),
            ('product_id.product_tmpl_id.purchase_ok', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', False),
            '|',
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
        ]

        if self.party_id:
            domain.append(('party_id', '=', self.party_id.id))

        if self.rm_type:
            domain.append(('product_id.product_tmpl_id', '=', self.rm_type.id))

        if self.rm_grade:
            domain.append((
                'product_id.product_template_variant_value_ids',
                'in',
                self.rm_grade.id
            ))

        return domain

    # ------------------------------------------------------
    # OPENING BALANCE
    # ------------------------------------------------------
    def _compute_opening_balance(self):
        opening = 0.0
        Move = self.env['stock.move']

        moves = Move.search([
            ('state', '=', 'done'),
            ('date', '<', self._datetime_from()),
            ('product_id.product_tmpl_id.purchase_ok', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', False),
            '|',
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
        ])

        for mv in moves:
            qty = mv.product_uom_qty
            if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                opening += qty
            elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                opening -= qty

        return opening

    # ------------------------------------------------------
    # MAIN ACTION
    # ------------------------------------------------------
    def action_show_report(self):
        self.ensure_one()

        Report = self.env['rm.grade.wise.stock.report']
        Move = self.env['stock.move']

        # Clear old data
        Report.search([
            ('computation_key', 'like', f"{self.env.uid}-")
        ]).unlink()

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"
        balance = self._compute_opening_balance()

        moves = Move.search(self._base_domain(), order='date,id')

        kg_uom = self.env.ref('uom.product_uom_kgm')

        for mv in moves:

            # ❌ Skip finished product (MO output)
            if mv.production_id and not mv.raw_material_production_id:
                continue

            # ❌ Skip only WH/MO picking
            if mv.picking_id and mv.picking_id.name and mv.picking_id.name.startswith('WH/MO/'):
                continue

            received = 0.0
            issued = 0.0

            # -------- QTY IN KG --------
            qty = 0.0
            if mv.move_line_ids:
                for line in mv.move_line_ids:
                    qty += line.product_uom_id._compute_quantity(
                        line.qty_done, kg_uom
                    )
            else:
                qty = mv.product_uom._compute_quantity(
                    mv.product_uom_qty, kg_uom
                )

            src = mv.location_id
            dest = mv.location_dest_id

            # PURCHASE
            if src.usage == 'supplier' and dest.usage == 'internal':
                received = qty

            # RM ISSUE (WH/PC)
            elif mv.picking_id and mv.picking_id.origin and 'WH/MO/' in mv.picking_id.origin:
                if src.usage == 'internal' and dest.usage == 'internal':
                    issued = qty

            # DELIVERY
            elif src.usage == 'internal' and dest.usage == 'customer':
                issued = qty

            # BALANCE
            balance += (received - issued)

            # ❌ Skip zero movement
            if not received and not issued:
                continue

            # -------- GET MO --------
            mo = False
            if mv.picking_id and mv.picking_id.origin:
                mo = self.env['mrp.production'].search([
                    ('name', '=', mv.picking_id.origin)
                ], limit=1)

            # ==================================================
            # ✅ FINAL PRODUCT LOGIC (ADDED)
            # ==================================================
            if received:
                # ❌ Hide product for purchase
                product_id_value = False

            elif issued:
                # ✅ Show finished product for issue
                if mo:
                    product_id_value = mo.product_id.id
                else:
                    product_id_value = mv.product_id.id
            else:
                product_id_value = False
            # ==================================================

            # -------- PARTICULARS --------
            if mv.picking_id:
                particulars = mv.picking_id.name
            else:
                particulars = mv.reference or ''

            lot_name = mv.move_line_ids[:1].lot_id.name if mv.move_line_ids else False

            Report.create({
                'computation_key': computation_key,
                'date': mv.date.date(),
                'particulars': particulars,
                'product_id': product_id_value,
                'batch': lot_name or '',
                'rm_grade_name': self._get_grade_name(mv.product_id),
                'vendor_id': mv.picking_id.partner_id.id if mv.picking_id else False,
                'invoice_no': mv.picking_id.invoice_number if mv.picking_id else '',
                'received_qty': received,
                'issue_qty': issued,
                'balance_qty': balance,
                'pmemo_no': mv.picking_id.name if mv.picking_id else '',
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Grade Wise Stock Report'),
            'res_model': 'rm.grade.wise.stock.report',
            'view_mode': 'list',
            'domain': [('computation_key', '=', computation_key)],
            'target': 'current',
        }
