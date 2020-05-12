# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AppointmentPartner(models.Model):
    _inherit = "res.partner"

    # nuevas celdas añadidas a partner
    historial_ids = fields.One2many('s2u.appointment.registration', 'partner_id', 'Historial Clinico')
    contact_type = fields.Selection(
        string=u'Tipo de Contacto',
        selection=[
            ('1', u'Paciente'),
            ('2', u'Medico'),
            ('3', u'Especialista'),
        ],
        default='1',
        help=u'Identificacion del Cliente, segun los tipos definidos por la DIAN.',
    )
    id_type = fields.Selection(
        string=u'Tipo de Documento',
        selection=[
            ('CC', 'CEDULA DE CIUDADANÍA'),
            ('CE', 'CEDULA DE EXTRANJERÍA'),
            ('PA', 'PASAPORTE'),
            ('SC', 'SALVO CONDUCTO'),
            ('RC', 'REGISTRO CIVIL '),
            ('PE', 'PERMISO ESPECIAL DE PERMANENCIA'),
            ('TI', 'TARJETA DE IDENTIDAD'),
            ('AS', 'ADULTO SIN IDENTIFICAR'),
            ('MS', 'MENOR SIN IDENTIFICAR'),
        ],
        help=u'Identificacion del Cliente',
    )
    id_document = fields.Integer(string='No. Documento', default=None)
    sex = fields.Selection(
        string=u'Sexo',
        selection=[
            ('M', 'Masculino'),
            ('F', 'Femenino')
        ],
    )
    estado_civil = fields.Char('Estado Civil')
    eps = fields.Char('EPS')
    afil_type = fields.Char('Tipo de Afiliacion')
