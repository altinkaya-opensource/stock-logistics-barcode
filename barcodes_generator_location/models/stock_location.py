# Copyright 2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import json

from lxml import etree

from odoo import api, models


class StockLocation(models.Model):
    _name = "stock.location"
    _description = "Stock Location"
    _inherit = ["stock.location", "barcode.generate.mixin"]

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """Add readonly modifier to barcode field and handle stock_barcodes compatibility.

        If stock_barcodes module is installed, it adds a separate barcode group.
        We merge our generator fields into their group and remove our duplicate group.
        """
        result = super().get_view(view_id=view_id, view_type=view_type, **options)

        if view_type != "form":
            return result

        doc = etree.XML(result["arch"])

        # Find stock_barcodes group (if exists)
        stock_barcodes_group = doc.xpath("//group[@name='barcode']")
        our_group = doc.xpath("//group[@name='barcodes_generator_location']")

        if not our_group:
            # Our group is not in the view (might be filtered by groups permission)
            return result

        our_group = our_group[0]

        if stock_barcodes_group:
            # stock_barcodes module is installed
            # Move our generator fields to their barcode group and remove our duplicate barcode field
            stock_barcodes_group = stock_barcodes_group[0]
            stock_barcodes_barcode_field = doc.xpath("//group[@name='barcode']//field[@name='barcode']")

            if stock_barcodes_barcode_field:
                stock_barcodes_barcode_field = stock_barcodes_barcode_field[0]

                # Move all our fields (except barcode) to stock_barcodes group
                for child in list(our_group):
                    if child.tag == 'field' and child.get('name') == 'barcode':
                        # Skip our duplicate barcode field
                        continue
                    # Move other fields/buttons after stock_barcodes' barcode field
                    stock_barcodes_barcode_field.addnext(child)

                # Remove our now-empty group
                our_group.getparent().remove(our_group)

                # Use stock_barcodes' barcode field for modifier
                barcode_field = stock_barcodes_barcode_field
            else:
                # Unexpected: stock_barcodes group exists but has no barcode field
                # Use our barcode field
                barcode_field = doc.xpath("//group[@name='barcodes_generator_location']//field[@name='barcode']")
                barcode_field = barcode_field[0] if barcode_field else None
        else:
            # stock_barcodes module is NOT installed, use our barcode field
            barcode_field = doc.xpath("//group[@name='barcodes_generator_location']//field[@name='barcode']")
            barcode_field = barcode_field[0] if barcode_field else None

        # Add readonly modifier to barcode field
        if barcode_field is not None:
            modifier = {"readonly": [("generate_type", "=", "sequence")]}
            barcode_field.set("modifiers", json.dumps(modifier))

        result["arch"] = etree.tostring(doc)
        return result
