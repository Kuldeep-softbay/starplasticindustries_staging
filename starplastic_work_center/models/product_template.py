from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_insert = fields.Char("Product Insert")
    product_code = fields.Char("Product Code")
    raw_material = fields.Char("Raw Material")
    mould_name = fields.Char("Mould Name")
    difference = fields.Float("Difference")
    is_product = fields.Boolean(string="Is Product?")
    batch_number = fields.Char("Batch Number")

    product_counting_type = fields.Selection([
        ('kg', 'Kg'),
        ('unit', 'Unit'),
    ], string="Product Counting Type")

    unit_weight_tolerance = fields.Float("Unit Weight Tolerance (+/-)")
    process = fields.Selection([
        ('blow', 'Blow molding'),
        ('injection', 'Injection molding'),
        ('blow_injection', 'Blow Injection molding'),
        ('other', 'Other'),
    ], string="Process")

    rm_formulation = fields.Text("RM Formulation")
    packing_method = fields.Char("Packing Method")
