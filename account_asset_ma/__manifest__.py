# -*- encoding: utf-8 -*-

{
    'name': 'Gestion des immobilisations (norme Marocaine)',
    'version': '1.0',
    'author': 'Andema',
    'website': 'http://www.andemaconsulting.com',
    "depends": [
        'account','account_asset_comm', 'account_fiscal_year', 'account_fiscal_period'
    ],
    'data': [
        'wizard/asset_control_view.xml',
        'security/asset_security.xml',
        'security/ir.model.access.csv',
        "views/asset.xml"
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
