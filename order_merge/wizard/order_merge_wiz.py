# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import copy


class OrderMerge(models.TransientModel):
    _name = 'order.merge'
    _description = 'Merge Sale orders'


    @api.model
    def default_get(self, fields):
        rec = super(OrderMerge, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        
        if active_ids:
            sale_ids = []
            sales = self.env['sale.order'].browse(active_ids)

            if any(sale.state == 'done' for sale in sales):
                raise Warning ('You can not merge done orders.')
                    
            sale_ids = [sale.id for sale in sales if sale.state in ('draft')]
            if 'order_to_merge' in fields:
                rec.update({'order_to_merge': sale_ids})
        return rec

    order_to_merge = fields.Many2many(
        'sale.order', 'rel_sale_to_merge', 'sale_id', 'to_merge_id',
        'Orders to merge' ,domain=[('state', '!=', 'done')])
    type = fields.Selection([('new','New Order and Cancel Selected'),('exist','New order and Delete all selected order'),('exist_1','Merge order on existing selected order and cancel others'),('exist_2','Merge order on existing selected order and delete others')],'Merge Type',default='new', required=True)
    order = fields.Many2one('sale.order', string='Merge with')
    
    
    @api.multi
    def merge(self):
        sale_obj = self.env['sale.order']
        mod_obj = self.env['ir.model.data']
        line_obj = self.env['sale.order.line']
        action = mod_obj.xmlid_to_object('stock.stock_picking_action_picking_type')
        form_view_id = mod_obj.xmlid_to_res_id('sale.view_order_form')
        sales = sale_obj.browse(self._context.get('active_ids', []))
        partners_list = []
        partners_list_write = []
        line_list= []
        cancel_list = []
        copy_list = []
        vals={}
        customer_ref = []
        partner_name= False
        myString = ''
        
        if len(sales) < 2:
            raise Warning ('Please select multiple orders to merge in the list view.')
                    
        if any(sale.state in ['done','sale','confirmed','cancel'] for sale in sales):
            raise Warning ('You can not merge Done and Sale order orders.')
        for sale in sales:
            if sale.client_order_ref:
                customer_ref.append(sale.client_order_ref)
                if len(customer_ref) > 1:
                    myString = ",".join(customer_ref)
                else:
                    myString = customer_ref[0]
        if self.order:
            self.order.write({'client_order_ref':myString})
        if self.type == 'new':
            partner_name = sales and sales[0].partner_id.id
            new_sale = sale_obj.create({'partner_id':partner_name,'client_order_ref':myString})
            for sale in sales:
                partners_list.append(sale.partner_id)
                if not partners_list[1:] == partners_list[:-1]:
                    raise Warning ('You can only merge orders of same partners.')
                    
                else:
                    cancel_list.append(sale)
                    merge_ids = line_obj.search([('order_id', '=', sale.id)])
                    for line in merge_ids:
                        vals = {
                                'product_id':line.product_id.id or False,
                                'product_uom_qty':line.product_uom_qty or False,
                                'price_unit':line.price_unit or False,
                                'tax_id': [(6, 0, [tax.id for tax in line.tax_id if line.tax_id])] or False,
                                'order_id':new_sale.id,
                                }
                        line_obj.create(vals)   
            for orders in cancel_list:
                    orders.action_cancel()
        if self.type == 'exist':
            partner_name = sales and sales[0].partner_id.id
            new_sale = sale_obj.create({'partner_id':partner_name,'client_order_ref':myString})
            for sale in sales:
                partners_list_write.append(sale.partner_id)
                
                if not partners_list_write[1:] == partners_list_write[:-1]:
                    raise Warning ('You can only merge orders of same partners.')
                    
                else:
                    cancel_list.append(sale)
                    merge_ids = line_obj.search([('order_id', '=', sale.id)])
                    for line in merge_ids:
                        vals = {
                                'product_id':line.product_id.id or False,
                                'product_uom_qty':line.product_uom_qty or False,
                                'price_unit':line.price_unit or False,
                                'tax_id':  [(6, 0, [tax.id for tax in line.tax_id if line.tax_id])] or False,
                                'order_id':new_sale.id,
                                }
                        line_obj.create(vals)
            for orders in cancel_list:
                orders.action_cancel()
                orders.unlink()
        if self.type == 'exist_1':
            for sale in sales:
                partners_list_write.append(sale.partner_id)
                new_sale = self.order
                
                if not partners_list_write[1:] == partners_list_write[:-1]:
                    raise Warning ('You can only merge orders of same partners.')
                    
                else:
                    partner_name = sale.partner_id.id
                    cancel_list.append(sale.id)
                    merge_ids = line_obj.search([('order_id', '=', sale.id)])
                    for line in merge_ids:
                        line.write({'order_id':self.order.id})
                    
            if self.order.id in cancel_list:
                cancel_list.remove(self.order.id)
            for orders in cancel_list:
                for s_order in self.env['sale.order'].browse(orders):
                    s_order.action_cancel()
            return True
        if self.type == 'exist_2':
            for sale in sales:
                partners_list_write.append(sale.partner_id)
                new_sale = self.order
                
                if not partners_list_write[1:] == partners_list_write[:-1]:
                    raise Warning ('You can only merge orders of same partners.')
                    
                else:
                    partner_name = sale.partner_id.id
                    cancel_list.append(sale.id)
                    merge_ids = line_obj.search([('order_id', '=', sale.id)])
                    for line in merge_ids:
                        if self.order.state in ['done','sale','confirmed','cancel']:
                            raise Warning ('You can not merge oredrs with Done, Cancel and Sale order orders.')
                        else:
                            line.write({'order_id':self.order.id})
                    
            if self.order.id in cancel_list:
                cancel_list.remove(self.order.id)
            for orders in cancel_list:
                for s_order in self.env['sale.order'].browse(orders):
                    s_order.action_cancel()
                    s_order.unlink()
        result =  {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': new_sale.id,
            'views': [(False, 'form')],
        }
        return result
                    

class PurchaseOrderMerge(models.TransientModel):
    _name = 'purchase.order.merge'
    _description = 'Merge Purchase orders'
    
    @api.model
    def default_get(self, fields):
        rec = super(PurchaseOrderMerge, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        
        if active_ids:
            purchase_ids = []
            purchases = self.env['purchase.order'].browse(active_ids)
            
            if any(pur.state == 'done' for pur in purchases):
                raise Warning ('You can not merge done orders.')
                    
            purchase_ids = [pur.id for pur in purchases if pur.state in ('draft')]
                 
            if 'purchase_order_to_merge' in fields:
                rec.update({'purchase_order_to_merge': purchase_ids})
        return rec
    
    purchase_order = fields.Many2one(
        'purchase.order', 'Merge into')
    purchase_order_to_merge = fields.Many2many(
        'purchase.order', 'rel_purchase_to_merge', 'purchase_id', 'to_merge_id',
        'Orders to merge',domain=[('state', '!=', 'done')])
    type = fields.Selection([('new','New Order and Cancel Selected'),('exist','New order and Delete all selected order'),('exist_1','Merge order on existing selected order and cancel others'),('exist_2','Merge order on existing selected order and delete others')],'Merge Type',default='new', required=True)
    
    @api.multi
    def merge_purchase(self):
        purchase_obj = self.env['purchase.order']
        mod_obj = self.env['ir.model.data']
        line_obj = self.env['purchase.order.line']
        form_view_id = mod_obj.xmlid_to_res_id('purchase.purchase_order_form')
        purchases = purchase_obj.browse(self._context.get('active_ids', []))
        partners_list = []
        partners_list_write = []
        line_list= []
        cancel_list = []
        copy_list = []
        vendor_ref = []
        myString = ''
        source_docs = []
        
        if len(purchases) < 2:
            raise Warning ('Please select multiple orders to merge in the list view.')
                    
        if any(pur.state in ['done','purchase','cancel'] for pur in purchases):
            raise Warning ('You can not merge this order with existing state.')
        for pur in purchases:
            if pur.partner_ref:
                vendor_ref.append(pur.partner_ref)
                if len(vendor_ref) > 1:
                    myString = ",".join(vendor_ref)
                else:
                    myString = vendor_ref[0]
        if self.purchase_order:
            self.purchase_order.write({'partner_ref':myString})
        if self.type == 'new':
            partner_name = purchases and purchases[0].partner_id.id
            new_purchase = purchase_obj.create({'partner_id':partner_name,'partner_ref':myString})
            for pur in purchases:
                partners_list.append(pur.partner_id)
                # get origin source docs and append to list
                purchase = self.env['purchase.order'].search([('id', '=', pur.id)])
                source_docs.append(str(purchase.origin))

                if not partners_list[1:] == partners_list[:-1]:
                    raise Warning ('You can only merge orders of same partners.')
                    
                else:
                    cancel_list.append(pur)
                    merge_ids = line_obj.search([('order_id', '=', pur.id)])
                    for line in merge_ids:
                        vals = {
                                'date_planned':line.date_planned or False,
                                'name':line.product_id.name or False,
                                'product_id':line.product_id.id or False,
                                'product_qty':line.product_qty or False,
                                'product_uom':line.product_uom.id or False,
                                'price_unit':line.price_unit or False,
                                'taxes_id': [(6, 0, [tax.id for tax in line.taxes_id if line.taxes_id])] or False,
                                'order_id':new_purchase.id,
                                }
                        line_obj.create(vals)
                    
            for orders in cancel_list:
                    orders.button_cancel()
            new_purchase.origin = '; '.join(map(str, source_docs))

        if self.type == 'exist':
            partner_name = purchases and purchases[0].partner_id.id
            new_purchase = purchase_obj.create({'partner_id':partner_name,'partner_ref':myString})
            for pur in purchases:
                partners_list_write.append(pur.partner_id)
                
                if not partners_list_write[1:] == partners_list_write[:-1]:
                    raise Warning ('You can only merge orders of same partners.')
                    
                else:
                    partner_name = pur.partner_id.id
                    cancel_list.append(pur)
                    merge_ids = line_obj.search([('order_id', '=', pur.id)])
                    for line in merge_ids:
                        vals = {
                            'date_planned':line.date_planned or False,
                                'name':line.product_id.name or False,
                                'product_id':line.product_id.id or False,
                                'product_qty':line.product_qty or False,
                                'product_uom':line.product_uom.id or False,
                                'price_unit':line.price_unit or False,
                                'taxes_id': [(6, 0, [tax.id for tax in line.taxes_id if line.taxes_id])] or False,
                                'order_id':new_purchase.id,
                                }
                        line_obj.create(vals)
                    
            for orders in cancel_list:
                orders.button_cancel()
                orders.unlink()
        if self.type == 'exist_1':
            for pur in purchases:
                partners_list_write.append(pur.partner_id)
                new_purchase = self.purchase_order
                
                if not partners_list_write[1:] == partners_list_write[:-1]:
                    raise Warning ('You can only merge orders of same partners.')
                    
                else:
                    partner_name = pur.partner_id.id
                    cancel_list.append(pur.id)
                    merge_ids = line_obj.search([('order_id', '=', pur.id)])
                    for line in merge_ids:
                        line.write({'order_id':self.purchase_order.id})
            if self.purchase_order.id in cancel_list:
                cancel_list.remove(self.purchase_order.id)
            for orders in cancel_list:
                for s_order in self.env['purchase.order'].browse(orders):
                    s_order.button_cancel()
        if self.type == 'exist_2':
            for pur in purchases:
                partners_list_write.append(pur.partner_id)
                new_purchase = self.purchase_order
                
                if not partners_list_write[1:] == partners_list_write[:-1]:
                    raise Warning ('You can only merge orders of same partners.')
                    
                else:
                    partner_name = pur.partner_id.id
                    cancel_list.append(pur.id)
                    merge_ids = line_obj.search([('order_id', '=', pur.id)])
                    for line in merge_ids:
                        line.write({'order_id':self.purchase_order.id})
            if self.purchase_order.id in cancel_list:
                cancel_list.remove(self.purchase_order.id)
            for orders in cancel_list:
                for p_order in self.env['purchase.order'].browse(orders):
                    p_order.button_cancel()
                    p_order.unlink()
        result =  {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': new_purchase.id,
            'views': [(False, 'form')],
        }
        return result

