{
    'name': 'Reorder Planning (Pilot)',
    'version': '1.0.0',
    'category': 'Inventory',
    'summary': 'Pilot reorder point calculation and planning',
    'description': 'Compute reorder point.',
    'depends': ['stock', 'sale_management', 'mrp', 'purchase'],
    'data': [
        'data/cron_reorder_planning.xml',
        'security/ir.model.access.csv',
        'wizard/reorder_wizard_views.xml',
        'views/reorder_analysis_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
