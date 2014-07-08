# -*- coding: utf-8 -*-
{
    'name': 'gavin_odoo_extend',
    'version': '0.1',
    'category': 'gavin',
    'description': """odoo业务扩展模块""",
    'author': 'gavin',
    'sequence': 5,
    'website': 'http://freshfresh.com',
    'depends': ['base','stock','product','purchase','account','product_expiry'],
    'js': [
       ],
    'data': [
         'wizard/stock_check_out_product_view.xml',
         'product_view.xml',
         'stock_cron.xml',
         'stock_pdf_sequence.xml',
         'purchase_view.xml',
         'stock_view.xml',
    ],
    'installable': True,
}