# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from lxml import etree
from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import time

class product_out_check_wizard(osv.osv_memory):
    
    _name = 'picking.out.check.wizard'
     
    _description = u'出库单检查操作'
    
    _columns = {
        'name':fields.char(u'扫描编号'), 
        'last_name':fields.char(u'出库单号'),
        'picking_id': fields.many2one('stock.picking', 'Reference'),
        'confirm':fields.boolean(u'确认'),
        'move_ids': fields.one2many('product.out.list.wizard', 'wizard_id', string='Users'),
     }
    
    
    _defaults = {
        'confirm':False,
    }
    
    def onchange_stock_out_code(self, cr, uid, ids, outcode,last_name, move_ids,context=None):
        v = {}
        stock_picking_obj = self.pool.get('stock.picking')
        list_wizard_obj = self.pool.get('product.out.list.wizard')
        if outcode:
            if outcode.startswith('OUT'):
                ids = stock_picking_obj.search(cr,uid,[('name','=',outcode)])
                
                orders = stock_picking_obj.browse(cr,uid,ids)
                if orders[0].state <>"done" :
                    stock_picking_obj.action_assign(cr,uid,ids)
                    
                move_ids =[]
                for line in orders[0].move_lines:
                    if line.state <>'cancel':
                        move_ids.append({'product_qty':line.product_qty,'product_code':line.product_id.default_code,'state':line.qc_scan,'gb_code':line.product_id.gb_code,'product_name':line.product_id.name_template,'move_id':line.id,'product_id':line.product_id.id})
                v['name'] =''
                v['last_name'] = outcode
                v['picking_id'] =orders[0].id
                v['move_ids'] = move_ids 
                v['confirm'] = self.check_state(move_ids)  
                main_id  = self.create(cr, uid, {'name':outcode,'last_name':outcode,'picking_id':orders[0].id}, context)
                for temp in move_ids:
                    temp.update({'wizard_id':main_id})
                    list_wizard_obj.create(cr,uid,temp)
            elif not outcode.startswith('OUT'):
                if last_name:
                    v['name'] =''
                    v['last_name'] =last_name
                    move_ids = resolve_o2m_operations(cr, uid, list_wizard_obj, move_ids,['product_name','product_code','state','gb_code'], context)
                    for temp in move_ids:
                        if temp['product_code'] == outcode or temp['gb_code'] == outcode:
                            temp.update({'state':True})
#                             break
                    v['move_ids'] = move_ids
                    v['confirm'] = self.check_state(move_ids)
            elif outcode.startswith('OUT') and last_name.startswith('OUT'):
                ids = stock_picking_obj.search(cr,uid,[('name','=',outcode)])
                orders = stock_picking_obj.browse(cr,uid,ids)
                if orders[0].state <>"done" :
                    stock_picking_obj.action_assign(cr,uid,ids)
                move_ids =[]
                for line in orders[0].move_lines:
                    if line.state <>'cancel':
                        move_ids.append({'product_qty':line.product_qty,'product_code':line.product_id.default_code,'state':line.qc_scan,'gb_code':line.product_id.gb_code,'product_name':line.product_id.name_template,'move_id':line.id,'product_id':line.product_id.id})
                v['name'] =''
                v['last_name'] = outcode
                v['picking_id'] =orders[0].id
                v['move_ids'] = move_ids 
                v['confirm'] = self.check_state(move_ids)  
                main_id  = self.create(cr, uid, {'name':outcode,'last_name':outcode,'picking_id':orders[0].id}, context)
                for temp in move_ids:
                    temp.update({'wizard_id':main_id})
                    list_wizard_obj.create(cr,uid,temp)
        return {'value': v}
    
    def check_state(self,move_lins):
        lines = [ line for line in move_lins if line['state'] == False ]
        return len(lines)==0 or False
    
    def do_check(self, cr, uid, ids, context=None):
        stock_move_obj = self.pool.get('stock.move')
        orders = self.browse(cr,uid,ids)
        for line in orders:
            ids = [ line.move_id.id for line in line.move_ids]
            stock_move_obj.write(cr,uid,ids,{'qc_scan':True})
        
        partial_data = {
            'delivery_date' : time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        }
        
        for move in orders[0].move_ids:
            move_id = move.move_id.id
            partial_data['move%s' % (move_id)] = {
                'product_id': move.product_id.id,
                'product_qty': move.product_qty,
                'product_uom': move.move_id.product_uom.id,
                'prodlot_id': move.move_id.prodlot_id.id,
            }
        
        self.pool.get('stock.move').do_partial(cr, uid, ids, partial_data, context=context)
            
        return  {
            'name': '出库检测',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'picking.out.check.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
        
    
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
                context = {}
        res = super(product_out_check_wizard, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        return res
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(product_out_check_wizard, self).default_get(cr, uid, fields, context=context)
        return res
     
def resolve_o2m_operations(cr, uid, target_osv, operations, fields, context):
    results = []
    for operation in operations:
        result = None
        if not isinstance(operation, (list, tuple)):
            result = target_osv.read(cr, uid, operation, fields, context=context)
        elif operation[0] == 0:
            # may be necessary to check if all the fields are here and get the default values?
            result = operation[2]
        elif operation[0] == 1:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
            if not result: result = {}
            result.update(operation[2])
        elif operation[0] == 4:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
        if result != None:
            results.append(result)
    return results    


class product_out_list(osv.osv_memory):
    _name='product.out.list.wizard'
    
    _description = u'出库单明细'  
    
    _columns = {
        'wizard_id': fields.many2one('picking.out.check.wizard', string='Wizard', ondelete='cascade',required=True), 
        'product_id':fields.many2one('product.product',u'产品'),
        'product_name':fields.char(u'产品名称'),
        'product_code':fields.char(u'产品编号'),
        'gb_code':fields.char(u'国标编码'),
        'product_qty':fields.float(u'数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'state':fields.boolean(u'状态'),
        'move_id':fields.many2one('stock.move', u'明细Id', readonly=True),
     } 
    
    _defaults = {
        'state':False,
    }
     