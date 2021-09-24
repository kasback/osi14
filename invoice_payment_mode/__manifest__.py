# -*- coding: utf-8 -*-


{
    "name": "Invoice payment mode",
    "version": "14.0",
    'category': 'Accounting',
    "depends": [
        "account",
        ],
    "author": "ANDEMA",
    "summary": "customisation de la facture:-Mode de paiement",
    'website': 'http://www.andemaconsulting.com',
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_view.xml',
        'report/report_invoice.xml'
        ],
    'installable': True,
    'active': False,
}
