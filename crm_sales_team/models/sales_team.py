# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.base.res.res_partner import FormatAddress
from odoo.exceptions import UserError
import datetime
from dateutil.relativedelta import relativedelta


class CrmTeam(models.Model):
    _inherit = "crm.team"

    @api.model
    @api.returns('self', lambda value: value.id if value else False)
    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        team_id = None
        if 'default_team_id' in self.env.context:
            team_id = self.env['crm.team'].browse(self.env.context.get('default_team_id'))
        if not team_id or not team_id.exists():
            company_id = self.sudo(user_id).env.user.company_id.id
            team_id = self.env['crm.team'].sudo().search([
                '|', ('user_id', '=', user_id), ('member_ids', 'in', user_id),
                '|', ('company_id', '=', False), ('company_id', 'child_of', [company_id])
            ], limit=1)
        if not team_id:
            default_team_id = self.env.ref('sales_team.team_sales_department', raise_if_not_found=False)
            if default_team_id and (self.env.context.get('default_type') != 'lead' or default_team_id.use_leads):
                team_id = default_team_id
        return team_id

    member_ids = fields.Many2many('res.users', string='Team Members')


class Lead(FormatAddress, models.Model):
    _inherit = "crm.lead"

    lead_type = fields.Selection([('product', 'Product'), ('services', 'Services')], string="Sale Type", required=True)
    lead_type_note = fields.Html('T&C for Sale Type')
    number = fields.Char(string="Number")

    @api.onchange('lead_type', 'partner_id')
    def onchange_lead_type(self):
        self.lead_type_note = ''
        company_id = self.env.user.company_id
        if self.lead_type == 'product':
            if self.partner_id and self.partner_id.product_note:
                self.lead_type_note = self.partner_id.product_note
            else:
                self.lead_type_note = company_id.product_note
        elif self.lead_type == 'services':
            if self.partner_id and self.partner_id.services_note:
                self.lead_type_note = self.partner_id.services_note
            else:
                self.lead_type_note = company_id.services_note

class SaleOrder(models.Model):
    _inherit = "sale.order"

    lead_type = fields.Selection([('product', 'Product'), ('services', 'Services')], string="Sale Type")
    lead_type_note = fields.Html('T&C for Sale Type')
    number = fields.Char(string="Number")

    @api.onchange('lead_type', 'partner_id')
    def onchange_lead_type(self):
        self.lead_type_note = ''
        company_id = self.env.user.company_id
        if self.lead_type == 'product':
            if self.partner_id and self.partner_id.product_note:
                self.lead_type_note = self.partner_id.product_note
            else:
                self.lead_type_note = company_id.product_note
        elif self.lead_type == 'services':
            if self.partner_id and self.partner_id.services_note:
                self.lead_type_note = self.partner_id.services_note
            else:
                self.lead_type_note = company_id.services_note

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('crm.sale.order') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('crm.sale.order') or _('New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
        result = super(SaleOrder, self).create(vals)
        return result

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
        # result = super(SaleOrder, self).create(vals) ## Super Method Close for Sale Sequence Code Change 
        return result

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.name = self.env['ir.sequence'].with_context().next_by_code('sale.order') or _('New')
        return res

    def _prepare_contract_data(self, payment_token_id=False):
        if self.template_id and self.template_id.contract_template:
            contract_tmp = self.template_id.contract_template
        else:
            contract_tmp = self.contract_template
        values = {
            'name': contract_tmp.name,
            'state': 'open',
            'template_id': contract_tmp.id,
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id,
            'date_start': fields.Date.today(),
            'description': self.note,
            'payment_token_id': payment_token_id,
            'pricelist_id': self.pricelist_id.id,
            'recurring_rule_type': contract_tmp.recurring_rule_type,
            'recurring_interval': contract_tmp.recurring_interval,
            'company_id': self.company_id.id,
        }
        # if there already is an AA, use it in the subscription's inherits
        if self.project_id:
            values.pop('name')
            values.pop('partner_id')
            values.pop('company_id')
            values['analytic_account_id'] = self.project_id.id
        # compute the next date
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
        recurring_next_date = today + invoicing_period
        values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)
        if 'template_asset_category_id' in contract_tmp._fields:
            values['asset_category_id'] = contract_tmp.with_context(force_company=self.company_id.id).template_asset_category_id.id
        return values

class ResCompany(models.Model):
    _inherit = "res.company"

    product_note = fields.Html('T&C for Sale Type Product')
    services_note = fields.Html('T&C for Sale Type Services')

class ResPartner(models.Model):
    _inherit = 'res.partner'

    product_note = fields.Html('T&C for Customer Product')
    services_note = fields.Html('T&C for Customer Services')

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        res = super(ResPartner, self).onchange_parent_id()
        if self.parent_id:
            self.product_note = self.parent_id.product_note
            self.services_note = self.parent_id.services_note
        return res
