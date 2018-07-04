# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Merge Sales And Purchase Order Odoo/OpenERP',
    'version': '10.0.0.1',
    'category': 'Sales',
    'summary': 'This module helps to merge sales and purchase orders with different options',
    'description': """
    Merge sales order, merge purchase orders, merge order, merge data,
    Sales Order Merge,
    Purchase Order Merge, Merge Sale Order, Merge purchases Order
""",
    'author': 'BrowseInfo',
    "price": 49,
    "currency": 'EUR',
    'website': 'http://www.browseinfo.in',
    'images': [],
    'depends': ['base','sale', 'purchase','product'],
    'data': [
        'views/order_merge_view.xml',
        'views/sale_order.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "images":["static/description/Banner.png"],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
