# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields


class product_product(osv.osv):
    
    _inherit = 'product.product'
    
    _columns ={
        'gb_code': fields.char(u'厂家编码', size=50,),
        'standard': fields.char(u'规格', size=50,),
    }
