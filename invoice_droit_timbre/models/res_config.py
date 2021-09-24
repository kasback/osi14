# -*- coding: utf-8 -*-


from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _default_taux_droit_timbre(self):
        taux_droit_timbre = self.env['ir.config_parameter'].get_default('res.config.settings', 'taux_droit_timbre')
        return self.env['res.config.settings'].browse(taux_droit_timbre)

    taux_droit_timbre = fields.Float(string=u'Taux droit timbre')

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            taux_droit_timbre=float(self.env['ir.config_parameter'].sudo().get_param('invoice_droit_timbre.taux_droit_timbre')),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.taux_droit_timbre:
            self.env['ir.config_parameter'].sudo().set_param('invoice_droit_timbre.taux_droit_timbre',
                                                             self.taux_droit_timbre)