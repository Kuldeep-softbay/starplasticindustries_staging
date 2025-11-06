{
    "name": "Packing Memo",
    "version": "1.0.0",
    "summary": "Generate two packing memo copies from Sales Orders",
    "category": "Sales",
    "depends": ["stock", 'sale_management'],
    "data": [
        "views/res_company_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
        "report/packing_memo_report.xml",
        "report/packing_memo_templates.xml",
        # "report/sale_order_report.xml",
    ],
    "license": "LGPL-3",
    "application": False,
}