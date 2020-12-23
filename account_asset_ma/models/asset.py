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


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    asset_id = fields.Many2one('account.asset.asset', 'Immobilisation')

    def invoice_validate(self):
        for invoice in self:
            # refuse to validate a vendor bill/refund if there already exists one with the same reference for the same partner,
            # because it's probably a double encoding of the same bill/refund
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference),
                                ('company_id', '=', invoice.company_id.id),
                                ('commercial_partner_id', '=', invoice.commercial_partner_id.id),
                                ('id', '!=', invoice.id)]):
                    raise UserError(_(
                        "Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
            if invoice.asset_id:
                invoice.move_id.write({'asset_id': invoice.asset_id.id})
                invoice.asset_id.write({'sold_amount': invoice.amount_untaxed})
        return self.write({'state': 'open'})


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('asset_category_id')
    def onchange_asset(self):
        if self.asset_category_id:
            self.property_account_expense_id = self.asset_category_id.account_asset_id
            self.property_account_income_id = self.asset_category_id.account_revenue_id


class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'

    account_vna_id = fields.Many2one('account.account', string="Compte VNA", required=True,
                                     domain=[('internal_type','=','other'), ('deprecated', '=', False)])
    account_revenue_id = fields.Many2one('account.account', string="Compte de produit de cession", required=True,
                                         domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])


class AccountAsset(models.Model):
    _inherit = "account.asset.asset"

    invoice_date = fields.Date(string=u"Date de facturation", required=False)
    is_cost_asset = fields.Boolean(u'Charge à répartir sur plusieurs exercice')
    is_depreciated = fields.Boolean(u'Le bien est amorti', default=True)
    parent_id = fields.Many2one('account.asset.asset', string=u'Immo Parent')
    child_ids = fields.One2many(inverse_name='parent_id', string=u'Immo Childs', comodel_name='account.asset.asset')
    acquisition_mode = fields.Selection([('a', 'Acquisition'),
                                         ('p', 'Production'),
                                         ('v', 'Virement')],
                                         u"Mode d'acquisition",
                                        required=True, default='a')
    serial_number = fields.Char(u'Code / Numéro de série')
    #Champs cession
    mode_session = fields.Selection([('c', 'Cession'),
                                     ('r', 'Retrait'),
                                     ('v', 'Virement')],
                                    u"Mode de cession", required=True, default='c')
    date_cession = fields.Date('Date de cession')
    vna_move_id = fields.Many2one('account.move', u'Pièce comptable VNA', readonly=True)
    amount_vna = fields.Float(u'Valeur VNA', readonly=True)
    sold_amount = fields.Float(u'Montant de cession', readonly=True)
    reeval_value = fields.Float(u'Valeur comptable après réévaluation')
    observations = fields.Text(u'Observations')

    asset_succursale_id = fields.Many2one(comodel_name="asset.succursale", string=u"Succursale", required=False, )
    asset_emplacement_id = fields.Many2one(comodel_name="asset.emplacement", string=u"Emplacement", required=False, )
    cumul_amortissements = fields.Float(u'Cumul des amortissements', compute='_compute_cumul_amortissements')

    @api.depends('depreciation_line_ids.amount', 'depreciation_line_ids.move_check')
    def _compute_cumul_amortissements(self):
        total_amount = 0.0
        for line in self.depreciation_line_ids:
            if line.move_check and line.depreciation_date < fields.Date.context_today(self):
                total_amount += line.amount
        self.cumul_amortissements = total_amount

    def _compute_entries(self, date, group_entries=False):
        current_date_range = self.env.user.company_id.find_daterange_fy(fields.Date.from_string(date))
        depreciation_ids = self.env['account.asset.depreciation.line'].search([
            ('asset_id', 'in', self.ids), ('depreciation_date', '<=', date),
            ('depreciation_date', '>=', current_date_range.date_start),
            ('move_check', '=', False), ('asset_id.is_depreciated', '=', True)])
        if group_entries:
            return depreciation_ids.create_grouped_move()
        return depreciation_ids.create_move()

    def generate_vna_move(self):
        company_currency = self.company_id.currency_id
        current_currency = self.currency_id
        sign = (self.category_id.journal_id.type == 'purchase' or self.category_id.journal_id.type == 'sale' and 1) or -1
        categ_type = self.category_id.type
        amonut_dep =  0
        for line in self.depreciation_line_ids:
            amonut_dep+=line.amount
        amount_vna = self.value - amonut_dep
        move_line_1 = {
            'name': self.name,
            'account_id': self.category_id.account_vna_id.id,
            'debit': amount_vna,
            'credit': 0,
            'journal_id': self.category_id.journal_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
            'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'sale' else False,
            'date': self.date_cession,
        }
        move_line_2 = {
            'name': self.name,
            'account_id': self.category_id.account_depreciation_id.id,
            'debit': amonut_dep,
            'credit': 0,
            'journal_id': self.category_id.journal_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
            'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'sale' else False,
            'date': self.date_cession,
        }
        move_line_3 = {
            'name': self.name,
            'account_id': self.category_id.account_asset_id.id,
            'debit': 0,
            'credit': self.value,
            'journal_id': self.category_id.journal_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
            'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'sale' else False,
            'date': self.date_cession,
        }
        move_vals = {
            'ref': self.code,
            'date': self.date_cession or False,
            'journal_id': self.category_id.journal_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2), (0, 0, move_line_3)],
        }
        move = self.env['account.move'].create(move_vals)
        return [move, amount_vna]

    def _compute_board_amount(self, sequence, residual_amount, amount_to_depr, undone_dotation_number,
                              posted_depreciation_line_ids, total_days, depreciation_date):
        amount = 0
        if sequence == undone_dotation_number:
            amount = residual_amount
        else:
            if self.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if self.prorata:
                    amount = amount_to_depr / self.method_number
                    if sequence == 1:
                        date = self.date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                            amount = (amount_to_depr / self.method_number) / month_days * days

                        else:
                            # days = (self.company_id.compute_fiscalyear_dates(date)['date_to'] - date).days + 1
                            # amount = (amount_to_depr / self.method_number) / total_days * days
                            months = 13 - date.month
                            amount = (amount_to_depr / self.method_number) / 12 * months
            elif self.method == 'degressive':
                amount = residual_amount * self.method_progress_factor

                if self.prorata:
                    if sequence == 1:
                        date = self.date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                            amount = (residual_amount * self.method_progress_factor) / month_days * days

                        else:
                            months = 13 - date.month
                            amount = (residual_amount * self.method_progress_factor) / 12 * months
                            # days = (self.company_id.compute_fiscalyear_dates(date)['date_to'] - date).days + 1
                            # amount = (residual_amount * self.method_progress_factor) / total_days * days
        return amount
    # @api.multi
    # def compute_depreciation_board(self):
    #     self.ensure_one()
    #
    #     posted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: x.move_check).sorted(
    #         key=lambda l: l.depreciation_date, reverse=True)
    #     unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: not x.move_check)
    #
    #     # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
    #     commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]
    #
    #     if self.value_residual != 0.0 and not self.vna_move_id:
    #         amount_to_depr = residual_amount = self.value_residual
    #         date_dep = self._get_last_depreciation_date()[self.id]
    #         if self.prorata:
    #             depreciation_date = self._get_last_depreciation_date()[self.id].replace(month=12, day=31)
    #         else:
    #             # depreciation_date = 1st of January of purchase year
    #             if self.method_period >= 12:
    #                 asset_date = self.date.replace(month=12, day=31)
    #             else:
    #                 asset_date = self.date.replace(day=1)
    #                 # date_asset = fields.Date.from_string(self.date)
    #                 # asset_date = datetime(date_asset.year, date_asset.month, 1) + relativedelta(months=1)
    #             # if we already have some previous validated entries, starting date isn't 1st January but last entry + method period
    #             if posted_depreciation_line_ids and posted_depreciation_line_ids[0].depreciation_date:
    #                 last_depreciation_date = posted_depreciation_line_ids[0].depreciation_date
    #                 depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
    #
    #             else:
    #                 depreciation_date = asset_date
    #         day = depreciation_date.day
    #         month = depreciation_date.month
    #         year = depreciation_date.year
    #         total_days = (year % 4) and 365 or 366
    #
    #         undone_dotation_number = self._compute_board_undone_dotation_nb(depreciation_date, total_days)
    #
    #         for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
    #             sequence = x + 1
    #             amount = self._compute_board_amount(sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, date_dep)
    #             amount = self.currency_id.round(amount)
    #             if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
    #                 continue
    #             residual_amount -= amount
    #             vals = {
    #                 'amount': amount,
    #                 'asset_id': self.id,
    #                 'sequence': sequence,
    #                 'name': (self.code or '') + '/' + str(sequence),
    #                 'remaining_value': residual_amount,
    #                 'depreciated_value': self.value - (self.salvage_value + residual_amount),
    #                 'depreciation_date': depreciation_date.strftime(DF),
    #             }
    #             commands.append((0, False, vals))
    #             # Considering Depr. Period as months
    #             depreciation_date = date(year, month, day) + relativedelta(months=+self.method_period)
    #             day = depreciation_date.day
    #             month = depreciation_date.month
    #             year = depreciation_date.year
    #
    #     self.write({'depreciation_line_ids': commands})
    #
    #     return True

    def set_to_close(self):
        move_ids = []
        for asset in self:
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: not x.move_check)
            if unposted_depreciation_line_ids:
                old_values = {
                    'method_end': asset.method_end,
                    'method_number': asset.method_number,
                }

                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

                # Create a new depr. line with the residual amount and post it
                sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_line_ids) + 1
                date_cession = self.date_cession
                if not date_cession:
                    raise ValidationError(
                        (u'Merci de préciser la date et la méthode de cession.'))
                depreciation_date = date_cession.replace(month=12, day=31)
                last_date = date(self.date.year, self.date.month, self.date.day) + relativedelta(years=int(self.method_number))
                diff = (last_date - date_cession)
                diff_dep_date = depreciation_date - date_cession
                amount = 0
                if diff > diff_dep_date:
                    months = date_cession.month-1
                    amount = (self.value / self.method_number) / 12 * months
                else:
                    months = math.floor(diff/60)
                    amount = (self.value / self.method_number) / 12 * months
                vals = {
                    'amount': amount,
                    'asset_id': asset.id,
                    'sequence': sequence,
                    'name': (asset.code or '') + '/' + str(sequence) + u'(Dotation complémentaire)',
                    'remaining_value': 0,
                    'depreciated_value': asset.value - asset.salvage_value,  # the asset is completely depreciated
                    'depreciation_date': depreciation_date,
                }
                commands.append((0, False, vals))
                asset.write({'depreciation_line_ids': commands, 'method_end': asset.method_end, 'method_number': sequence})
                tracked_fields = self.env['account.asset.asset'].fields_get(['method_number', 'method_end'])
                changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
                if changes:
                    asset.message_post(subject=_('Asset sold or disposed. Accounting entry awaiting for validation.'),
                                       tracking_value_ids=tracking_value_ids)
                move_ids += asset.depreciation_line_ids[-1].create_move(post_move=False)
                move_id = self.generate_vna_move()
                self.write({'vna_move_id': move_id[0].id,'state': 'close','amount_vna':move_id[1],'value_residual':0})

