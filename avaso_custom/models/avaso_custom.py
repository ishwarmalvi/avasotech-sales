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

from openerp import models, fields, api


class CrmTeam(models.Model):
    _inherit = "crm.team"

    quotations_amount = fields.Integer(string='Amount of quotations to invoice', readonly=True)
    dashboard_graph_data = fields.Text()
    opportunities_count = fields.Integer(string='Number of open opportunities', readonly=True)
    quotations_count = fields.Integer(string='Number of quotations to invoice', readonly=True)
    sales_to_invoice_count = fields.Integer(string='Number of sales to invoice', readonly=True)
    dashboard_graph_type = fields.Selection([('line', 'Line'),('bar', 'Bar')], string='Type',
        help='The type of graph this channel will display in the dashboard.')
    unassigned_leads_count = fields.Integer(string='Unassigned Leads', readonly=True)
    opportunities_amount = fields.Integer(string='Amount of quotations to invoice', readonly=True)
    dashboard_button_name = fields.Char(string="Dashboard Button")
    dashboard_graph_group = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('user', 'Salesperson'),
    ], string='Group by', default='day', help="How this channel's dashboard graph will group the results.")
    team_type = fields.Selection([('sales', 'Sales'), ('website', 'Website'), ('pos', 'Point of Sale')], string='Channel Type',
        default='sales', required=True, help="The type of this channel, it will define the resources this channel uses.")
    dashboard_graph_period = fields.Selection([
        ('week', 'Last Week'),
        ('month', 'Last Month'),
        ('year', 'Last Year'),
    ], string='Scale', default='month', help="The time period this channel's dashboard graph will consider.")
    dashboard_graph_model = fields.Selection([('sale.report', 'Sales'), ('account.invoice.report', 'Invoices'),
        ('crm.opportunity.report', 'Pipeline')], string="Content", help='The graph this channel will display in the Dashboard.\n')


class AccountJournal(models.Model):
    _inherit = "account.journal"

    display_on_footer = fields.Boolean("Show in Invoices Footer", help="Display this bank account on the footer of printed documents like invoices and sales orders.")

class AccountMove(models.Model):
    _inherit = "account.move"

    statement_line_id = fields.Many2one('account.bank.statement.line', index=True, string='Bank statement line reconciled with this entry', copy=False, readonly=True)

class Meeting(models.Model):
    _inherit = 'calendar.event'

    is_highlighted = fields.Boolean(string='Is the Event Highlighted')