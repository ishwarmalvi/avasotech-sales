# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning


class MergeOpportunityQuote(models.TransientModel):
    _name = 'crm.merge.opportunity.quote'

    opportunity_id = fields.Many2one('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]")

    @api.multi
    def action_link_opportunity(self):
        self.ensure_one()
        order_ids = self.env['sale.order'].browse(self._context.get('active_ids'))
        allready_available = ''
        count = 0
        for order in order_ids:
            if order.opportunity_id:
                allready_available += order.name + ' '
            else:
                order.opportunity_id = self.opportunity_id.id
            count += 1
        if allready_available != '' and count == len(order_ids):
            warning_msg = ("Allready link opportunity with %s Quotation/Order") %(allready_available)
            return {
                'name': 'Allready link opportunity',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'custom.pop.message',
                'target':'new',
                'context':{'default_name': warning_msg}
            }

class CustomPopMessage(models.TransientModel):
    _name = "custom.pop.message"

    name = fields.Char('Message')