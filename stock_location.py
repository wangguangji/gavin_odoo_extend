# -*- coding: utf-8 -*-

from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp.tools import float_compare
import logging
_logger = logging.getLogger(__name__)

class stock_location(osv.osv):
    
    _inherit = "stock.location"
    
    def _product_reserve(self, cr, uid, ids, product_id, product_qty, context=None, lock=False):
        result = []
        amount = 0.0
        if context is None:
            context = {}
        uom_obj = self.pool.get('product.uom')
        uom_rounding = self.pool.get('product.product').browse(cr, uid, product_id, context=context).uom_id.rounding
        if context.get('uom'):
            uom_rounding = uom_obj.browse(cr, uid, context.get('uom'), context=context).rounding

        locations_ids = self.search(cr, uid, [('location_id', 'child_of', ids)])
        # Fetch only the locations in which this product has ever been processed (in or out)
        cr.execute("""SELECT l.id FROM stock_location l WHERE l.id in %s AND
                    EXISTS (SELECT 1 FROM stock_move m WHERE m.product_id = %s
                            AND ((state = 'done' AND m.location_dest_id = l.id)
                                OR (state in ('done','assigned') AND m.location_id = l.id)))
                   """, (tuple(locations_ids), product_id,))

        locations_ids = cr.fetchall()
        
        
        if len(locations_ids)>0:
            cr.execute(""" select a.location_id  from stock_report_prodlots as a 
                           left join stock_production_lot as lot on a.prodlot_id = lot.id 
                           where round(a.qty)>0 and a.location_id in %s and a.product_id =%s order by lot.sort 
                           """,(tuple(locations_ids),product_id))
            locations_ids = cr.fetchall()
        
        for id in [i for (i,) in locations_ids]:
            if lock:
                try:
                    cr.execute("SAVEPOINT stock_location_product_reserve")
                    cr.execute("""SELECT id FROM stock_move
                                  WHERE product_id=%s AND
                                          (
                                            (location_dest_id=%s AND
                                             location_id<>%s AND
                                             state='done')
                                            OR
                                            (location_id=%s AND
                                             location_dest_id<>%s AND
                                             state in ('done', 'assigned'))
                                          )
                                  FOR UPDATE of stock_move NOWAIT""", (product_id, id, id, id, id), log_exceptions=False)
                except Exception:
                    cr.execute("ROLLBACK TO stock_location_product_reserve")
                    _logger.warning("Failed attempt to reserve %s x product %s, likely due to another transaction already in progress. Next attempt is likely to work. Detailed error available at DEBUG level.", product_qty, product_id)
                    _logger.debug("Trace of the failed product reservation attempt: ", exc_info=True)
                    return False

            # XXX TODO: rewrite this with one single query, possibly even the quantity conversion
            cr.execute("""SELECT product_uom, sum(product_qty) AS product_qty
                          FROM stock_move
                          WHERE location_dest_id=%s AND
                                location_id<>%s AND
                                product_id=%s AND
                                state='done'
                          GROUP BY product_uom
                       """,
                       (id, id, product_id))
            results = cr.dictfetchall()
            cr.execute("""SELECT product_uom,-sum(product_qty) AS product_qty
                          FROM stock_move
                          WHERE location_id=%s AND
                                location_dest_id<>%s AND
                                product_id=%s AND
                                state in ('done', 'assigned')
                          GROUP BY product_uom
                       """,
                       (id, id, product_id))
            results += cr.dictfetchall()
            total = 0.0
            results2 = 0.0
            for r in results:
                amount = uom_obj._compute_qty(cr, uid, r['product_uom'], r['product_qty'], context.get('uom', False))
                results2 += amount
                total += amount
            if total <= 0.0:
                continue

            amount = results2
            compare_qty = float_compare(amount, 0, precision_rounding=uom_rounding)
            if compare_qty == 1:
                if amount > min(total, product_qty):
                    amount = min(product_qty, total)
                result.append((amount, id))
                product_qty -= amount
                total -= amount
                if product_qty <= 0.0:
                    return result
                if total <= 0.0:
                    continue
        result.append((product_qty,ids[0]))
        
        return result
