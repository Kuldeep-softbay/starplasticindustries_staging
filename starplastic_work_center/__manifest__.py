{
    'name': 'Starplastic Work Center - extra fields',
    'version': '1.0.0',
    'summary': 'Add computed fields used by customized Work Center views',
    'category': 'Manufacturing',
    'author': 'You',
    'website': '',
    'depends': ['mrp', 'product'],
    'data': [
        'views/mrp_workcenter_form_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
