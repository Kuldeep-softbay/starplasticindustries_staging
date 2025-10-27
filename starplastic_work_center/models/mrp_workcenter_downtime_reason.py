from odoo import fields, models

class WcDowntimeReason(models.Model):
    _name = 'wc.downtime.reason'
    _description = 'Downtime Reason'

    name = fields.Char(required=True, string='Reason')


class WcDowntimeSubreason(models.Model):
    _name = 'wc.downtime.subreason'
    _description = 'Downtime Sub Reason'

    name = fields.Char(required=True, string='Sub Reason')
    reason_id = fields.Many2one('wc.downtime.reason', string='Reason', required=True)