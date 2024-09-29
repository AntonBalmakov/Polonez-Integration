# -*- coding: utf-8 -*-
{
    'name': "Сustom integ",

    'summary': """
        Module for receiving data and updating product information""",

    'description': """
        Module for receiving data and updating product information.
    """,

    'author': "Balmakov",
    'website': "https://github.com/AntonBalmakov/Polonez-Integration",
    'application': True,
    'category': 'Extra Tools',
    'version': '0.1',

    'depends': ['product', 'base', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/pz_product.xml',
        'data/cron_job.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
