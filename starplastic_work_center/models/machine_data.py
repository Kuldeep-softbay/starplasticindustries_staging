from odoo import models, fields


class MachineData(models.Model):
    _name = "machine.data"
    _description = "Machine Data Entry"
    _order = "date desc"

    name = fields.Char(string="Item RM & Color")

    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine")
    product_id = fields.Many2one("product.product", string="Item")

    date = fields.Date(string="Date", required=True)


    # Injection Data
    ing_sec = fields.Float(string="ING (Sec)")
    ing_pressure = fields.Float(string="ING P (kg/cm²)")

    rlp_sec = fields.Float(string="RLP (Sec)")
    rlp_pressure = fields.Float(string="RLP P (kg/cm²)")

    cooling_sec = fields.Float(string="Cooling (Sec)")
    rm_feed = fields.Float(string="RM Feed")
    locking_tonnage = fields.Float(string="Locking Tonnage")

    # Temperature Zones
    temp_zone_1 = fields.Float(string="Temp Zone 1")
    temp_zone_2 = fields.Float(string="Temp Zone 2")
    temp_zone_3 = fields.Float(string="Temp Zone 3")
    temp_zone_4 = fields.Float(string="Temp Zone 4")
    temp_zone_5 = fields.Float(string="Temp Zone 5")
    temp_zone_6 = fields.Float(string="Temp Zone 6")
    temp_zone_7 = fields.Float(string="Temp Zone 7")

    notes = fields.Text(string="Notes")
