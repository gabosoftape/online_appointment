# -*- coding: utf-8 -*-

import pytz
import datetime
from datetime import datetime, timedelta, time

from odoo.addons.s2u_online_appointment.helpers import functions

from odoo import http, modules, tools
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class OnlineAppointment(http.Controller):

    def ld_to_utc(self, ld, appointee_id, duration=False):

        date_parsed = datetime.datetime.strptime(ld, "%b %d %Y %H:%M %p")
        if duration:
            date_parsed += datetime.timedelta(hours=duration)

        user = request.env['res.users'].sudo().search([('id', '=', appointee_id)])
        if user:
            if user.tz:
                tz = user.tz
            else:
                tz = 'America/Bogota'
            local = pytz.timezone(tz)
            local_dt = local.localize(date_parsed, is_dst=None)
            return local_dt.astimezone(pytz.utc)
        else:
            return ld

    def appointee_id_to_partner_id(self, appointee_id):

        appointee = request.env['res.users'].sudo().search([('id', '=', appointee_id)])
        if appointee:
            return appointee.partner_id.id
        else:
            return False

    def prepare_values(self, form_data=False, default_appointee_id=False, criteria='default'):

        #appointee_ids = self.select_appointees(criteria=criteria)
        #options = self.select_options(criteria=criteria)

        values = {
            'appointees': [],
            'timeslots': [],
            'appointee_id': 0,
            'appointment_option_id': 0,
            'appointment_date': '',
            'timeslot_id': 0,
            'mode': 'public' if request.env.user._is_public() else 'registered',
            'name': request.env.user.partner_id.name if not request.env.user._is_public() else '',
            'email': request.env.user.partner_id.email if not request.env.user._is_public() else '',
            'phone': request.env.user.partner_id.phone if not request.env.user._is_public() else '',
            'remarks': '',
            'error': {},
            'error_message': [],
            'form_action': '/online-appointment/appointment-confirm',
            'form_criteria': criteria
        }

        if form_data:
            try:
                appointee_id = int(form_data.get('appointee_id', 0))
            except:
                appointee_id = 0

            try:
                appointment_option_id = int(form_data.get('appointment_option_id', 0))
            except:
                appointment_option_id = 0

            try:
                timeslot_id = int(form_data.get('timeslot_id', 0))
            except:
                timeslot_id = 0

            try:
                appointment_date = datetime.datetime.strptime(form_data['appointment_date'], '%b %d %Y %H:%M %p').strftime('%b %d %Y %H:%M %p')
            except:
                appointment_date = ''

            values.update({
                'name': form_data.get('name', ''),
                'email': form_data.get('email', ''),
                'phone': form_data.get('phone', ''),
                'appointee_id': appointee_id,
                'appointment_option_id': appointment_option_id,
                'appointment_date': appointment_date,
                'timeslot_id': timeslot_id,
                'remarks': form_data.get('remarks', '')
            })

            if appointee_id and appointment_option_id and appointment_date:
                free_slots = self.get_free_appointment_slots_for_day(appointment_option_id, form_data['appointment_date'], appointee_id, criteria)
                days_with_free_slots = self.get_days_with_free_slots(appointment_option_id,
                                                                     appointee_id,
                                                                     datetime.datetime.strptime(form_data['appointment_date'], '%d/%m/%Y').year,
                                                                     datetime.datetime.strptime(form_data['appointment_date'], '%d/%m/%Y').month,
                                                                     criteria)
                values.update({
                    'timeslots': free_slots,
                    'days_with_free_slots': days_with_free_slots,
                    'focus_year': datetime.datetime.strptime(form_data['appointment_date'], '%d/%m/%Y').year,
                    'focus_month': datetime.datetime.strptime(form_data['appointment_date'], '%d/%m/%Y').month
                })
        else:
            if values['appointees']:
                try:
                    default_appointee_id = int(default_appointee_id)
                except:
                    default_appointee_id = False
                if default_appointee_id and default_appointee_id in values['appointees'].ids:
                    values['appointee_id'] = default_appointee_id
                else:
                    values['appointee_id'] = values['appointees'][0].id
            if True:
                values['appointment_option_id'] = 0
        return values

    @http.route(['/online-appointment'], auth='user', website=True, csrf=True)
    def online_appointment(self, **kw):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_online_appointment')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('s2u_online_appointment.only_registered_users')
        values = self.prepare_values(default_appointee_id=kw.get('appointee', False))

        return request.render('s2u_online_appointment.make_appointment', values)

    @http.route(['/online-appointment/appointment-confirm'], auth="public", type='http', website=True)
    def online_appointment_confirm(self, **post):
        error = {}
        error_message = []

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_online_appointment')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('s2u_online_appointment.only_registered_users')

            if not post.get('name', False):
                error['name'] = True
                error_message.append(_('Por favor, escriba su nombre.'))
            if not post.get('email', False):
                error['email'] = True
                error_message.append(_('Por favor, introduzca su dirección de correo electrónico.'))
            elif not functions.valid_email(post.get('email', '')):
                error['email'] = True
                error_message.append(_('Por favor, introduce una dirección de correo electrónico válida.'))
            if not post.get('phone', False):
                error['phone'] = True
                error_message.append(_('Por favor, introduzca su número de teléfono.'))
        # Remover validacion de tipo, doctor, fecha y hora.. porque no seran añadidos por el creador, sino por el blass
        #try:
        #    appointee_id = int(post.get('appointee_id', 0))
        #except:
        #    appointee_id = 0
        # validacion no doctor
        #if not appointee_id:
        #    error['appointee_id'] = True
        #    error_message.append(_('Por favor seleccione un Doctor válido.'))
        # Obtengo las opciones previamente configuradas.
        #option = request.env['s2u.appointment.option'].sudo().search([('id', '=', int(post.get('appointment_option_id', 0)))])
        # Validacion si no tengo tipo configurado
        #if not option:
        #    error['appointment_option_id'] = True
        #    error_message.append(_('Por favor seleccione un tipo válido.'))
    # Busco horarios de trabajo en mi modelo.
        # Validacion horario
        #slot = request.env['s2u.appointment.slot'].sudo().search([('id', '=', int(post.get('timeslot_id', 0)))])
        #if not slot:
        #    error['timeslot_id'] = True
        #    error_message.append(_('Seleccione un intervalo de tiempo válido.'))
    # validacion completa de fecha vs horarios de trabajo
        #try:
        #    date_start = datetime.datetime.strptime(post['appointment_date'], '%d/%m/%Y').strftime('%Y-%m-%d')
        #    day_slot = date_start + ' ' + functions.float_to_time(slot.slot)
        #    start_datetime = self.ld_to_utc(day_slot, appointee_id)
        #except:
        #    error['appointment_date'] = True
        #    error_message.append(_('Por favor seleccione una fecha valida.'))

        values = self.prepare_values(form_data=post)
        if error_message:
            values['error'] = error
            values['error_message'] = error_message
            return request.render('s2u_online_appointment.make_appointment', values)
    # validacion completa en caso de que se seleccione una ranura ocupada
        #if not self.check_slot_is_possible(option.id, post['appointment_date'], appointee_id, slot.id):
        #   values['error'] = {'timeslot_id': True}
        #    values['error_message'] = [_('La ranura de tiempo ya está ocupada, elija otra ranura.')]
        #    return request.render('s2u_online_appointment.make_appointment', values)
    # si el usuario no esta registrado lo registramos. por ahora que se registre, por loca
        #if request.env.user._is_public():
        #    partner = request.env['res.partner'].sudo().search(['|', ('phone', 'ilike', values['phone']),
        #                                                             ('email', 'ilike', values['email'])])
        #    if partner:
        #        partner_ids = [self.appointee_id_to_partner_id(appointee_id),
        #                       partner[0].id]
        #    else:
        #        partner = request.env['res.partner'].sudo().create({
        #            'name': values['name'],
        #            'phone': values['phone'],
        #            'email': values['email']
        #        })
        #        partner_ids = [self.appointee_id_to_partner_id(appointee_id),
        #                       partner[0].id]
        #else:
        #    partner_ids = [self.appointee_id_to_partner_id(appointee_id),
        #                   request.env.user.partner_id.id]

        # set detaching = True, we do not want to send a mail to the attendees
        #aqui se crea el nuevo evento en calendario mkon.
        now = datetime.now()