class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    def create_move(self, post_move=True):
            created_moves = self.env['account.move']
            for line in self:
                if line.move_id:
                    raise UserError(
                        ('This depreciation is already linked to a journal entry! Please post or delete it.'))

                depreciation_date = self.env.context.get('depreciation_date') or line.depreciation_date or fields.Date.context_today(self)
                company_currency = line.asset_id.company_id.currency_id
                current_currency = line.asset_id.currency_id
                amount = current_currency._convert(line.amount, company_currency, line.asset_id.company_id, line.depreciation_date)
                sign = (line.asset_id.category_id.journal_id.type == 'purchase' or line.asset_id.category_id.journal_id.type == 'sale' and 1) or -1
                asset_name = line.asset_id.name + ' (%s/%s)' % (line.sequence, line.asset_id.method_number)
                reference = line.asset_id.code
                journal_id = line.asset_id.category_id.journal_id.id
                partner_id = line.asset_id.partner_id.id
                categ_type = line.asset_id.category_id.type
                credit_account = line.asset_id.category_id.account_depreciation_id.id
                debit_account = line.asset_id.category_id.account_depreciation_expense_id.id
                move_line_1 = {
                    'name': asset_name,
                    'account_id': credit_account,
                    'debit': 0.0,
                    'credit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency.id or False,
                    'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                    'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'sale' else False,
                    'date': depreciation_date,
                }
                move_line_2 = {
                    'name': asset_name,
                    'account_id': debit_account,
                    'credit': 0.0,
                    'debit': amount,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'currency_id': company_currency != current_currency and current_currency.id or False,
                    'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                    'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'purchase' else False,
                    'date': depreciation_date,
                }
                move_vals = {
                    'ref': reference,
                    'date': depreciation_date or False,
                    'journal_id': line.asset_id.category_id.journal_id.id,
                    'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    'asset_id': line.asset_id.id,
                    }
                move = self.env['account.move'].create(move_vals)
                line.write({'move_id': move.id, 'move_check': True})
                created_moves |= move

            if post_move and created_moves:
                created_moves.filtered(lambda m: any(m.asset_depreciation_ids.mapped('asset_id.category_id.open_asset'))).post()
            return [x.id for x in created_moves]


class AssetSuccursale(models.Model):
    _name = 'asset.succursale'

    name = fields.Char(string=u"Succursale",required=True)
    itp = fields.Char(string=u'Identifiant Taxe Professionnelle')


class AccountMove(models.Model):
    _inherit = 'account.move'

    asset_id = fields.Many2one('account.asset.asset', string='Asset', ondelete="restrict")


class AssetEmplacement(models.Model):
    _name = 'asset.emplacement'

    name = fields.Char(string=u"Emplacement d'affectation",required=True)
    succursale_id = fields.Many2one(comodel_name="asset.succursale", string=u"Succursale", required=True)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    def asset_create(self):
        res = super(AccountInvoiceLine, self).asset_create()
        asset = self.env['account.asset.asset'].search([('invoice_id', '=', self.move_id.id)])
        if asset:
            asset.write({'invoice_date': self.move_id.date})

        return res

