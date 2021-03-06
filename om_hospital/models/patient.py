# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import date,datetime
from dateutil.relativedelta import relativedelta
import re

class HospitalPatient(models.Model):
    _name = "hospital.patient"
    _inherit = ["mail.thread","mail.activity.mixin"]
    _description = "Hospital Patient informations"
    _order =  'name desc'
 

    name = fields.Char(string="ID", required=True, tracking=True, 
                            copy=False, readonly=True, default= lambda self: _('New'))
    first_name = fields.Char(string='Name', required=True, tracking=True)
    prefix = fields.Selection([('mr','Mr'),('miss','Miss'),('mrs','Mrs'),('ms','Ms'),('baby','Baby')],string="Prefix")
    last_name = fields.Char('Last Name')
    full_name = fields.Char('Full Name', compute='_compute_full_name')
    date_of_birth = fields.Date('Birth Date')
    parent = fields.Many2one('hospital.patient',string='Parent Name')
    resposible_id = fields.Many2one('res.partner',string='Responsible')
    age = fields.Char(string='Age', tracking=True)
    appoinment_count = fields.Integer(string='Appoitment Count', compute='_compute_appoinment_count')
    Gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], required=True, default='male', tracking=True)
    note = fields.Text(string='Description')
    state = fields.Selection([('draft', 'Draft'), 
                              ('confirm', 'Confirmed'),
                              ('done','Done'),
                              ('cancel','Cancelled')], string ="Status", tracking=True, default='draft')
    appoinment_ids = fields.One2many('hospital.appoinment','patient_id',string='Appoitments')
    image = fields.Binary(string="Patient Image",widget="image")
    partner_id = fields.Many2one('res.partner',string="Partner",readonly=True)
    phone = fields.Char('Phone',required=True)
    # email = fields.Char(string="Email",readonly=True)
    re_generated_by = fields.Many2one('res.users', "Generated By", ondelete='restrict')
    email = fields.Char("Email")

    _sql_constraints = [
        ('check_percentage', 'CHECK(age >= 0 OR age=0)',
         'The percentage of an analytic distribution should be between 0 and 100.')
    ]

    @api.model
    def send_birthday_email(self):
        wish_template_id = self.env.ref(
            'om_hospital.email_template_birthday_wish', raise_if_not_found=False)
        print('ABCd',wish_template_id)
        today = datetime.now()
        today_month_day = '%-' + today.strftime('%m') + '-' + today.strftime('%d')
        patient_ids = self.search([('date_of_birth', 'like', today_month_day)])
        for patient_id in patient_ids:
            if patient_id.email:
                wish_temp = wish_template_id
                wish_temp.sudo().send_mail(patient_id.id, force_send=True)


    @api.depends('prefix', 'first_name', 'last_name')
    def _compute_full_name(self):
        for rec in self:
            rec.full_name = str(rec.prefix) + ' ' + str(rec.first_name) + ' ' + str(rec.last_name)

    @api.constrains('first_name')
    def check_name(self):
        for rec in self:
            print("test")
            patients = self.env['hospital.patient'].search([('first_name','=',rec.first_name),('id','!=',rec.id)])
            if patients:
                raise ValidationError("Name already exists")

    @api.constrains('age')
    def check_ages(self):
        for rec in self:
            if rec.age == 0:
                raise ValidationError("Age should not be 0")


    @api.constrains('phone')
    def check_num(self):
        for rec in self:
            if len(rec.phone) != 10:
                raise ValidationError("Number should be just 10 digits")

    @api.onchange('date_of_birth')
    def _onchange_age(self):
        self.age = False
        age = self.get_age_from_dob(self.date_of_birth)
        self.age = age

    def get_age_from_dob(self, date_of_birth):
        today = date.today()
        dob = fields.Date.from_string(date_of_birth)
        gap = relativedelta(today, dob)
        if dob == today:
            self.age = str(1) + ' Days '
        if gap.years > 0:
            self.age = str(gap.years) + ' Years ' + str(gap.months) + ' Months '
        if gap.years == 0 and gap.months > 0:
            self.age = str(gap.months) + ' Months '
        if gap.years == 0 and gap.months == 0 and gap.days > 0:
            self.age = str(gap.days) + ' Days '
        age = self.age
        return age

    @api.onchange('phone')
    def onchnage_phone(self):
        if self.phone:
            if re.match("^[0-9]{10}$", self.phone) == None:
                raise ValidationError(_("Enter valid 10 digits Mobile number"))

    def _compute_appoinment_count(self):
        for rec in self:
            appoinment_count = self.env['hospital.appoinment'].search_count([('patient_id','=',rec.id)])
            rec.appoinment_count = appoinment_count

    def action_confirm(self):
        # raise UserError("Working---------")
        self.state = 'confirm'

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state ='draft'

    def action_cancel(self):
        self.state ='cancel'

    @api.model
    def create(self, vals):
        patient_partner = self.env['res.partner'].create({'name': vals['first_name'],'phone' : vals['phone']})
        print('--------------------',self.env.user)
        if not vals.get('note'):
            vals['note'] = "New Patient"
        if vals.get('name',('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hospital.patient') or _('New')
        # if not vals.get('email'):
        #     vals['email'] = ("%s@gmail.com" % self.name)
        res = super(HospitalPatient,self).create(vals)
        res.partner_id = patient_partner.id
        return res

    def write(self,vals):
        self.ensure_one()
        res = super(HospitalPatient,self).write(vals)
        print("-----------test done")
        return res


    def print_report(self):
        data = {
        'from_date': self.from_date,
        'to_date': self.to_date,
        }
        return self.env.ref('module_name.action_student_id_card').report_action(None, data=data)

    @api.model
    def default_get(self, fields):
        res = super(HospitalPatient,self).default_get(fields)
        res['Gender'] = 'female'
        return res
    
    # def name_get(self):
    #     res = []
    #     for rec in self:
    #         name = rec.referance + ' ' + rec.name
    #         res.append((rec.id,name))
    #     return res

    # def name_search(self, name='', args=None, operator='ilike', limit=100):
    #     if args is None:
    #         args = []
    #     domain = args + ['|',('referance',operator,name),('name',operator,name)]
    #     return super(HospitalPatient, self).search(domain, limit=limit).name_get()


    def action_open_appointment(self):
        return {
            'name' : 'Appoitments',
            'type' : 'ir.actions.act_window',
            'view_mode' : 'tree,form',
            'res_model' : 'hospital.appoinment',
            'target' : 'current',
            'domain' : [('patient_id','=',self.id)],
            'context' : {'default_patient_id' : self.id},
        }

    def send_msg(self):
        return {'type': 'ir.actions.act_window',
                'name': _('Whatsapp Message'),
                'res_model': 'whatsapp.msg.wizard',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_user_id': self.id},
                }

    def action_open_document(self):
        document = self.env['patient.attachment'].search([
            ('res_id', '=', self.id), ('res_model', '=', 'hospital.patient')])

        return {
        'name' : 'Documents',
        'view_type' : 'form',
        'view_mode' : 'tree,form',
        'res_model' : 'patient.attachment',
        'target' : 'current',
        'type': 'ir.actions.act_window',
        'domain': [('id', 'in', document.ids)],
        'res_ids' : document.ids
        }

