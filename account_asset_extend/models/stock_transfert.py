# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class AssetStock(models.Model):
    _name = "account.asset.transfert"

    state = fields.Selection([('draft', 'Brouillon'), ('confirm', 'En cours'), ('done', 'Validé')], string="État", default='draft')
    name = fields.Char('Réference du Transfert', required=True)
    date = fields.Date('Date Inventaire')
    line_ids = fields.One2many('account.asset.transfert.line', 'asset_transfert_id', string="Lignes de transfert d\'immobilisation")
    partner_id = fields.Many2one('res.partner', 'Responsable')

    def action_start(self):
        for inventory in self:
            if inventory.state != 'draft':
                continue
            vals = {
                'state': 'confirm',
                'date': fields.Datetime.now() if not self.date else self.date
            }
            self.write(vals)
            return self.action_open_inventory_lines()

    def action_validate(self):
        self.line_ids._generate_moves()
        self.write({'state': 'done'})

    def action_draft(self):
        self.line_ids.unlink()
        self.write({'state': 'draft'})

    def action_open_inventory_lines(self):
        self.ensure_one()
        view = self.env.ref('account_asset_extend.stock_asset_transfert_line_tree')
        action = {
            'type': 'ir.actions.act_window',
            'views': [(view.id, 'tree')],
            'view_mode': 'tree',
            'name': 'Lignes de Transfert',
            'res_model': 'account.asset.transfert.line',
        }
        context = {
            'default_is_editable': True,
            'default_asset_transfert_id': self.id,
        }
        # Define domains and context
        domain = [
            ('asset_transfert_id', '=', self.id),
            # ('location_id.usage', '=', 'internal')
        ]
        action['context'] = context
        action['domain'] = domain
        return action


class AssetTransfertLine(models.Model):
    _name = "account.asset.transfert.line"

    state = fields.Selection('Status', related='asset_transfert_id.state')
    asset_transfert_id = fields.Many2one('account.asset.transfert', string='Inventaire d\'immobilisation')
    asset_id = fields.Many2one('account.asset.asset', string="Immobilisation")
    num_ordre = fields.Char(related='asset_id.num_ordre', string="Numéro d'ordre")
    location_id = fields.Many2one('account.asset.location', related='asset_id.num_salle', string="Lieu")
    location_dest_id = fields.Many2one('account.asset.location', string="Lieu de destination")

    def _generate_moves(self):
        vals_list = []
        for line in self:
            vals = line._get_move_values(line.location_id.id, line.location_dest_id.id)
            line.asset_id.write({
                'num_salle': line.location_dest_id.id
            })
            vals_list.append(vals)
        return self.env['account.asset.stock.move'].create(vals_list)

    def _get_move_values(self,location_id, location_dest_id):
        self.ensure_one()
        return {
            'name': 'TRANSFERT IMM:' + (self.asset_transfert_id.name or ''),
            'asset_id': self.asset_id.id,
            'date': self.asset_transfert_id.date,
            'asset_uom_qty': 1.0,
            'type': 'trnf',
            # 'inventory_asset_id': self.asset_stock_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
        }

