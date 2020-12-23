# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models


class WizStockBarcodesReadAssets(models.AbstractModel):
    _name = "wiz.stock.barcodes.read.assets"
    _inherit = "barcodes.barcode_events_mixin"
    _description = "Wizard to read barcode"
    # To prevent remove the record wizard until 2 days old
    _transient_max_hours = 48

    barcode = fields.Char('Code de barre')
    res_model_id = fields.Many2one(comodel_name="ir.model", index=True)
    res_id = fields.Integer(index=True)
    asset_id = fields.Many2one(comodel_name="account.asset.asset", string='Immobilisation')
    location_id = fields.Many2one(comodel_name="account.asset.location", string='Emplacement')
    product_qty = fields.Float(digits="Product Unit of Measure")
    manual_entry = fields.Boolean(string="Entrée Manuelle")
    # Computed field for display all scanning logs from res_model and res_id
    # when change product_id
    scan_log_ids = fields.Many2many(
        comodel_name="stock.barcodes.read.asset.log", compute="_compute_scan_log_ids"
    )
    message_type = fields.Selection(
        [
            ("info", "Barcode read with additional info"),
            ("not_found", "No barcode found"),
            ("more_match", "More than one matches found"),
            ("success", "Barcode read correctly"),
        ],
        readonly=True,
    )
    message = fields.Char(readonly=True)

    @api.onchange("location_id")
    def onchange_location_id(self):
        self.asset_id = False

    def _set_messagge_info(self, message_type, message):
        """
        Set message type and message description.
        For manual entry mode barcode is not set so is not displayed
        """
        self.message_type = message_type
        if self.barcode:
            self.message = _("Barcode: %s (%s)") % (self.barcode, message)
        else:
            self.message = "%s" % message

    def process_barcode(self, barcode):
        domain = self._barcode_domain(barcode.strip().replace(' ', '+'))
        asset = self.env["account.asset.asset"].search(domain)

        if asset:
            self.barcode = barcode
            self.action_product_scaned_post(asset)
            self.action_done()
            self._set_messagge_info("success", _("Barcode read correctly"))
            return
        else:
            self.barcode = False
            self._set_messagge_info("not_found", _("Barcode not found"))

    def _barcode_domain(self, barcode):
        return [("code_inventaire", "=", barcode)]

    def on_barcode_scanned(self, barcode):
        self.reset_qty()
        self.process_barcode(barcode)

    def check_done_conditions(self):
        if not self.product_qty:
            self._set_messagge_info("info", _("Waiting quantities"))
            return False
        if self.manual_entry:
            self._set_messagge_info("success", _("Manual entry OK"))
        return True

    def action_done(self):
        if not self.check_done_conditions():
            return False
        self._add_read_log()
        return True

    def action_cancel(self):
        return True

    def action_product_scaned_post(self, asset):
        self.asset_id = asset
        self.product_qty = 0.0 if self.manual_entry else 1.0

    def action_manual_entry(self):
        return True

    def _prepare_scan_log_values(self, log_detail=False):
        return {
            "name": self.barcode,
            "location_id": self.location_id.id,
            "asset_id": self.asset_id.id,
            "product_qty": self.product_qty,
            "manual_entry": self.manual_entry,
            "res_model_id": self.res_model_id.id,
            "res_id": self.res_id,
        }

    def _add_read_log(self, log_detail=False):
        if self.product_qty:
            vals = self._prepare_scan_log_values(log_detail)
            self.env["stock.barcodes.read.asset.log"].create(vals)

    @api.depends("asset_id")
    def _compute_scan_log_ids(self):
        logs = self.env["stock.barcodes.read.asset.log"].search(
            [
                ("res_model_id", "=", self.res_model_id.id),
                ("res_id", "=", self.res_id),
                ("location_id", "=", self.location_id.id),
                ("asset_id", "=", self.asset_id.id),
            ],
            limit=10,
        )
        self.scan_log_ids = logs

    def reset_qty(self):
        self.product_qty = 0

    def action_undo_last_scan(self):
        return True
