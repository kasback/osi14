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


class AccountAsset(models.Model):
    _inherit = "account.asset.asset"
    # _rec_name = 'display_name'

    display_name = fields.Char('Nom Affiché', compute='_compute_inventory_code', store=True)
    product_id = fields.Many2one('product.template', u'Article')
    lot_id = fields.Many2one('stock.production.lot', u'Numéro de serie')
    num_salle = fields.Many2one('account.asset.location', string="Salle")
    niveau_id = fields.Many2one('account.asset.location', related='num_salle.parent_id', string="Niveau")
    num_ordre = fields.Char(u'Numéro d\'ordre')
    code_inventaire = fields.Char('Code d\'inventaire', compute='_compute_inventory_code', default='', store=True)
    bar_code_print = fields.Char('Code à imprimer', compute='_compute_inventory_code', default='', store=True)
    affectataire = fields.Many2one('hr.employee', string='Affectataire')
    account_id = fields.Many2one('account.account', related='category_id.account_asset_id', string='Compte Comptable')
    num_so = fields.Char('N° de BC/MARCHE')
    num_facture = fields.Char('Numéro de facture')
    date_bl = fields.Date('Date BL')
    valeure_aquisition = fields.Float('Valeur acquisition HT')
    be = fields.Char('BE')
    op = fields.Char('OP')
    date_aquisition = fields.Char('Date d\'acquisition')
    sous_famille = fields.Many2one('product.sous.famille', string="Sous Famille")

    # @api.model
    # def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
    #     if args is None:
    #         args = []
    #     domain = args + [('display_name', operator, name)]
    #     asset_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
    #     print('assets', self.browse(asset_ids).with_user(name_get_uid))
    #     return models.lazy_name_get(self.browse(asset_ids).with_user(name_get_uid))

    @api.depends('name', 'num_ordre', 'num_salle', 'category_id.account_asset_id', 'category_id.inv_liste')
    def _compute_inventory_code(self):
        for rec in self:
            rec.code_inventaire = ''
            rec.bar_code_print = ''
            rec.display_name = ''
            if not rec.category_id.inv_liste:
                if rec.num_salle and rec.category_id.account_asset_id and rec.num_ordre and rec.name:
                    salle = rec.num_salle.name.split('/')
                    if len(salle) > 1:
                        rec.code_inventaire = rec.category_id.account_asset_id.code[
                                              :5] + salle[0] + salle[1] + rec.num_ordre
                        rec.bar_code_print = '1' + salle[1] + rec.num_ordre
                    else:
                        rec.code_inventaire = rec.category_id.account_asset_id.code[
                                              :5] + salle[0] + rec.num_ordre
                        rec.bar_code_print = '1' + salle[0] + rec.num_ordre
                    rec.display_name = '[' + rec.code_inventaire + ']' + ' ' + rec.name

    @api.model
    def create(self, vals):
        category_id = self.env['account.asset.category'].browse(vals['category_id'])
        if not category_id.inv_liste:
            vals['num_ordre'] = self.env['ir.sequence'].next_by_code('asset_order_number')
        return super(AccountAsset, self).create(vals)

    def action_print(self):
        return self.env.ref('account_asset_extend.report_asset_label_A4_57x35').with_context(discard_logo_check=True).report_action(self.id)

    def action_open_asset_moves(self):
        self.ensure_one()
        action = self.env.ref('account_asset_extend.action_account_asset_stock_move').read()[0]
        context = {
            'default_asset_id': self.id,
        }
        domain = [
            ('asset_id', '=', self.id),
        ]
        action['domain'] = domain
        action['context'] = context
        return action


class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'

    inv_liste = fields.Boolean('Inventoriable par liste', default=False)


class AccountAssetLocation(models.Model):
    _name = 'account.asset.location'

    name = fields.Char('Nom de l\'emplacement')
    usage = fields.Selection([('internal', 'Emplacement Interne'), ('view', 'Vue')], default="internal")
    parent_id = fields.Many2one('account.asset.location', string="Emplacement Parent")
    line_ids = fields.One2many('account.asset.location.line', 'asset_location_id')

    def _get_inventory_lines_values(self):
        assets = self.env['account.asset.asset'].search([('num_salle', '=', self.id)])
        vals = []
        for asset in assets:
            if asset not in self.line_ids.mapped('asset_id'):
                res = {
                    'asset_id': asset.id,
                    'asset_location_id': self.id,
                }
                vals.append(res)
        return vals

    def action_display_asset_stock(self):
        self.ensure_one()
        self.env['account.asset.location.line'].create(self._get_inventory_lines_values())
        action = self.env.ref('account_asset_extend.action_display_asset_stock').read()[0]
        context = {
            'asset_location_id': self.id,
        }
        domain = [
            ('asset_location_id', '=', self.id),
        ]
        action['domain'] = domain
        action['context'] = context
        return action


class AccountAssetLocationLine(models.Model):
    _name = 'account.asset.location.line'

    asset_id = fields.Many2one('account.asset.asset', string="Immobilisation")
    num_ordre = fields.Char(related='asset_id.num_ordre', string="Numéro d'ordre")
    asset_location_id = fields.Many2one('account.asset.location', string='Emplacement')

