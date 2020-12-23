# -*- coding: utf-8 -*-


import datetime

from odoo import models, fields, api


class AssetControl(models.Model):
    _name = 'asset.control'

    fiscal_year = fields.Many2one('date.range', 'Exercice fiscal', required=True)
    control_ids = fields.One2many('asset.control.line', 'asset_control_id',
                                 string='Asset Control', readonly=True,)
    control_accounting_ids = fields.One2many('asset.control.accounting', 'asset_control_id',
                                 string='Asset Control Accounting', readonly=True,)

    # generate the control
    def asset_control(self):
        self.control_ids = False
        self.control_accounting_ids = False
        # Control Accounting
        depreciation_ids = self.env['account.asset.depreciation.line'].search([('depreciation_date', '>=', self.fiscal_year.date_start),
                                                                               ('depreciation_date', '<=',self.fiscal_year.date_end),
                                                                               ('move_check', '<=', False),

                                                                               ])
        for dep in depreciation_ids:
            self.env['asset.control.accounting'].create({'asset_control_id': self.ids[0],
                                                   'depreciation_date': dep.depreciation_date,
                                                   'asset_id': dep.asset_id.id,
                                                   'amount': dep.amount,
                                                   'account_id': dep.asset_id.category_id.account_asset_id.id,
                                                   })
        # Control Immobilisation
        accounts_ids = self.env['account.account'].search([('code', '=like', '21%')]) | self.env['account.account'].search([('code', '=like', '22%')]) | \
                       self.env['account.account'].search([('code', '=like', '23%')])
        for account_id in accounts_ids:
            if self.fiscal_year:
                print(self.fiscal_year,"fiscal_year")
                query_asset = """
                                            SELECT sum(value)
                                            FROM account_asset_asset
                                            INNER JOIN account_asset_category ON account_asset_asset.category_id = account_asset_category.id
                                            WHERE account_asset_category.account_asset_id = %s
                                            GROUP BY account_asset_category.account_asset_id
                                        """ % (account_id.id,)
                self.env.cr.execute(query_asset)
                valeur_brut = self.env.cr.fetchone()
                print(valeur_brut, 'valeur_brut')
                query_moves = """
                                                    SELECT SUM(debit) - SUM(credit) as solde
                                                    FROM account_move_line
                                                    WHERE account_id = %s and EXTRACT(year FROM "date") = %s
                                                    GROUP BY account_id
                                             """ % (account_id.id, datetime.datetime.strptime(str(self.fiscal_year.date_start), '%Y-%m-%d').year)
                self.env.cr.execute(query_moves)
                solde_move = self.env.cr.fetchone()

            vals = {}
            if (solde_move and solde_move[0]) or (valeur_brut and valeur_brut[0]):
                    print(solde_move, valeur_brut, 'VALEUR BRUT')
                    self.env['asset.control.line'].create({'asset_control_id': self.ids[0],
                                                      'account_id': account_id.id,
                                                      'balance_asset': valeur_brut and valeur_brut[0],
                                                      'balance_account': solde_move and solde_move[0],
                                                      'diff_amount': valeur_brut and solde_move and valeur_brut[0] - solde_move[0],
                                                      'is_reconciled': False,
                                                      'unreconciled_ids': [(0, 0, vals)],
                                                      })
        # Control ammortissement
        accounts_ids = self.env['account.account'].search([('code', '=like', '28%')])
        for account_id in accounts_ids:
            if self.fiscal_year:
                query_asset = """
                                                     SELECT SUM(credit) - SUM(debit) as solde
                                                     FROM account_move_line
                                                     INNER JOIN account_move ON account_move_line.move_id = account_move.id
                                                     WHERE account_id = %s and EXTRACT(year FROM account_move.date) = %s
                                                     GROUP BY account_id
                                         """ % (
                account_id.id, datetime.datetime.strptime(str(self.fiscal_year.date_start), '%Y-%m-%d').year)
                self.env.cr.execute(query_asset)
                value_without_asset = self.env.cr.fetchone()
                query_moves = """
                                                     SELECT SUM(credit) - SUM(debit) as solde
                                                     FROM account_move_line
                                                     INNER JOIN account_move ON account_move_line.move_id = account_move.id
                                                     WHERE account_move.asset_id is not NULL AND account_id = %s
                                                     GROUP BY account_id
                                              """ % (
                account_id.id, )
                self.env.cr.execute(query_moves)
                value_with_asset = self.env.cr.fetchone()

            vals = {}
            if value_without_asset and value_without_asset[0] or value_with_asset and value_with_asset[0]:
                self.env['asset.control.line'].create({'asset_control_id': self.ids[0],
                                                  'account_id': account_id.id,
                                                  'balance_asset': value_without_asset and value_without_asset[0],
                                                  'balance_account': value_with_asset and value_with_asset[0],
                                                  'diff_amount': value_without_asset and value_with_asset and value_without_asset[0] - value_with_asset[0],
                                                  'is_reconciled': False,
                                                  'unreconciled_ids': [(0, 0, vals)],
                                                  })
        return True

class AssetControlLine(models.Model):
    _name = "asset.control.line"

    account_id = fields.Many2one('account.account', 'Compte')
    balance_asset = fields.Float(string='Solde Immobilisation')
    balance_account = fields.Float(string='Solde Ecritures Comptables')
    diff_amount = fields.Float(string='Difference')
    is_reconciled = fields.Boolean(u'Reconcilie', default=True)
    unreconciled_ids = fields.One2many('asset.unreconciled', 'asset_control_line_id',
                                       string='Asset Unreconciled', readonly=True,)
    asset_control_id = fields.Many2one('asset.control', 'Asset Control')


class AssetControlAccounting(models.Model):
    _name = "asset.control.accounting"

    asset_id = fields.Many2one('account.asset.asset', string='Asset', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', 'Compte')
    amount = fields.Float(string=u'Amortissement', digits=0, required=True)
    depreciation_date = fields.Date('Depreciation Date')
    asset_control_id = fields.Many2one('asset.control', 'Asset Control')


class AssetUnreconciled(models.Model):
    _name = "asset.unreconciled"

    account_id = fields.Many2one('account.account', 'Compte')
    move_id = fields.Many2one('account.move', 'Piece Comptable')
    date = fields.Date(string='Date Ecriture')
    journal_id = fields.Many2one('account.journal', 'Journal')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    asset_control_line_id = fields.Many2one('asset.control.line', 'Asset Control Line')