#        appointment = request.env['calendar.event'].sudo().with_context(detaching=False).create({
#            'name': "Nueva cita medica creada",
#            'description': post.get('remarks', ''),
#            'start': now.strftime("%Y-%m-%d %H:%M:%S"),
#            'stop': (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
#            'user_id': request.env.user.id,
#        })
        # set all attendees on 'accepted'
#        appointment.attendee_ids.write({
#            'state': 'accepted'
#        })

        # registered user, we want something to show in his portal
        if not request.env.user._is_public():
            vals = {
                'partner_id': request.env.user.partner_id.id,
                'descripcion': post.get('remarks'),
                'enfermedades': post.get('antecedentes'),
                'cirugias': post.get('procedimientos'),
                'state': 'pending',
                # 'appointee_id': self.appointee_id_to_partner_id(appointee_id),
                #'event_id': appointment.id
            }
            registration = request.env['s2u.appointment.registration'].create(vals)
            print(registration)

        return request.redirect('/online-appointment/appointment-scheduled?appointment=%d' % registration.id)

    @http.route(['/online-appointment/appointment-scheduled'], auth="public", type='http', website=True)
    def confirmed(self, **post):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_online_appointment')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('s2u_online_appointment.only_registered_users')

        registro = request.env['s2u.appointment.registration'].sudo().search([('id', '=', int(post.get('appointment', 0)))])
        if not registro:
            values = {
                'appointment': False,
                'error_message': [],
                'registration_id': False,
            }
            return request.render('s2u_online_appointment.thanks', values)

        if request.env.user._is_public():
            values = {
                'appointment': False,
                'error_message': []
            }
            return request.render('s2u_online_appointment.thanks', values)
        else:
            if request.env.user.partner_id.id != registro.partner_id.id:
                values = {
                    'appointment': False,
                    'error_message': [_('Appointment not found.')]
                }
                return request.render('s2u_online_appointment.thanks', values)

            values = {
                'appointment': registro,
                'error_message': []
            }
            return request.redirect('/shop/cart/update?product_id=2&amp;express=1')

    def recurrent_events_overlapping(self, appointee_id, event_start, event_stop):
        query = """
                    SELECT e.id FROM calendar_event e, calendar_event_res_partner_rel ep  
                        WHERE ep.res_partner_id = %s AND
                              e.active = true AND
                              e.recurrency = true AND
                              e.final_date >= %s AND
                              e.id = ep.calendar_event_id                                         
        """
        request.env.cr.execute(query, (self.appointee_id_to_partner_id(appointee_id),
                                       datetime.datetime.now().strftime('%Y-%m-%d')))
        res = request.env.cr.fetchall()
        event_ids = [r[0] for r in res]
        for event in request.env['calendar.event'].sudo().browse(event_ids):
            recurrent_dates = event._get_recurrent_dates_by_event()
            for recurrent_start_date, recurrent_stop_date in recurrent_dates:
                recurrent_start_date_short = recurrent_start_date.strftime('%Y-%m-%d %H:%M')
                recurrent_stop_date_short = recurrent_stop_date.strftime('%Y-%m-%d %H:%M')
                if (event_start <= recurrent_start_date_short <= event_stop) or (
                        recurrent_start_date_short <= event_start and recurrent_stop_date_short >= event_stop) or (
                        event_start <= recurrent_stop_date_short <= event_stop):
                    return True
        return False

    def check_slot_is_possible(self, option_id, appointment_date, appointee_id, slot_id):

        if not appointment_date:
            return False

        if not appointee_id:
            return False

        if not option_id:
            return False

        if not slot_id:
            return False

        option = request.env['s2u.appointment.option'].sudo().search([('id', '=', option_id)])
        if not option:
            return False
        slot = request.env['s2u.appointment.slot'].sudo().search([('id', '=', slot_id)])
        if not slot:
            return False

        date_start = datetime.datetime.strptime(appointment_date, '%d/%m/%Y').strftime('%Y-%m-%d')

        # if today, then skip slots in te past (< current time)
        if date_start == datetime.datetime.now().strftime('%Y-%m-%d') and self.ld_to_utc(date_start + ' ' + functions.float_to_time(slot.slot), appointee_id) < datetime.datetime.now(pytz.utc):
            return False

        event_start = self.ld_to_utc(date_start + ' ' + functions.float_to_time(slot.slot), appointee_id).strftime("%Y-%m-%d %H:%M:%S")
        event_stop = self.ld_to_utc(date_start + ' ' + functions.float_to_time(slot.slot), appointee_id,
                                    duration=option.duration).strftime("%Y-%m-%d %H:%M:%S")

        query = """
                SELECT e.id FROM calendar_event e, calendar_event_res_partner_rel ep  
                    WHERE ep.res_partner_id = %s AND
                          e.active = true AND
                          (e.recurrency = false or e.recurrency is null) AND
                          e.id = ep.calendar_event_id AND 
                        ((e.start >= %s AND e.start <= %s) OR
                             (e.start <= %s AND e.stop >= %s) OR
                             (e.stop >= %s) AND e.stop <= %s)                                       
        """
        request.env.cr.execute(query, (self.appointee_id_to_partner_id(appointee_id),
                                       event_start, event_stop,
                                       event_start, event_stop,
                                       event_start, event_stop))
        res = request.env.cr.fetchall()
        if not res:
            if not self.recurrent_events_overlapping(appointee_id, event_start, event_stop):
                return True

        return False

    def filter_slots(self, slots, criteria):
        # override this method when slots needs to be filtered
        return slots

    def get_free_appointment_slots_for_day(self, option_id, appointment_date, appointee_id, criteria):

        def slot_present(slots, slot):

            for s in slots:
                if s['timeslot'] == functions.float_to_time(slot):
                    return True
            return False

        if not appointment_date:
            return []

        if not appointee_id:
            return []

        option = request.env['s2u.appointment.option'].sudo().search([('id', '=', option_id)])
        if not option:
            return []

        week_day = datetime.datetime.strptime(appointment_date, '%d/%m/%Y').weekday()
        slots = request.env['s2u.appointment.slot'].sudo().search([('user_id', '=', appointee_id),
                                                                   ('day', '=', str(week_day))])
        slots = self.filter_slots(slots, criteria)

        date_start = datetime.datetime.strptime(appointment_date, '%d/%m/%Y').strftime('%Y-%m-%d')
        free_slots = []
        for slot in slots:
            # skip double slots
            if slot_present(free_slots, slot.slot):
                continue

            # if today, then skip slots in te past (< current time)
            if date_start == datetime.datetime.now().strftime('%Y-%m-%d') and self.ld_to_utc(date_start + ' ' + functions.float_to_time(slot.slot), appointee_id) < datetime.datetime.now(pytz.utc):
                continue

            event_start = self.ld_to_utc(date_start + ' ' + functions.float_to_time(slot.slot), appointee_id).strftime("%Y-%m-%d %H:%M:%S")
            event_stop = self.ld_to_utc(date_start + ' ' + functions.float_to_time(slot.slot), appointee_id,
                                        duration=option.duration).strftime("%Y-%m-%d %H:%M:%S")

            # check normal calendar events
            query = """
                    SELECT e.id FROM calendar_event e, calendar_event_res_partner_rel ep  
                        WHERE ep.res_partner_id = %s AND
                              e.active = true AND
                              (e.recurrency = false or e.recurrency is null) AND 
                              e.id = ep.calendar_event_id AND 
                            ((e.start >= %s AND e.start <= %s) OR
                             (e.start <= %s AND e.stop >= %s) OR
                             (e.stop >= %s) AND e.stop <= %s)                                         
            """
            request.env.cr.execute(query, (self.appointee_id_to_partner_id(appointee_id),
                                           event_start, event_stop,
                                           event_start, event_stop,
                                           event_start, event_stop))
            res = request.env.cr.fetchall()
            if not res:
                if not self.recurrent_events_overlapping(appointee_id, event_start, event_stop):
                    free_slots.append({
                        'id': slot.id,
                        'timeslot': functions.float_to_time(slot.slot)
                    })

        return free_slots

    def get_days_with_free_slots(self, option_id, appointee_id, year, month, criteria):

        if not option_id:
            return {}

        if not appointee_id:
            return {}

        start_datetimes = {}
        start_date = datetime.date(year, month, 1)
        for i in range(31):
            if start_date < datetime.date.today():
                start_date += datetime.timedelta(days=1)
                continue
            if start_date.weekday() not in start_datetimes:
                start_datetimes[start_date.weekday()] = []
            start_datetimes[start_date.weekday()].append(start_date.strftime('%Y-%m-%d'))
            start_date += datetime.timedelta(days=1)
            if start_date.month != month:
                break

        day_slots = []

        option = request.env['s2u.appointment.option'].sudo().search([('id', '=', option_id)])
        if not option:
            return {}

        for weekday, dates in start_datetimes.items():
            slots = request.env['s2u.appointment.slot'].sudo().search([('user_id', '=', appointee_id),
                                                                       ('day', '=', str(weekday))])
            slots = self.filter_slots(slots, criteria)

            for slot in slots:
                for d in dates:
                    # if d == today, then skip slots in te past (< current time)
                    if d == datetime.datetime.now().strftime('%Y-%m-%d') and self.ld_to_utc(d + ' ' + functions.float_to_time(slot.slot), appointee_id) < datetime.datetime.now(pytz.utc):
                        continue

                    day_slots.append({
                        'timeslot': functions.float_to_time(slot.slot),
                        'date': d,
                        'start': self.ld_to_utc(d + ' ' + functions.float_to_time(slot.slot), appointee_id).strftime("%Y-%m-%d %H:%M:%S"),
                        'stop': self.ld_to_utc(d + ' ' + functions.float_to_time(slot.slot), appointee_id, duration=option.duration).strftime("%Y-%m-%d %H:%M:%S")
                    })
        days_with_free_slots = {}
        for d in day_slots:
            if d['date'] in days_with_free_slots:
                # this day is possible, there was a slot possible so skip other slot calculations for this day
                # We only need to inform the visitor he can click on this day (green), after that he needs to
                # select a valid slot.
                continue

            query = """
                    SELECT e.id FROM calendar_event e, calendar_event_res_partner_rel ep  
                        WHERE ep.res_partner_id = %s AND 
                              e.active = true AND
                              (e.recurrency = false or e.recurrency is null) AND
                              e.id = ep.calendar_event_id AND  
                            ((e.start >= %s AND e.start <= %s) OR
                             (e.start <= %s AND e.stop >= %s) OR
                             (e.stop >= %s) AND e.stop <= %s)                                         
            """
            request.env.cr.execute(query, (self.appointee_id_to_partner_id(appointee_id),
                                           d['start'], d['stop'],
                                           d['start'], d['stop'],
                                           d['start'], d['stop']))
            res = request.env.cr.fetchall()
            if not res:
                if not self.recurrent_events_overlapping(appointee_id, d['start'], d['stop']):
                    days_with_free_slots[d['date']] = True
        return days_with_free_slots




    def online_appointment_state_change(self, appointment, previous_state):
        # método para anular cuando desea que algo suceda en un cambio de estado, por ejemplo, enviar correo
        return True

    @http.route(['/online-appointment/portal/cancel'], auth="public", type='http', website=True)
    def online_appointment_portal_cancel(self, **post):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_online_appointment')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('s2u_online_appointment.only_registered_users')

        try:
            id = int(post.get('appointment_to_cancel', 0))
        except:
            id = 0

        if id:
            appointment = request.env['s2u.appointment.registration'].search([('id', '=', id)])
            if appointment and (
                    appointment.partner_id == request.env.user.partner_id or appointment.appointee_id == request.env.user.partner_id):
                previous_state = appointment.state
                appointment.cancel_appointment()
                self.online_appointment_state_change(appointment, previous_state)

        return request.redirect('/my/online-appointments')

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home_redirect(self, **kw):
        return request.redirect('/my/online-appointments')

    @http.route(['/online-appointment/portal/confirm'], auth="public", type='http', website=True)
    def online_appointment_portal_confirm(self, **post):

        if request.env.user._is_public():
            param = request.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_online_appointment')], limit=1)
            if not param or param.value.lower() != 'public':
                return request.render('s2u_online_appointment.only_registered_users')

        try:
            id = int(post.get('appointment_to_confirm', 0))
        except:
            id = 0

        if id:
            appointment = request.env['s2u.appointment.registration'].search([('id', '=', id)])
            if appointment and (
                    appointment.partner_id == request.env.user.partner_id or appointment.appointee_id == request.env.user.partner_id):
                previous_state = appointment.state
                appointment.confirm_appointment()
                self.online_appointment_state_change(appointment, previous_state)

        return request.redirect('/my/online-appointments')

