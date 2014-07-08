# -*- coding: utf-8 -*-
import time
from openerp.tools.float_utils import float_round

from openerp.report import report_sxw

class order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_sale_order':self.get_sale_order, 
        })
        
        
    def get_sale_order(self,out_items):
        cr = self.cr
        uid = self.uid
        order_list = [{'sequence':self.pool.get('ir.sequence').get(cr,uid, 'stock.out.pdf'),'picking':line} for line in out_items]
        return order_list
    

report_sxw.report_sxw('report.stock.out_order.report', 'stock.picking', 'addons/gavin_odoo_extend/report/out_bill_order.rml', parser=order, header="external")
