# -*- coding: utf-8 -*-
# from odoo import http


# class JhSalesSubscription(http.Controller):
#     @http.route('/jh_sales_subscription/jh_sales_subscription', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/jh_sales_subscription/jh_sales_subscription/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('jh_sales_subscription.listing', {
#             'root': '/jh_sales_subscription/jh_sales_subscription',
#             'objects': http.request.env['jh_sales_subscription.jh_sales_subscription'].search([]),
#         })

#     @http.route('/jh_sales_subscription/jh_sales_subscription/objects/<model("jh_sales_subscription.jh_sales_subscription"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('jh_sales_subscription.object', {
#             'object': obj
#         })

