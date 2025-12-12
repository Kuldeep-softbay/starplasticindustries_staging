from odoo import api, fields, models, _
from datetime import datetime, time
import logging

_logger = logging.getLogger(__name__)


class RmStockSheetReport(models.Model):
    _name = 'rm.stock.sheet.report'
    _description = 'RM Stock Sheet Report'
    _order = 'party_id, location_id, product_id, grade, id'

    computation_key = fields.Char(index=True)

    date = fields.Date(string='Date')
    party_id = fields.Many2one('job.party.work', string='Party')
    location_id = fields.Many2one('stock.location', string='Location')

    product_id = fields.Many2one('product.product', string='Product')
    grade = fields.Char(string='RM Grade')
    mfi = fields.Char(string='MFI')
    batch = fields.Char(string='Batch')

    bag_qty = fields.Float(string='Bag')
    kgs = fields.Float(string='Kgs')
    total_kgs = fields.Float(string='Total Kg')


class RmStockSheetWizard(models.TransientModel):
    _name = 'rm.stock.sheet.wizard'
    _description = 'RM Stock Sheet Wizard'

    date = fields.Date(
        string='As On Date',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    party_id = fields.Many2one('job.party.work', string='Party')
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]",
    )
    product_id = fields.Many2one('product.product', string='Product')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _datetime_to(self):
        """As-of datetime (end of selected date)."""
        return fields.Datetime.to_datetime(
            datetime.combine(self.date, time.max)
        )

    def _base_domain(self):
        """Stock moves up to selected date."""
        self.ensure_one()
        dt_to = self._datetime_to()
        domain = [
            ('state', '=', 'done'),
            ('date', '<=', dt_to),
            # only storable products (RM)
            ('product_id.type', '=', 'product'),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.party_id:
            domain.append(('partner_id', '=', self.party_id.id))
        # we do *not* put location filter here; logic below will interpret moves
        return domain

    # ------------------------------------------------------------------
    # Main action
    # ------------------------------------------------------------------

    def action_show_report(self):
        self.ensure_one()
        report_env = self.env['rm.stock.sheet.report']
        Move = self.env['stock.move']

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"

        domain = self._base_domain()
        moves = Move.search(domain, order='date, id')

        _logger.info(
            "RM Stock Sheet: domain=%s, moves=%s",
            domain, len(moves)
        )

        # Aggregate quantities by (party, location, product, grade, batch, mfi)
        aggregated = {}

        for mv in moves:
            qty = mv.product_uom_qty

            # Decide IN / OUT relative to chosen location (or whole warehouse)
            delta = 0.0
            if self.location_id:
                loc = self.location_id
                if mv.location_dest_id == loc and mv.location_id != loc:
                    delta = qty    # IN to this location
                elif mv.location_id == loc and mv.location_dest_id != loc:
                    delta = -qty   # OUT from this location
                else:
                    # internal->internal but not involving our location -> ignore
                    continue
                location = loc
            else:
                # No location filter: global internal stock
                if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                    delta = qty
                    location = mv.location_dest_id
                elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                    delta = -qty
                    location = mv.location_id
                else:
                    # internal->internal or external->external: no overall change
                    continue

            if not delta:
                continue

            # Party = vendor/supplier for incoming moves, or partner on picking
            party = mv.partner_id or (mv.picking_id.partner_id if mv.picking_id else False)

            # Try to read grade / mfi / batch from product or move
            product = mv.product_id
            grade = getattr(product, 'grade', False) or ''
            mfi = getattr(product, 'mfi', False) or ''
            batch = getattr(mv, 'internal_batch_number', False) or ''

            key = (
                party.id if party else False,
                location.id if location else False,
                product.id,
                grade,
                batch,
                mfi,
            )

            if key not in aggregated:
                aggregated[key] = {
                    'qty': 0.0,
                    'party': party,
                    'location': location,
                    'product': product,
                    'grade': grade,
                    'mfi': mfi,
                    'batch': batch,
                }

            aggregated[key]['qty'] += delta

        # Create report lines (only for non-zero qty)
        for (party_id, location_id, product_id, grade, batch, mfi), data in aggregated.items():
            qty = data['qty']
            if abs(qty) < 1e-6:
                continue

            # For now: Bag and Kgs are both same as qty.
            # You can later split qty into bags * weight per bag.
            bag_qty = 0.0
            kgs = qty
            total_kgs = qty

            report_env.create({
                'computation_key': computation_key,
                'date': self.date,
                'party_id': party_id,
                'location_id': location_id,
                'product_id': product_id,
                'grade': grade,
                'mfi': mfi,
                'batch': batch,
                'bag_qty': bag_qty,
                'kgs': kgs,
                'total_kgs': total_kgs,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Stock Sheet Report'),
            'res_model': 'rm.stock.sheet.report',
            'view_mode': 'list',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }
