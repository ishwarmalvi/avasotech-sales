# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016-Today Geminate Consultancy Services (<http://geminatecs.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from babel.dates import format_date
from odoo.release import version
import json

class CrmTeam(models.Model):
    _inherit = "crm.team"

    quotations_count = fields.Integer(
        compute='_compute_quotations_to_invoice',
        string='Number of quotations to invoice', readonly=True)
    quotations_amount = fields.Integer(
        compute='_compute_quotations_to_invoice',
        string='Amount of quotations to invoice', readonly=True)
    dashboard_graph_data = fields.Text(compute='_compute_dashboard_graph')
    dashboard_graph_group = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('user', 'Salesperson'),
    ], string='Group by', default='day', help="How this channel's dashboard graph will group the results.")
    dashboard_graph_period = fields.Selection([
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('year', 'This Year'),
    ], string='Period', default='month', help="The time period this channel's dashboard graph will consider.")
    dashboard_graph_model = fields.Selection([('sales', 'Sales'),('invoices', 'Invoices'),
        ('pipeline', 'Pipeline')], string="Content", help='The graph this channel will display in the Dashboard.\n')
    opportunities_count = fields.Integer(
        compute='_compute_opportunities',
        string='Number of open opportunities', readonly=True)
    opportunities_amount = fields.Integer(
        compute='_compute_opportunities',
        string='Amount of quotations to invoice', readonly=True)
    sales_to_invoice_count = fields.Integer(
        compute='_compute_sales_to_invoice',
        string='Number of sales to invoice', readonly=True)
    dashboard_graph_type = fields.Selection([
        ('line', 'Line'),
        ('bar', 'Bar'),
    ], string='Type', compute='_compute_dashboard_graph', help='The type of graph this channel will display in the dashboard.')
    unassigned_leads_count = fields.Integer(
        compute='_compute_unassigned_leads_count',
        string='Unassigned Leads', readonly=True)
    dashboard_button_name = fields.Char(string="Dashboard Button", compute='_compute_dashboard_button_name')
    team_type = fields.Selection([('sales', 'Sales'), ('website', 'Website'), ('pos', 'Point of Sale')], string='Channel Type',
        default='sales', required=True, help="The type of this channel, it will define the resources this channel uses.")

    def _compute_quotations_to_invoice(self):
        non_website_teams = self.filtered(lambda team: team.team_type != 'website')
        if non_website_teams:
            quotation_data = self.env['sale.report'].read_group([
                ('team_id', 'in', non_website_teams.ids),
                ('state', 'in', ['draft', 'sent']),
            ], ['price_total', 'team_id', 'name'], ['team_id', 'name'], lazy=False)
            for datum in quotation_data:
                self.browse(datum['team_id'][0]).quotations_amount += datum['price_total']
                self.browse(datum['team_id'][0]).quotations_count += 1

    @api.depends('dashboard_graph_group', 'dashboard_graph_model', 'dashboard_graph_period')
    def _compute_dashboard_graph(self):
        for team in self.filtered('dashboard_graph_model'):
            if team.dashboard_graph_group in (False, 'user') or team.dashboard_graph_period == 'week' and team.dashboard_graph_group != 'day' \
                    or team.dashboard_graph_period == 'month' and team.dashboard_graph_group != 'day':
                team.dashboard_graph_type = 'bar'
            else:
                team.dashboard_graph_type = 'line'
            team.dashboard_graph_data = json.dumps(team._get_graph())

    def _compute_opportunities(self):
        opportunity_data = self.env['crm.lead'].read_group([
            ('team_id', 'in', self.ids),
            ('probability', '<', 100),
            ('type', '=', 'opportunity'),
        ], ['planned_revenue', 'probability', 'team_id'], ['team_id'])
        counts = {datum['team_id'][0]: datum['team_id_count'] for datum in opportunity_data}
        amounts = {datum['team_id'][0]: (datum['planned_revenue'] * datum['probability'] / 100) for datum in opportunity_data}
        for team in self:
            team.opportunities_count = counts.get(team.id, 0)
            team.opportunities_amount = amounts.get(team.id, 0)

    @api.multi
    def _compute_sales_to_invoice(self):
        sale_order_data = self.env['sale.order'].read_group([
            ('team_id', 'in', self.ids),
            ('order_line.qty_to_invoice', '>', 0),
        ], ['team_id'], ['team_id'])
        for datum in sale_order_data:
            self.browse(datum['team_id'][0]).invoiced = datum['team_id_count']

    def _compute_unassigned_leads_count(self):
        leads_data = self.env['crm.lead'].read_group([
            ('team_id', 'in', self.ids),
            ('type', '=', 'lead'),
            ('user_id', '=', False),
        ], ['team_id'], ['team_id'])
        counts = {datum['team_id'][0]: datum['team_id_count'] for datum in leads_data}
        for team in self:
            team.unassigned_leads_count = counts.get(team.id, 0)

    def _compute_dashboard_button_name(self):
        """ Sets the adequate dashboard button name depending on the sales channel's options
        """
        for team in self:
            team.dashboard_button_name = _("Big Pretty Button :)") # placeholder

    def _get_graph(self):
        def get_week_name(start_date, locale):
            """ Generates a week name (string) from a datetime according to the locale:
                E.g.: locale    start_date (datetime)      return string
                      "en_US"      November 16th           "16-22 Nov"
                      "en_US"      December 28th           "28 Dec-3 Jan"
            """
            if (start_date + relativedelta(days=6)).month == start_date.month:
                short_name_from = format_date(start_date, 'd', locale=locale)
            else:
                short_name_from = format_date(start_date, 'd MMM', locale=locale)
            short_name_to = format_date(start_date + relativedelta(days=6), 'd MMM', locale=locale)
            return short_name_from + '-' + short_name_to

        self.ensure_one()
        values = []
        today = fields.Date.from_string(fields.Date.context_today(self))
        start_date, end_date = self._graph_get_dates(today)
        graph_data = self._graph_data(start_date, end_date)

        # line graphs and bar graphs require different labels
        if self.dashboard_graph_type == 'line':
            x_field = 'x'
            y_field = 'y'
        else:
            x_field = 'label'
            y_field = 'value'

        # generate all required x_fields and update the y_values where we have data for them
        locale = self._context.get('lang', 'en_US')
        if self.dashboard_graph_group == 'day':
            for day in range(0, (end_date - start_date).days + 1):
                short_name = format_date(start_date + relativedelta(days=day), 'd MMM', locale=locale)
                values.append({x_field: short_name, y_field: 0})
            for data_item in graph_data:
                index = (datetime.strptime(data_item.get('x_value'), DF).date() - start_date).days
                values[index][y_field] = data_item.get('y_value')

        elif self.dashboard_graph_group == 'week':
            weeks_in_start_year = int(date(start_date.year, 12, 28).isocalendar()[1]) # This date is always in the last week of ISO years
            for week in range(0, (end_date.isocalendar()[1] - start_date.isocalendar()[1]) % weeks_in_start_year + 1):
                short_name = get_week_name(start_date + relativedelta(days=7 * week), locale)
                values.append({x_field: short_name, y_field: 0})

            for data_item in graph_data:
                index = int((data_item.get('x_value') - start_date.isocalendar()[1]) % weeks_in_start_year)
                values[index][y_field] = int(data_item.get('y_value'))

        elif self.dashboard_graph_group == 'month':
            for month in range(0, (end_date.month - start_date.month) % 12 + 1):
                short_name = format_date(start_date + relativedelta(months=month), 'MMM', locale=locale)
                values.append({x_field: short_name, y_field: 0})

            for data_item in graph_data:
                index = int((data_item.get('x_value') - start_date.month) % 12)
                values[index][y_field] = data_item.get('y_value')

        elif self.dashboard_graph_group == 'user':
            for data_item in graph_data:
                values.append({x_field: self.env['res.users'].browse(data_item.get('x_value')).name, y_field: data_item.get('y_value')})

        else:
            for data_item in graph_data:
                values.append({x_field: data_item.get('x_value'), y_field: data_item.get('y_value')})

        [graph_title, graph_key] = self._graph_title_and_key()
        color = '#875A7B' if '+e' in version else '#7c7bad'
        return [{'values': values, 'area': True, 'title': graph_title, 'key': graph_key, 'color': color}]

    # Note: crm/models/crm_team.py another inherit method
    def _graph_get_dates(self, today):
        """ return a coherent start and end date for the dashboard graph according to the graph settings.
        """
        if self.dashboard_graph_period == 'week':
            start_date = today - relativedelta(weeks=1)
        elif self.dashboard_graph_period == 'year':
            start_date = today - relativedelta(years=1)
        else:
            start_date = today - relativedelta(months=1)

        # we take the start of the following month/week/day if we group by month/week/day
        # (to avoid having twice the same month/week/day from different years/month/week)
        if self.dashboard_graph_group == 'month':
            start_date = date(start_date.year + start_date.month / 12, start_date.month % 12 + 1, 1)
            # handle period=week, grouping=month for silly managers
            if self.dashboard_graph_period == 'week':
                start_date = today.replace(day=1)
        elif self.dashboard_graph_group == 'week':
            start_date += relativedelta(days=8 - start_date.isocalendar()[2])
            # add a week to make sure no overlapping is possible in case of year period (will display max 52 weeks, avoid case of 53 weeks in a year)
            if self.dashboard_graph_period == 'year':
                start_date += relativedelta(weeks=1)
        else:
            start_date += relativedelta(days=1)

        return [start_date, today]

    def _graph_date_column(self):
        if self.dashboard_graph_model in ['sales', 'invoices']:
            return 'date'
        elif self.dashboard_graph_model == 'pipeline':
            return 'date_deadline'
        return super(CrmTeam, self)._graph_date_column()

    def _graph_x_query(self):
        if self.dashboard_graph_group == 'user':
            return 'user_id'
        elif self.dashboard_graph_group == 'week':
            return 'EXTRACT(WEEK FROM %s)' % self._graph_date_column()
        elif self.dashboard_graph_group == 'month':
            return 'EXTRACT(MONTH FROM %s)' % self._graph_date_column()
        else:
            return 'DATE(%s)' % self._graph_date_column()

    def _graph_y_query(self):
        if self.dashboard_graph_model == 'sales':
            return 'SUM(price_subtotal)'
        elif self.dashboard_graph_model == 'invoices':
            return 'SUM(price_total)'
        elif self.dashboard_graph_model == 'pipeline':
            return 'date_deadline'
        return super(CrmTeam, self)._graph_y_query()

    def _graph_sql_table(self):
        if self.dashboard_graph_model == 'sales':
            return 'sale_report'
        elif self.dashboard_graph_model == 'invoices':
            return 'account_invoice_report'
        elif self.dashboard_graph_model == 'pipeline':
            return 'crm_opportunity_report'
        return super(CrmTeam, self)._graph_sql_table()

    def _extra_sql_conditions(self):
        if self.dashboard_graph_model == 'sales':
            return "AND state in ('sale', 'done')"
        elif self.dashboard_graph_model == 'invoices':
            return "AND state in ('open', 'paid')"
        return ''

    def _graph_title_and_key(self):
        """ Returns an array containing the appropriate graph title and key respectively.

            The key is for lineCharts, to have the on-hover label.
        """
        return ['', '']

    # Note: pos_sale/models/crm_team.py another inherit method
    def _graph_data(self, start_date, end_date):
        """ return format should be an iterable of dicts that contain {'x_value': ..., 'y_value': ...}
            x_values should either be dates, weeks, months or user_ids depending on the self.dashboard_graph_group value.
            y_values are floats.
        """
        query = """SELECT %(x_query)s as x_value, %(y_query)s as y_value
                     FROM %(table)s
                    WHERE team_id = %(team_id)s
                      AND DATE(%(date_column)s) >= %(start_date)s
                      AND DATE(%(date_column)s) <= %(end_date)s
                      %(extra_conditions)s
                    GROUP BY x_value;"""
        query = query % {
            'x_query': self._graph_x_query(),
            'y_query': self._graph_y_query(),
            'table': self._graph_sql_table(),
            'team_id': "%s",
            'date_column': self._graph_date_column(),
            'start_date': "%s",
            'end_date': "%s",
            'extra_conditions': self._extra_sql_conditions(),
        }
        self._cr.execute(query, [self.id, start_date, end_date])
        return self.env.cr.dictfetchall()

class Meeting(models.Model):
    _inherit = 'calendar.event'

    def _compute_is_highlighted(self):
        if self.env.context.get('active_model') == 'res.partner':
            partner_id = self.env.context.get('active_id')
            for event in self:
                if event.partner_ids.filtered(lambda s: s.id == partner_id):
                    event.is_highlighted = True

    is_highlighted = fields.Boolean(compute='_compute_is_highlighted', string='# Meetings Highlight')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    description_pickingin = fields.Text('Description on Receptions', translate=True)
    description_pickingout = fields.Text('Description on Delivery Orders', translate=True)

class AccountJournal(models.Model):
    _inherit = "account.journal"

    display_on_footer = fields.Boolean("Show in Invoices Footer", help="Display this bank account on the footer of printed documents like invoices and sales orders.")
    use_in_payment = fields.Boolean("Use in payment", help="Display this bank account on messages in payment process.")

class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['account.move', 'mail.thread']

    statement_line_id = fields.Many2one('account.bank.statement.line', index=True, string='Bank statement line reconciled with this entry', copy=False, readonly=True)

class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_installed_sale = fields.Boolean()
    default_purchase_method = fields.Selection([
        ('purchase', 'Ordered quantities'),
        ('receive', 'Delivered quantities'),
        ], string="Bill Control", default_model="product.template",
        help="This default value is applied to any new product created. "
        "This can be changed in the product detail form.", default="receive")
    module_sale = fields.Boolean("Sales")
    po_order_approval = fields.Boolean("Order Approval", default=lambda self: self.env.user.company_id.po_double_validation == 'two_step')
    module_sale = fields.Boolean("Sales")
    module_mrp = fields.Boolean("Manufacturing")
    lock_confirmed_po = fields.Boolean("Lock Confirmed Orders", default=lambda self: self.env.user.company_id.po_lock == 'lock')

    @api.multi
    def get_default_is_installed_sale(self, fields):
        return {
            'is_installed_sale': self.env['ir.module.module'].search([('name', '=', 'sale'), ('state', '=', 'installed')]).id
        }

    @api.multi
    def set_po_order_approval(self):
        self.po_double_validation = 'two_step' if self.po_order_approval else 'one_step'

    @api.multi
    def set_lock_confirmed_po(self):
        self.po_lock = 'lock' if self.lock_confirmed_po else 'edit'

class WizardValuationHistory(models.TransientModel):
    _inherit = 'wizard.valuation.history'

    compute_at_date = fields.Selection([
        (0, 'Current Inventory'),
        (1, 'At a Specific Date')
        ], string="Compute", help="Choose to analyze the current inventory or from a specific date in the past.")

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    module_currency_rate_live = fields.Boolean(string="Allow Currency Rate Live")
    module_account_bank_statement_import_camt = fields.Boolean("Import in CAMT.053 format")
    tax_cash_basis_journal_id = fields.Many2one('account.journal',
        related='company_id.tax_cash_basis_journal_id', string="Tax Cash Basis Journal",)
    module_l10n_eu_service = fields.Boolean(string="EU Digital Goods VAT")
    module_product_margin = fields.Boolean(string="Allow Product Margin")
    module_print_docsaway = fields.Boolean(string="Docsaway")

class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_cash_basis_journal_id = fields.Many2one('account.journal', string="Tax Cash Basis Journal")

class AccountTax(models.Model):
    _inherit = 'account.tax'

    use_cash_basis = fields.Boolean(
        'Use Cash Basis',
        help="Select this if the tax should use cash basis,"
        "which will create an entry for this tax on a given account during reconciliation")
    cash_basis_account = fields.Many2one(
        'account.account',
        string='Tax Received Account',
        domain=[('deprecated', '=', False)],
        help='Account use when creating entry for tax cash basis')

