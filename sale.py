# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp.osv import fields

class sale_order(osv.osv):
    "Sale"
    _inherit = 'sale.order'
    
    _columns = {
         'delivery_time':fields.char(u'配送时间'),
    }
    
    
    def _prepare_order_picking(self, cr, uid, order, context=None):
        result = super(sale_order, self)._prepare_order_picking(cr, uid, order, context=context)
        result.update(delivery_time=order.delivery_time)
        return result 