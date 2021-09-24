# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    droit_timbre = fields.Float('Droit de timbre', compute='compute_droit_timbre')
    total_a_payer = fields.Float('Total à payer', compute='compute_droit_timbre')
    rate = fields.Float('Taux droit timbre', compute='compute_droit_timbre')

    def is_cash(self):
        for rec in self:
            for mode in rec.mode_reglement_ids:
                if mode.name == 'cash':
                    return True
        return False

    @api.depends('amount_total', 'mode_reglement_ids.name')
    def compute_droit_timbre(self):
        rate = self.env['ir.config_parameter'].sudo().get_param('invoice_droit_timbre.taux_droit_timbre')
        for rec in self:
            rec.droit_timbre = 0
            rec.total_a_payer = 0
            rec.rate = 0
            if rate and rec.amount_total and rec.is_cash():
                rec.droit_timbre = float(rate) * rec.amount_total / 100
                rec.total_a_payer = rec.amount_total + rec.droit_timbre
                rec.rate = rate
            else:
                 rec.total_a_payer = rec.amount_total