class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"

    name = fields.Char(translate=True)
    comparison = fields.Boolean('Allow comparison', default=True, help='display the comparison filter')
    cash_basis = fields.Boolean('Use cash basis', help='if true, report will always use cash basis, if false, user can choose from filter inside the report')
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    company_id = fields.Many2one('res.company', string='Company')
    date_range = fields.Boolean('Based on date ranges', default=True, help='specify if the report use date_range or single date')
    analytic = fields.Boolean('Allow analytic filter', help='display the analytic filter')
    tax_report = fields.Boolean('Tax Report', help="Set to True to automatically filter out journal items that have the boolean field 'tax_exigible' set to False")
    line_ids = fields.One2many('account.financial.html.report.line', 'financial_report_id', string='Lines')

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    country_ids = fields.Many2many(
        'res.country', 'payment_country_rel',
        'payment_id', 'country_id', 'Countries',
        help="This payment gateway is available for selected countries. If none is selected it is available for all countries.")

class CrmActivity(models.Model):
    _inherit = 'crm.activity'


class CrmLead(models.Model):
    _inherit = "crm.lead"

    date_action = fields.Date('Next Activity Date', index=True)
    next_activity_id = fields.Many2one("crm.activity", string="Next Activity", index=True)
    activity_ids = fields.One2many('mail.activity', 'res_id', 'Activities')
    activity_date_deadline = fields.Date('Next Activity Deadline', related='activity_ids.date_deadline',
        readonly=True, store=True)
    website = fields.Char('Website', index=True, help="Website of the contact")
    activity_summary = fields.Char('Next Activity Summary', related='activity_ids.summary')
    activity_type_id = fields.Many2one('mail.activity.type', 'Next Activity Type', related='activity_ids.activity_type_id')
    activity_state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], string='State',
        compute='_compute_activity_state',
        help='Status based on activities\nOverdue: Due date is already passed\n'
             'Today: Activity date is today\nPlanned: Future activities.')

    @api.depends('activity_ids.state')
    def _compute_activity_state(self):
        for record in self:
            states = record.activity_ids.mapped('state')
            if 'overdue' in states:
                record.activity_state = 'overdue'
            elif 'today' in states:
                record.activity_state = 'today'
            elif 'planned' in states:
                record.activity_state = 'planned'

