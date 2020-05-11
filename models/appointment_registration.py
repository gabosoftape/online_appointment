# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AppointmentRegistration(models.Model):
    _name = 's2u.appointment.registration'
    _description = 'Appointment Registration'
    _inherit = ['portal.mixin', 'mail.thread.cc', 'mail.activity.mixin']

    event_id = fields.Many2one('calendar.event', string='Event', ondelete='cascade')
    factura = fields.Many2one('account.move', string="Factura vinculada")
    partner_id = fields.Many2one('res.partner', string='Cliente', ondelete='cascade')
    appointee_id = fields.Many2one('res.partner', string='Doctor', ondelete='cascade')
    appointment_begin = fields.Datetime(string="Inicio de evento", related='event_id.start', readonly=True, store=True)
    appointment_end = fields.Datetime(string="Fin de Evento", related='event_id.stop', readonly=True)
    name = fields.Char(string='Evento', related='partner_id.name', readonly=True, store=True)
    state = fields.Selection([
        ('pending', _('Pendiente')),
        ('valid', _('Agendada')),
        ('iniciada', _('Iniciada')),
        ('finish',_('Finalizada')),
        ('cancel', _('Cancelada')),
    ], required=True, default='valid', string='Status', copy=False)
    descripcion = fields.Text(string="Descripcion de sintomas del paciente")
    appointee_interaction = fields.Boolean(string='Terminada', default=False)
    diagnostico = fields.Text(string="Diagnostico")
    medicacion = fields.Text(string="Medicacion")
    enfermedades = fields.Text(string="Antecedente Enfermedades")
    cirugias = fields.Text(string="Antecedentes procedimientos quirurgicos")

    def cancel_appointment(self):
        for appointment in self:
            if appointment.state in ['pending', 'valid']:
                appointment.sudo().event_id.write({
                    'active': False
                })
                appointment.write({
                    'state': 'cancel'
                })

        return True

    def confirm_appointment(self):

        for appointment in self:
            if appointment.state == 'pending':
                appointment.write({
                    'state': 'valid'
                })

        return True

    def start_appointment(self):

        for appointment in self:
            if appointment.state == 'pending':
                appointment.write({
                    'state': 'valid'
                })

        return True
