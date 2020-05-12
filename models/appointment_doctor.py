# -*- coding: utf-8 -*-

from odoo.addons.s2u_online_appointment.helpers import functions
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AppointmentDoctor(models.Model):
    _name = 's2u.appointment.doctor'
    _description = "Appointment Doctor"

    name = fields.Char('Nombre')
    login = fields.Char('Login')
    email = fields.Char('Correo Electronico')
    phone = fields.Char('Telefono')
    documento = fields.Char('No. Documento')
    image = fields.Binary('Imagen')
    partner_id = fields.Many2one('res.partner', ondelete='restrict',
                                 string='Related Partner', help='Partner-related data of the user')
    res_group_id = fields.Many2many('res.groups', 'rel_faculty_group', string="Assign Group", required=True)

    @api.model
    def create(self, vals):
        doctor_group = self.env.ref('s2u_online_appointment.group_appointments_doctor')
        new_user = self.env['res.users'].create({
            'name': vals['name'],
            'login': vals['login'],
            'email': vals['email'],
            'notification_type': 'email',
            'company_id': self.env.ref('base.main_company').id,
            'groups_id': [(6, 0, [doctor_group.id, self.env.ref('base.group_user').id])]
        })
        print(new_user.id)
        result = super(AppointmentDoctor, self).create(vals)
        result['partner_id'] = self.env['res.partner'].sudo().create({'name': vals['name'],
                                                                      'email': vals['email'],
                                                                      'contact_type': '2',
                                                                      'company_id': self.env.ref(
                                                                          'base.main_company').id})
        #result['employee_id'] = self.env['hr.employee'].sudo().create({'name': result['name'],
        #                                                               'user_id': new_user.id,
        #                                                               'address_home_id': result['partner_id'].id,
        #                                                               'company_id': self.env.ref(
        #                                                                   'base.main_company').id})
        #user = self.env['res.users'].sudo().search([('login', '=', vals['login'])])
        #        user.action_reset_password()
        return result
