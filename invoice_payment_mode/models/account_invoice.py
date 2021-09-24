# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.move"

    comment = fields.Text(readonly=False)
    mode_reglement_ids = fields.One2many('account.invoice.mode.reglement', 'invoice_id')


class AccountInvoiceModeReglement(models.Model):
    _name = "account.invoice.mode.reglement"

    name = fields.Selection([('ov', u'Virement'),
                             ('cash', u'Espèce'),
                             ('bank', u'Chèque'),
                             ('cb', u'Carte bancaire'),
                             ], string='Mode de paiement')
    ref_regl = fields.Char(u'Réf Règlement')
    invoice_id = fields.Many2one('account.move', string='Facture')
