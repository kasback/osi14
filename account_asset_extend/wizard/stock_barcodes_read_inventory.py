# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import first


class WizStockBarcodesReadInventoryAsset(models.TransientModel):
    _name = "wiz.stock.barcodes.read.inventory.asset"
    _inherit = "wiz.stock.barcodes.read.assets"

    asset_stock_id = fields.Many2one(comodel_name="account.asset.stock", readonly=True)
    inventory_product_qty = fields.Float(
        string="Inventory quantities", digits="Product Unit of Measure", readonly=True
    )

    def name_get(self):
        return [
            (
                rec.id,
                "{} - {} - {}".format(
                    _("Barcode reader"), rec.asset_stock_id.name, self.env.user.name
                ),
            )
            for rec in self
        ]

    def _prepare_inventory_line(self):
        return {
            "asset_stock_id": self.asset_stock_id.id,
            "asset_id": self.asset_id.id,
            "location_id": self.location_id.id,
            "product_qty": self.product_qty,
        }

    def _prepare_inventory_line_domain(self, log_scan=False):
        """
        Use the same domain for create or update a stock inventory line.
        Source data is scanning log record if undo or wizard model if create or
        update one
        """
        record = log_scan or self
        return [
            ("asset_stock_id", "=", self.asset_stock_id.id),
            ("asset_id", "=", record.asset_id.id),
            ("location_id", "=", record.location_id.id),
        ]

    def _add_inventory_line(self):
        AssetStockInventoryLine = self.env["account.asset.stock.line"]
        line = AssetStockInventoryLine.search(self._prepare_inventory_line_domain(), limit=1)
        if line:
            if line.product_qty + self.product_qty > 1:
                raise ValidationError('Vous avez déjà scanné cet immobilisation')
            line.write({"product_qty": line.product_qty + self.product_qty})
        else:
            line = AssetStockInventoryLine.create(self._prepare_inventory_line())
        self.inventory_product_qty = line.product_qty

    def check_done_conditions(self):
        return super().check_done_conditions()

    def action_done(self):
        result = super().action_done()
        if result:
            self._add_inventory_line()
        return result

    def action_manual_entry(self):
        result = super().action_manual_entry()
        if result:
            self.action_done()
        return result

    def reset_qty(self):
        super().reset_qty()
        self.inventory_product_qty = 0.0

    def action_undo_last_scan(self):
        res = super().action_undo_last_scan()
        log_scan = first(
            self.scan_log_ids.filtered(lambda x: x.create_uid == self.env.user)
        )
        if log_scan:
            inventory_line = self.env["account.asset.stock.line"].search(
                self._prepare_inventory_line_domain(log_scan=log_scan)
            )
            if inventory_line.asset_stock_id.state == "done":
                raise ValidationError(
                    _(
                        "You can not remove a scanning log from an inventory "
                        "validated"
                    )
                )
            if inventory_line:
                qty = inventory_line.product_qty - log_scan.product_qty
                inventory_line.product_qty = max(qty, 0.0)
                self.inventory_product_qty = inventory_line.product_qty
        log_scan.unlink()
        return res
