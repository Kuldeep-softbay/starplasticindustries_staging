{
    "name": "Packing Memo",
    "version": "1.0.0",
    "summary": "Generate two packing memo copies from Sales Orders",
    "category": "Sales",
    "depends": ["stock", 'sale_management'],
    "data": [
        "views/sale_order_view.xml",
        "report/packing_memo_report.xml",
        "report/packing_memo_templates.xml",
    ],
    "license": "LGPL-3",
    "application": False,
}
