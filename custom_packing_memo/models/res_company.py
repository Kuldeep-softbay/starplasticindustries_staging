from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    packing_header_image = fields.Binary(string="Packing Memo Header")
    packing_footer_image = fields.Binary(string="Packing Memo Footer")
    quotation_header_image = fields.Binary(string="Quotation Header")
    quotation_footer_image = fields.Binary(string="Quotation Footer")
    work_order_header_image = fields.Binary(string="Work Order Header")
    work_order_footer_image = fields.Binary(string="Work Order Footer")
