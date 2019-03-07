# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MergeOpportunity(models.TransientModel):
    _inherit = 'crm.merge.opportunity'

    @api.onchange('user_id')
    def _onchange_user(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        team_id = False
        if self.user_id:
            user_in_team = False
            if self.team_id:
                user_in_team = self.env['crm.team'].search_count([('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id), ('member_ids', 'in', [self.user_id.id])])
            if not user_in_team:
                team_id = self.env['crm.team'].search(['|', ('user_id', '=', self.user_id.id), ('member_ids', '=', [self.user_id.id])], limit=1)
        self.team_id = team_id