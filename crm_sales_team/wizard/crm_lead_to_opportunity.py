# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Lead2OpportunityPartner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'

    @api.onchange('user_id')
    def _onchange_user(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of.
        """
        if self.user_id:
            if self.team_id:
                user_in_team = self.env['crm.team'].search_count([('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id), ('member_ids', 'in', [self.user_id.id])])
            else:
                user_in_team = False
            if not user_in_team:
                values = self.env['crm.lead']._onchange_user_values(self.user_id.id if self.user_id else False)
                self.team_id = values.get('team_id', False)

    @api.multi
    def action_apply(self):
        res = super(Lead2OpportunityPartner, self).action_apply()
        lead = self.env['crm.lead'].browse(self._context.get('active_ids', []))
        lead.number = self.env['ir.sequence'].next_by_code('crm.lead')
        return res