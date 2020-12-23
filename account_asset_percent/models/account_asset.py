# -*- encoding: utf-8 -*-

import calendar
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    by_percent = fields.Boolean('En pourcentage')
    percent = fields.Float('Pourcentage')

    @api.onchange('percent')
    def onchange_percent(self):
        if self.percent:
            self.method_number = 100 / (self.percent or 100) * 12 / (self.method_period or 12)

    @api.onchange('method_number')
    def onchange_method_number(self):
        self.percent = 100 / (self.method_number or 1) * 12 / (self.method_period or 12)

    @api.onchange('method_period')
    def onchange_method_period(self):
        self.percent = 100 / (self.method_number or 1) * 12 / (self.method_period or 12)
        self.method_number = 100 / (self.percent or 100) * 12 / (self.method_period or 12)


    def _compute_board_amount(self, sequence, residual_amount, amount_to_depr, undone_dotation_number,
                              posted_depreciation_line_ids, total_days, depreciation_date):
        amount = 0
        if sequence == undone_dotation_number:
            amount = residual_amount
        else:
            if self.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if self.prorata:
                    if self.by_percent:
                        amount = amount_to_depr * self.percent/100
                    else:
                        amount = amount_to_depr / self.method_number
                    if sequence == 1:
                        date = self.date
                        if self.method_period % 12 != 0:
                            month_days = calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                            if self.by_percent:
                                amount = (amount_to_depr * self.percent/100) / month_days * days
                            else:
                                amount = (amount_to_depr / self.method_number) / month_days * days
                        else:

                            months = 13 - date.month
                            if self.by_percent:
                                amount = (amount_to_depr * self.percent/100) / 12 * months
                            else:
                                amount = (amount_to_depr / self.method_number) / 12 * months

            elif self.method == 'degressive':
                amount = residual_amount * self.method_progress_factor
                if self.prorata:
                    if sequence == 1:
                        months = 13 - depreciation_date.month
                        amount = (residual_amount * self.method_progress_factor) / 12 * months
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
    #         date_dep = datetime.strptime(self._get_last_depreciation_date()[self.id], DF).date()
    #         if self.prorata:
    #             depreciation_date = datetime.strptime(self._get_last_depreciation_date()[self.id][:4] + '-12-31', DF).date()
    #         else:
    #             # depreciation_date = 1st of January of purchase year
    #             if self.method_period >= 12:
    #                 asset_date = datetime.strptime(self.date[:4] + '-12-31', DF).date()
    #             else:
    #                 asset_date = datetime.strptime(self.date[:7] + '-01', DF).date()
    #
    #                 # date_asset = fields.Date.from_string(self.date)
    #                 # asset_date = datetime(date_asset.year, date_asset.month, 1) + relativedelta(months=1)
    #             # if we already have some previous validated entries, starting date isn't 1st January but last entry + method period
    #             if posted_depreciation_line_ids and posted_depreciation_line_ids[0].depreciation_date:
    #                 last_depreciation_date = datetime.strptime(posted_depreciation_line_ids[0].depreciation_date, DF).date()
    #                 depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
    #             else:
    #                 depreciation_date = asset_date
    #         day = depreciation_date.day
    #         month = depreciation_date.month
    #         year = depreciation_date.year
    #         total_days = (year % 4) and 365 or 366
    #
    #         undone_dotation_number = self._compute_board_undone_dotation_nb(depreciation_date, total_days)
    #         sequence = 0
    #
    #         for x in range(len(posted_depreciation_line_ids), int(undone_dotation_number)):
    #             sequence = x + 1
    #             amount = self._compute_board_amount(sequence, residual_amount, amount_to_depr, undone_dotation_number,
    #                                                 posted_depreciation_line_ids, total_days, date_dep)
    #             amount = self.currency_id.round(amount)
    #             if amount <= residual_amount:
    #                 residual_amount -= amount
    #                 vals = {
    #                     'amount': amount,
    #                     'asset_id': self.id,
    #                     'sequence': sequence,
    #                     'name': (self.code or '') + '/' + str(sequence),
    #                     'remaining_value': residual_amount,
    #                     'depreciated_value': self.value - (self.salvage_value + residual_amount),
    #                     'depreciation_date': depreciation_date.strftime(DF),
    #                 }
    #                 commands.append((0, False, vals))
    #                 # Considering Depr. Period as months
    #                 depreciation_date = date(year, month, day) + relativedelta(months=+self.method_period)
    #                 day = depreciation_date.day
    #                 month = depreciation_date.month
    #                 year = depreciation_date.year
    #
    #     self.write({'depreciation_line_ids': commands})
    #     if round(self.depreciation_line_ids[-1].remaining_value, 2) > 0:
    #         values = {
    #                 'amount': self.depreciation_line_ids[-1].remaining_value,
    #                 'asset_id': self.id,
    #                 'sequence': sequence+1,
    #                 'name': (self.code or '') + '/' + str(sequence+1),
    #                 'remaining_value': 0,
    #                 'depreciated_value': self.value,
    #                 'depreciation_date': depreciation_date.strftime(DF),
    #             }
    #         self.write({'depreciation_line_ids': [(0, False, values)]})
    #
    #     return True