class ActivityReport(models.Model):
    _inherit = "crm.activity.report"

    mail_activity_type_id = fields.Many2one('mail.activity.type', 'Activity Type', readonly=True)

class MailActivity(models.Model):
    _name = 'mail.activity'

    res_id = fields.Integer('Related Document ID', index=True)
    date_deadline = fields.Date('Deadline', index=True, required=True, default=fields.Date.today)
    summary = fields.Char('Summary')
    activity_type_id = fields.Many2one('mail.activity.type', 'Activity Type', readonly=True)
    state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], 'State',
        compute='_compute_state')

    @api.depends('date_deadline')
    def _compute_state(self):
        today = date.today()
        for record in self.filtered(lambda activity: activity.date_deadline):
            date_deadline = fields.Date.from_string(record.date_deadline)
            diff = (date_deadline - today)
            if diff.days == 0:
                record.state = 'today'
            elif diff.days < 0:
                record.state = 'overdue'
            else:
                record.state = 'planned'

class MailActivityType(models.Model):
    _name = 'mail.activity.type'

    name = fields.Char('Name', required=True, translate=True)

class CRMSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    generate_sales_team_alias = fields.Boolean("Automatically generate an email alias at the sales channel creation",
        help="Odoo will generate an email alias based on the sales channel name")
    default_generate_lead_from_alias = fields.Boolean('Manual Assignation of Emails')
    multi_sales_price = fields.Boolean("Multiple sales price per product", default_model='sale.config.settings')
    module_helpdesk = fields.Boolean("Helpdesk")
    module_sale_stock = fields.Boolean("Inventory")
    module_delivery_fedex = fields.Boolean("FedEx")
    module_delivery_usps = fields.Boolean("USPS")
    module_delivery_ups = fields.Boolean("UPS")
    module_delivery_dhl = fields.Boolean("DHL")
    module_sale_coupon = fields.Boolean("Manage coupons and promotional offers")
    module_product_email_template = fields.Boolean("Specific Email")
    module_timesheet_grid_sale = fields.Boolean("Timesheets")
    group_multi_currency = fields.Boolean("Multi-Currencies", implied_group='base.group_multi_currency')
    multi_sales_price_method = fields.Selection([
        ('percentage', 'Multiple prices per product (e.g. customer segments, currencies)'),
        ('formula', 'Price computed from formulas (discounts, margins, roundings)')
        ], string="Pricelists")
    group_stock_packaging = fields.Boolean("Packaging", implied_group='product.group_stock_packaging',
        help="""Ability to select a package type in sales orders and 
            to force a quantity that is a multiple of the number of units per package.""")
    module_web_clearbit = fields.Boolean("Company Research")
    default_use_sale_note = fields.Boolean()
    module_sale_ebay = fields.Boolean("eBay")
    module_account_accountant = fields.Boolean("Accounting")
    module_print_docsaway = fields.Boolean("Docsaway")

    @api.model
    def get_default_generate_sales_team_alias(self, fields):
        return {
            'generate_sales_team_alias': self.env['ir.values'].get_default('sale.config.settings', 'generate_sales_team_alias')
        }

    @api.multi
    def set_default_generate_sales_team_alias(self):
        IrValues = self.env['ir.values']
        if self.env['res.users'].has_group('base.group_erp_manager'):
            IrValues = IrValues.sudo()
        IrValues.set_default('sale.config.settings', 'generate_sales_team_alias', self.generate_sales_team_alias)

    @api.model
    def get_default_default_generate_lead_from_alias(self, fields):
        return {
            'default_generate_lead_from_alias': self.env['ir.config_parameter'].sudo().get_param('sale_config_settings.default_generate_lead_from_alias')
        }

    @api.multi
    def set_default_default_generate_lead_from_alias(self):
        self.env['ir.config_parameter'].sudo().set_param('sale_config_settings.default_generate_lead_from_alias', self.default_generate_lead_from_alias)

    @api.onchange('group_use_lead')
    def _onchange_group_use_lead(self):
        """ Reset alias / leads configuration if leads are not used """
        if not self.group_use_lead:
            self.default_generate_lead_from_alias = False

    @api.onchange('default_generate_lead_from_alias')
    def _onchange_default_generate_lead_from_alias(self):
        if self.default_generate_lead_from_alias:
            self.alias_prefix = self.alias_prefix or 'info'
        else:
            self.alias_prefix = False

    @api.model
    def get_default_sale_pricelist_setting(self, fields):
        sale_pricelist_setting = self.env['ir.values'].get_default('sale.config.settings', 'sale_pricelist_setting')
        multi_sales_price = sale_pricelist_setting in ['percentage', 'formula']
        return {
            'sale_pricelist_setting': sale_pricelist_setting,
            'multi_sales_price': multi_sales_price,
            'multi_sales_price_method': multi_sales_price and sale_pricelist_setting or False
        }

    @api.onchange('multi_sales_price', 'multi_sales_price_method')
    def _onchange_sale_price(self):
        if self.multi_sales_price and not self.multi_sales_price_method:
            self.update({
                'multi_sales_price_method': 'percentage',
            })
        self.sale_pricelist_setting = self.multi_sales_price and self.multi_sales_price_method or 'fixed'
        if self.sale_pricelist_setting == 'percentage':
            self.update({
                'group_product_pricelist': True,
                'group_sale_pricelist': True,
                'group_pricelist_item': False,
            })
        elif self.sale_pricelist_setting == 'formula':
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': True,
                'group_pricelist_item': True,
            })
        else:
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': False,
                'group_pricelist_item': False,
            })

    @api.model
    def get_default_use_sale_note(self, fields):
        default_use_sale_note = self.env['ir.config_parameter'].sudo().get_param('sale.default_use_sale_note', default=False)
        return dict(default_use_sale_note=default_use_sale_note)

    @api.multi
    def set_default_use_sale_note(self):
        self.env['ir.config_parameter'].sudo().set_param("sale.default_use_sale_note", self.default_use_sale_note)

class Groups(models.Model):
    _inherit = "res.groups"

    _sql_constraints = [
        ('name_uniq', 'CHECK(1=1)', 'The name of the group must be unique within an application!')
    ]