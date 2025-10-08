{
    'name': 'Starplastic MRP Enhancements',
    'version': '1.0.0',
    'category': 'Manufacturing',
    'author': 'Kuldeep Singh',
    'website': '',
    'depends': ['mrp', 'sale_management', 'purchase'],
    'data': [
        'views/mrp_workcenter_form_views.xml',
        'views/product_template_views.xml',
        'views/mrp_routing_views.xml',
        'views/mrp_workorder_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
