# -*- encoding: utf-8 -*-

{
    'name': 'Gestion des immobilisations (norme Article)',
    'version': '1.0',
    'author': 'Andema',
    'website': 'http://www.andemaconsulting.com',
    "depends": [
        'account','account_asset_comm','stock', 'hr', 'account_asset_ma'
    ],
    'data': [
        "data/data.xml",
        "security/asset_security.xml",
        "security/ir.model.access.csv",
        "views/asset.xml",
        "views/asset_stock.xml",
        "views/stock_transfert_views.xml",
        "views/product_template.xml",
        "views/asset_stock_move_views.xml",
        "views/asset_picking_views.xml",
        "report/asset_report.xml",
        "report/asset_report_templates.xml",
        "report/product_label_templates.xml",
        "report/asset_label_report.xml",
        "wizard/print_asset_report.xml",
        "wizard/stock_barcodes_read_views.xml",
        "wizard/stock_barcodes_read_inventory_views.xml",
        "data/sequence.xml"
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
