# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp import netsvc
from openerp.osv import fields

class stock_move (osv.osv):
    _inherit = 'stock.move'
    
    _columns = {
         'qc_scan':fields.boolean(u'出库扫描'),
    } 
    
    _order = 'id'

    _defaults={'qc_scan':False}


    def check_assign(self, cr, uid, ids, context=None):
        """ Checks the product type and accordingly writes the state.
        @return: No. of moves done
        """
        done = []
        production_move =[]
        count = 0
        pickings = {}
        if context is None:
            context = {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.product_id.type == 'consu' or move.location_id.usage == 'supplier':
                if move.state in ('confirmed', 'waiting'):
                    done.append(move.id)
                pickings[move.picking_id.id] = 1
                continue
            if move.state in ('confirmed', 'waiting'):
                # Important: we must pass lock=True to _product_reserve() to avoid race conditions and double reservations
                res = self.pool.get('stock.location')._product_reserve(cr, uid, [move.location_id.id], move.product_id.id, move.product_qty, {'uom': move.product_uom.id}, lock=True)
                if res:
                    #_product_available_test depends on the next status for correct functioning
                    #the test does not work correctly if the same product occurs multiple times
                    #in the same order. This is e.g. the case when using the button 'split in two' of
                    #the stock outgoing form
                    r = res.pop(0)
                    self.write(cr, uid, [move.id], {'state':'assigned'})
                    done.append(move.id)
                    pickings[move.picking_id.id] = 1
                    prodlots_id = self._get_prodlots_id(cr,uid,move,r)
                    product_uos_qty = self.pool.get('stock.move').onchange_quantity(cr, uid, ids, move.product_id.id, r[0], move.product_id.uom_id.id, move.product_id.uos_id.id)['value']['product_uos_qty']
                    cr.execute('update stock_move set location_id=%s, product_qty=%s, product_uos_qty=%s ,prodlot_id =%s  where id=%s', (r[1], r[0],product_uos_qty,prodlots_id, move.id))
                    while res:
                        r = res.pop(0)
                        prodlots_id = self._get_prodlots_id(cr,uid,move,r)
                        if move.move_dest_id:
                            move_dest_id = self.copy(cr,uid,move.move_dest_id.id,{'product_uos_qty': product_uos_qty,'state':'assigned','product_qty': r[0],'prodlot_id':prodlots_id,'location_id':move.location_dest_id.id})
                            state = 'assigned'
                            move_id = self.copy(cr, uid, move_dest_id, {'move_dest_id': move_dest_id,'picking_id':move.picking_id.id,'state':state,'location_id': r[1],'location_dest_id':move.location_dest_id.id})
                            if state =='assigned':
                                done.append(move_id)
                            production_move.append(move_dest_id)
                        else:
                            state = 'assigned'
                            move_id = self.copy(cr, uid, move.id, {'product_uos_qty': product_uos_qty,'state':state,'prodlot_id':prodlots_id, 'product_qty': r[0], 'location_id': r[1]})
                            if state =='assigned':
                                done.append(move_id)
        if done:
            count += len(done)
            self.write(cr, uid, done, {'state': 'assigned'})
        
            if production_move:
                #添加生产单的投料批次，工作类似是拆分批次，根据库存中实际的先入先出的情况
                self.add_production_new_move(cr, uid, move, production_move)
            
        
        if count:
            for pick_id in pickings:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_write(uid, 'stock.picking', pick_id, cr)
        return count
    
    def add_production_new_move(self,cr,uid,move,new_moves):
            production_obj = self.pool.get('mrp.production')
            if move.move_dest_id:
                production_ids = production_obj.search(cr, uid, [('move_lines', 'in', [move.move_dest_id.id])])
                for new_move in new_moves:
                    production_obj.write(cr, uid, production_ids, {'move_lines': [(4, new_move)]})
    
    
    #根据商品和库位指定批次号
    def _get_prodlots_id(self,cr,uid,move,resu,isupdate=True):
        if move.move_dest_id and move.move_dest_id.prodlot_id:
            return  move.move_dest_id.prodlot_id.id
        location_id = resu[1]
        cr.execute(""" select a.prodlot_id  from stock_report_prodlots as a 
               left join stock_production_lot as lot on a.prodlot_id = lot.id 
               where round(a.qty)>0 and a.location_id = %s and a.product_id =%s  order by lot.sort 
               """,(location_id,move.product_id.id))
        res = cr.fetchone()
        prodlot_id = (res and res[0] and float(res[0])) or None
        if move.move_dest_id and not move.move_dest_id.prodlot_id and isupdate:
            self.write(cr, uid, move.move_dest_id.id, {'prodlot_id':prodlot_id,'product_qty':resu[0]}, {})
        return prodlot_id
    

class Stock_Picking_Out(osv.osv):
    _inherit  ='stock.picking.out'
    
    _columns = {
        'delivery_time':fields.char(u'配送时间'),
    }
    
    def action_assign(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            if pick.state == 'draft':
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_confirm', cr)
            move_ids = [x.id for x in pick.move_lines if x.state in ('confirmed','waiting')]
            if move_ids:
#                 raise osv.except_osv(_('Warning!'),_('Not enough stock, unable to reserve the products.'))
                self.pool.get('stock.move').action_assign(cr, uid, move_ids)
        return True
    
class StockPicking(osv.osv):
    _name = 'stock.picking'
    _inherit = 'stock.picking'  
    
    _columns = {
        'delivery_time':fields.char(u'配送时间'),
    }
    
    def action_assign(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            if pick.state == 'draft':
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_confirm', cr)
            move_ids = [x.id for x in pick.move_lines if x.state in ('confirmed','waiting')]
            if move_ids:
#                 raise osv.except_osv(_('Warning!'),_('Not enough stock, unable to reserve the products.'))
                self.pool.get('stock.move').action_assign(cr, uid, move_ids)
        return True
    
    def clear_sequence_pdf(self,cr,uid):
        sequence_obj = self.pool.get('ir.sequence')
        ids = sequence_obj.search(cr,uid,[('code','=','stock.out.pdf')])
        if ids:
            sequence_obj.write(cr,uid,ids,{'number_next':2})
            sequence_obj.write(cr,uid,ids,{'number_next_actual':1})
           
        
   
    