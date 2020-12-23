# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tva_rapport_id = fields.Binary(string="Rapport Excel TVA")

    tax_journal_id = fields.Many2one('account.journal', related='company_id.tax_journal_id', readonly=False,
                                     string="Journal de TVA")

    tax_account_id = fields.Many2one('account.account', related='company_id.tax_account_id', readonly=False,
        string=u"Crédit de TVA")

    payed_tax_account_id = fields.Many2one('account.account', related='company_id.payed_tax_account_id', readonly=False,
                                     string="Etat TVA due")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            tva_rapport_id=self.env['ir.config_parameter'].sudo().get_param('tva_encaissement_maroc.tva_rapport_id'),
            # tax_journal_id=int(self.env['ir.config_parameter'].sudo().get_param('tva_encaissement_maroc.tax_journal_id')),
            # tax_account_id=int(self.env['ir.config_parameter'].sudo().get_param('tva_encaissement_maroc.tax_account_id')),
            # payed_tax_account_id=int(self.env['ir.config_parameter'].sudo().get_param('tva_encaissement_maroc.payed_tax_account_id')),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.tva_rapport_id:
            self.env['ir.config_parameter'].sudo().set_param('tva_encaissement_maroc.tva_rapport_id', self.tva_rapport_id)
        # if self.tax_journal_id:
        #     self.env['ir.config_parameter'].sudo().set_param('tva_encaissement_maroc.tax_journal_id', self.tax_journal_id.id)
        # if self.tax_account_id:
        #     self.env['ir.config_parameter'].sudo().set_param('tva_encaissement_maroc.tax_account_id', self.tax_account_id.id)
        # if self.payed_tax_account_id:
        #     self.env['ir.config_parameter'].sudo().set_param('tva_encaissement_maroc.payed_tax_account_id', self.payed_tax_account_id.id)


class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_journal_id = fields.Many2one('account.journal',
                                     string="Journal de TVA")
    tax_account_id = fields.Many2one('account.account',
                                     string=u"Crédit de TVA")

    payed_tax_account_id = fields.Many2one('account.account',
                                           string="Etat TVA due")


