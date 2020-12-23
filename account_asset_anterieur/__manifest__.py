# -*- encoding: utf-8 -*-

{
    'name': 'Cumul antérieur des immobilisations',
    'version': '1.0',
    'author': 'Andema',
    'website': 'http://www.andemaconsulting.com',
    "depends": [
        'account','account_asset_comm',
    ],
    'data': [
        'security/security.xml',
        'wizard/account_asset_anterieur_views.xml',


        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
