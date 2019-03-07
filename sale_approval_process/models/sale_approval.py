# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MarginRole(models.Model):
    _name = "margin.role"

    name = fields.Char()


class SaleMarginLevel(models.Model):
    _name = "sale.margin.level"

    name = fields.Many2one('margin.role', string="Margin Level", required=True)
    min_margin = fields.Integer(string="Min Margin (%)", required=True)
    max_margin = fields.Integer(string="Max Margin (%)", required=True)


class Users(models.Model):
    _inherit = "res.users"

    margin_level = fields.Many2one('sale.margin.level', string="Sale Margin Level")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    @api.depends('margin', 'amount_untaxed')
    def _margin_role_check(self):
        for record in self:
            user_id = record.env.user
            margin_level = self.env['sale.margin.level'].search([('name', '=', user_id.margin_level.id)])
            if record.margin > 0:
                margin = ((record.margin * 100) / record.amount_untaxed)
                record.margin_percent = margin
                if margin and margin >= margin_level.min_margin and margin <= margin_level.max_margin:
                    record.is_approval = True

    margin_percent = fields.Float(compute='_margin_role_check', string="Margin (%)")
    is_approval = fields.Boolean(string='Is Approval')
    is_approved = fields.Boolean(string='Is Approved')

    @api.multi
    def action_approval(self):
        for order in self:
            order.is_approved = True
            order.is_approval = False

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            order.is_approved = False
        return res