from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    work_order_header_image = fields.Binary(string="Work Order Header")
    work_order_footer_image = fields.Binary(string="Work Order Footer")
    production_memo_header_image = fields.Binary(string="Production Memo Header")
    production_memo_footer_image = fields.Binary(string="Production Memo Footer")
    machine_status_memo_header_image = fields.Binary(string="Machine Status Memo Header")
    machine_status_memo_footer_image = fields.Binary(string="Machine Status Memo Footer")
    delayed_production_report_header_image = fields.Binary(string="Delayed Production Report Header")
    delayed_production_report_footer_image = fields.Binary(string="Delayed Production Report Footer")
    rm_stock_book_report_header_image = fields.Binary(string="RM Stock Book Report Header")
    rm_stock_book_report_footer_image = fields.Binary(string="RM Stock Book Report Footer")
    rm_grade_report_header_image = fields.Binary(string="RM Grade Report Header")
    rm_grade_report_footer_image = fields.Binary(string="RM Grade Report Footer")
    rm_stock_sheet_report_header_image = fields.Binary(string="FG Stock Sheet Report Header")
    rm_stock_sheet_report_footer_image = fields.Binary(string="FG Stock Sheet Report Footer")
