# -*- coding: utf-8 -*-

from collections import OrderedDict
from operator import itemgetter
import datetime
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['appointment_count'] = request.env['s2u.appointment.registration'].search_count(['|', ('partner_id', '=', request.env.user.partner_id.id),
                                                                                                     '&', ('appointee_id', '=', request.env.user.partner_id.id),
                                                                                                          ('appointee_interaction', '=', True)])
        return values

    # ------------------------------------------------------------
    # My Appointment
    # ------------------------------------------------------------
    def _appointment_get_page_view_values(self, appointment, access_token, **kwargs):
        values = {
            'page_name': 'appointment',
            'appointment': appointment,
        }
        return self._get_page_view_values(appointment, access_token, values, 'my_appointment_history', False, **kwargs)

    @http.route(['/my/online-appointments', '/my/online-appointments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_appointments(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        domain = [('partner_id', '=', request.env.user.partner_id.id)]

        searchbar_sortings = {
            'new': {'label': _('Recientes'), 'order': 'id desc'},
            'date1': {'label': _('Fecha ↓'), 'order': 'appointment_begin'},
            'date2': {'label': _('Fecha ↑'), 'order': 'appointment_begin desc'},
            'name': {'label': _('Nombre'), 'order': 'name'},
        }
        if not sortby or sortby not in searchbar_sortings.keys():
            sortby = 'new'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'Todo': {'label': _('Todo'), 'domain': []},
            'pending': {'label': _('Pendientes'), 'domain': [('state', '=', 'pending')]},
            'scheduled': {'label': _('Confirmadas'), 'domain': [('state', '=', 'valid')]},
            'cancel': {'label': _('Canceladas'), 'domain': [('state', '=', 'cancel')]},
        }
        if not filterby:
            filterby = 'Todo'
        domain = searchbar_filters[filterby]['domain'] + domain

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('s2u.appointment.registration', domain)
        if date_begin and date_end:
            domain = [('create_date', '>', date_begin), ('create_date', '<=', date_end)] + domain
        # appointments count
        appointment_count = request.env['s2u.appointment.registration'].search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/online-appointments",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=appointment_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        appointments = request.env['s2u.appointment.registration'].search([('state', '=', 'valid'),('partner_id', '=', request.env.user.partner_id.id)], order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_appointments_history'] = appointments.ids[:100]
        try:
            fechaappointment = datetime.datetime.strptime(date_begin, '%b %d %Y %H:%M %p').strftime('%b %d %Y %H:%M %p')
        except:
            fechaappointment = ""

        hora = date_begin
        values.update({
            'date': fechaappointment,
            'date_end': hora,
            'appointments': appointments,
            'page_name': 'appointment',
            'archive_groups': archive_groups,
            'default_url': '/my/online-appointments',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("s2u_online_appointment.portal_my_appointments", values)

    @http.route(['/my/online-appointment/<int:appointment_id>'], type='http', auth="public", website=True)
    def portal_my_appointment(self, appointment_id=None, access_token=None, **kw):
        try:
            appointment_sudo = self._document_check_access('s2u.appointment.registration', appointment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._appointment_get_page_view_values(appointment_sudo, access_token, **kw)
        return request.render("s2u_online_appointment.portal_my_appointment", values)
