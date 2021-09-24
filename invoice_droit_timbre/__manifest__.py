# -*- encoding: utf-8 -*-


{
    'name': 'Droit de timbre',
    'version': '11.0.1',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Tax',
    'description': """
    """,
    'author': 'Andema',
    'website': 'http://www.andemaconsulting.com',
    'depends': ['account',
                'invoice_payment_mode'],
    'data': [
        'views/account_invoice_view.xml',
        'views/res_config_view.xml',
        'report/report_invoice.xml',
    ],
    'installable': True,
}
