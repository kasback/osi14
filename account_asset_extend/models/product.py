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


class ProductTemplate(models.Model):
    _inherit = "product.template"

    company_id = fields.Many2one('res.company', string=u'Société', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get(
                                     'product.template'))

    code_article = fields.Char('Code')
    marque = fields.Char('Marque')
    modele = fields.Char('Modèle')
    dimension = fields.Char('Dimension')
    sous_famille = fields.Many2one('product.sous.famille')
    ref = fields.Char('Référence')
    couleur = fields.Char('Couleur de l\'article')
    autres_infos = fields.Char('Autres  infos')
    niveau = fields.Many2one('stock.location', string=u'Niveau')
    salle = fields.Many2one('stock.location', string=u'Salle')
    date_mise_service = fields.Char('Date de mise en service')
    supplier_id = fields.Many2one('res.partner', 'Fournisseur')
    invoice_number = fields.Char('N° de Facture')
    invoice_date = fields.Char('Date facture')
    bl_date = fields.Char('Date BL')
    date_aquisition = fields.Char('Date d\'acquisition')
    bc_marche = fields.Char('BC/MARCHE')
    be = fields.Char('BE')
    op = fields.Char('OP')
    recensement = fields.Char('Recensement')
    account_id = fields.Char('Compte Comptable')
    observations = fields.Text('Observations')
    num_ordre = fields.Char('N° ordre')
    taux_ammortissement = fields.Float('Taux d\'ammortissement')


class SousFamilleProduct(models.Model):
    _name = 'product.sous.famille'

    name = fields.Char('Nom')
    parent_id = fields.Char('Parent')
