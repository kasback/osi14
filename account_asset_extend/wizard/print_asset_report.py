# -*- coding: utf-8 -*-
import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

from odoo.tools.translate import _
import math


class PrintAssetWizard(models.TransientModel):
    _name = 'print.asset.report'

    all_locations = fields.Boolean('Tout les emplacements')
    location_id = fields.Many2one('account.asset.location', string='Emplacement')

    def print_action(self):
        if self.all_locations:
            recs = self.env['account.asset.asset'].search([], order='affectataire')
            location = 'Tout les emplacements'
        else:
            recs = self.env['account.asset.asset'].search([('num_salle', '=', self.location_id.id)])
            location = self.location_id.name
        data = {
            'location': location,
            'doc_ids': recs.mapped('id')
        }
        return self.env.ref('account_asset_extend.report_asset_location').report_action([], data=data)


class ParticularReport(models.AbstractModel):
    _name = 'report.account_asset_extend.asset_location_report_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj = self.env['ir.actions.report']
        report = report_obj._get_report_from_name('account_asset_extend.asset_location_report_template')
        docargs = {
            'doc_ids': data['doc_ids'],
            'doc_model': report.model,
            'docs': self.env[report.model].browse(data['doc_ids']),
            'location': data['location']
        }
        return docargs
