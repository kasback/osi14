# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class StockBarcodesAssetReadLog(models.Model):
    _name = "stock.barcodes.read.asset.log"
    _description = "Log barcode scanner"
    _order = "id DESC"

    name = fields.Char(string="Barcode Scanned")
    res_model_id = fields.Many2one(comodel_name="ir.model", index=True)
    res_id = fields.Integer(index=True)
    asset_id = fields.Many2one(comodel_name="account.asset.asset", index=True)
    location_id = fields.Many2one(comodel_name="stock.asset.location")
    product_qty = fields.Float(string="Quantity", digits="Product Unit of Measure")
    manual_entry = fields.Boolean(string="Manual entry")
    log_line_ids = fields.One2many(
        comodel_name="stock.barcodes.read.log.asset.line",
        inverse_name="read_log_id",
        string="Scanning log details",
    )


class StockBarcodesReadAssetLogLine(models.Model):
    """
    The goal of this model is store detail about scanning log, for example,
    when user read in pickings the product quantity can be distributed in more
    than one stock move line.
    This help to know what records have been affected by a scanning read.
    """

    _name = "stock.barcodes.read.log.asset.line"
    _description = "Stock barcodes read log lines"

    read_log_id = fields.Many2one(
        comodel_name="stock.barcodes.read.asset.log",
        string="Scanning log",
        ondelete="cascade",
        readonly=True,
    )
    move_line_id = fields.Many2one(
        comodel_name="account.asset.stock.line", string="Stock move lines", readonly=True
    )
    product_qty = fields.Float(
        string="Quantity scanned", digits="Product Unit of Measure", readonly=True
    )
