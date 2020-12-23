# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class AssetStock(models.Model):
    _name = "account.asset.stock"

    state = fields.Selection([('draft', 'Brouillon'), ('confirm', 'En cours'), ('done', 'Validé')], string="État", default='draft')
    name = fields.Char('Réference d\'ajustement', required=True)
    location_id = fields.Many2one('account.asset.location', string="Emplacement")
    specific_location = fields.Boolean('Inventaire d\'un emplacement', default="True")
    date = fields.Date('Date Inventaire')
    line_ids = fields.One2many('account.asset.stock.line', 'asset_stock_id', string="Lignes d\'inventaire immobilisation")
    partner_id = fields.Many2one('res.partner', 'Responsable')

    def action_start(self):
        for inventory in self:
            if inventory.state != 'draft':
                continue
            vals = {
                'state': 'confirm',
                'date': fields.Datetime.now() if not self.date else self.date
            }
            if not inventory.line_ids:
                self.env['account.asset.stock.line'].create(inventory._get_inventory_lines_values())
            inventory.write(vals)
            return self.action_open_inventory_lines()

    def _get_inventory_lines_values(self):
        location = False
        if self.specific_location:
            location = self.location_id.id

        assets = self.env['account.asset.asset'].search([('num_salle', '=', location)])
        vals = []
        for asset in assets:
            res = {
                'asset_id': asset.id,
                'asset_stock_id': self.id,
                'location_id': location,
                'product_qty': 0 if location else 0,
                'theoretical_qty': 1 if location else 0
            }
            vals.append(res)
        return vals

    def action_validate(self):
        self.line_ids._generate_moves()
        self.write({'state': 'done'})

    def action_draft(self):
        self.line_ids.unlink()
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'canceled'})

    def action_open_inventory_lines(self):
        self.ensure_one()
        view = self.env.ref('account_asset_extend.stock_asset_inventory_line_tree') if self.specific_location else self.env.ref('account_asset_extend.stock_asset_inventory_line_tree_no_location')
        action = {
            'type': 'ir.actions.act_window',
            'views': [(view.id, 'tree')],
            'view_mode': 'tree',
            'name': 'Lignes d\'inventaire',
            'res_model': 'account.asset.stock.line',
        }
        context = {
            'default_is_editable': True,
            'default_asset_stock_id': self.id,
        }
        # Define domains and context
        domain = [
            ('asset_stock_id', '=', self.id),
            # ('location_id.usage', '=', 'internal')
        ]
        action['context'] = context
        action['domain'] = domain
        return action

    def action_open_asset_moves(self):
        self.ensure_one()
        action = self.env.ref('account_asset_extend.action_account_asset_stock_move').read()[0]
        context = {
            'default_inventory_asset_id': self.id,
        }
        domain = [
            ('inventory_asset_id', '=', self.id),
        ]
        action['domain'] = domain
        action['context'] = context
        return action


class AssetStockLine(models.Model):
    _name = "account.asset.stock.line"

    is_editable = fields.Boolean(help="Technical field to restrict the edition.")
    state = fields.Selection('Status', related='asset_stock_id.state')
    asset_stock_id = fields.Many2one('account.asset.stock', string='Inventaire d\'immobilisation')
    asset_id = fields.Many2one('account.asset.asset', string="Immobilisation")
    num_ordre = fields.Char(related='asset_id.num_ordre', string="Numéro d'ordre")
    location_id = fields.Many2one('account.asset.location', related='asset_stock_id.location_id', string="Lieu")
    new_location_id = fields.Many2one('account.asset.location', string="Lieu")
    theoretical_qty = fields.Float('En Stock')
    product_qty = fields.Float('Compté')
    difference_qty = fields.Float('Différence', compute='_compute_difference')

    @api.depends('product_qty', 'theoretical_qty')
    def _compute_difference(self):
        for line in self:
            if line.product_qty > 1:
                raise ValidationError('Une immobilisation doît être unique')
            if line.product_qty < 0:
                raise ValidationError('Vous ne pouvez pas rentrer des valeurs négatives')
            line.difference_qty = line.product_qty - line.theoretical_qty

    def _generate_moves(self):
        vals_list = []
        for line in self:
            virtual_location = line._get_virtual_location()
            if float_is_zero(line.difference_qty, precision_rounding=1):
                continue
            if line.difference_qty == 1:  # found more than expected
                if line.asset_stock_id.specific_location:
                    dest_location_id = line.asset_stock_id.location_id
                else:
                    dest_location_id = line.new_location_id

                if line.asset_id.num_salle:
                    virtual_location = line.asset_id.num_salle
                line.asset_id.write({
                    'num_salle': dest_location_id.id
                })
                vals = line._get_move_values(line.difference_qty, virtual_location.id, dest_location_id.id, False)
            elif line.difference_qty == -1:  # found less than expected
                vals = line._get_move_values(abs(line.difference_qty), line.location_id.id, virtual_location.id, True)
                line.asset_id.write({
                    'num_salle': False
                })
            vals_list.append(vals)
        return self.env['account.asset.stock.move'].create(vals_list)

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        self.ensure_one()
        return {
            'name': 'INV IMM:' + (self.asset_stock_id.name or ''),
            'asset_id': self.asset_id.id,
            'asset_uom_qty': qty,
            'type': 'aju',
            'date': self.asset_stock_id.date,
            'inventory_asset_id': self.asset_stock_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id
        }

    def _get_virtual_location(self):
        return self.env.ref('account_asset_extend.stock_location_locations_virtual_asset')


class AssetStockMove(models.Model):
    _name = 'account.asset.stock.move'

    name = fields.Char('Réference du mouvement')
    asset_id = fields.Many2one('account.asset.asset', 'Immobilisation')
    num_ordre = fields.Char(related='asset_id.num_ordre', string="Numéro d'ordre")
    asset_uom_qty = fields.Float('Quantité')
    date = fields.Date('Date')
    inventory_asset_id = fields.Many2one('account.asset.stock', 'Inventaire d\'immobilisation')
    location_id = fields.Many2one('account.asset.location', 'Emplacement Source')
    location_dest_id = fields.Many2one('account.asset.location', 'Emplacement Destination')
    type = fields.Selection([('aju', 'Ajustement'), ('trnf', 'Transfert')], default='aju')


class StockInventory(models.Model):
    _inherit = ["barcodes.barcode_events_mixin", "account.asset.stock"]
    _name = "account.asset.stock"

    def action_barcode_scan(self):
        self.action_start()
        action = self.env.ref(
            "account_asset_extend.action_stock_barcodes_read_asset_inventory"
        ).read()[0]
        action["context"] = {
            "default_location_id": self.location_id.id,
            "default_asset_stock_id": self.id,
            "default_res_model_id": self.env.ref("account_asset_extend.model_account_asset_stock").id,
            "default_res_id": self.id,
        }
        return action
