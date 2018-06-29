# -*- coding: utf-8 -*-
import os
from fs.osfs import OSFS

# ----------------------------------------------------------------------------
# File is released under public domain and you can use without limitations
# ----------------------------------------------------------------------------

# if SSL/HTTPS is properly configured and you want all HTTP requests to
# be redirected to HTTPS, uncomment the line below:
# request.requires_https()

# app configuration made easy. Look inside private/appconfig.ini
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Auth, Service
from gluon.tools import Recaptcha2
from gluon import current
from plugin_ckeditor import CKEditor

# LOAD THE CONFIG to get DB and mail settings. This file is not under
# version control, so can be different on production and development servers

# once in production, remove reload=True to gain full speed
myconf = AppConfig(reload=True)

# ----------------------------------------------------------------------------
# DB connection definitions
# -- both connections (local/remote) need to have a created database in order
#    to create and populate tables
# ----------------------------------------------------------------------------

# PG setup
db = DAL(myconf.take('db.uri'), pool_size=myconf.take('db.pool_size', cast=int), lazy_tables=False)

# by default give a view/generic.extension to all actions from localhost
# none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []

# choose a style for forms
response.formstyle = myconf.take('forms.formstyle')
response.form_label_separator = myconf.take('forms.separator')

# ----------------------------------------------------------------------------
# ENABLE AUTH
# - authentication (registration, login, logout, ... )
# - authorization (role based authorization)
# ----------------------------------------------------------------------------

auth = Auth(db)
service = Service()
# plugins = PluginManager()

# -----------------------------------------------------------------------------
# CONFIGURE EMAIL ACCOUNT SETTINGS 
# -----------------------------------------------------------------------------

mail = auth.settings.mailer

# use the hostgator SMTP server
mail.settings.server = myconf.take('smtp.server')
mail.settings.sender = myconf.take('smtp.sender')
mail.settings.login = myconf.take('smtp.login')
mail.settings.ssl = True

# Store db, conf and mail in the current object so they can be imported by modules
current.myconf = myconf
current.db = db
current.mail = mail

# -----------------------------------------------------------------------------
# EXTEND THE USER TABLE DEFINITION
# -- defaults are: first_name, last_name, email, password
#                  registration_key, reset_password_key, registration_id
# -- legacy_user_id is purely for matching up imported users
# -- integrate ORCid login
# -- TODO - phone number formatting
# -- TODO - enforcing not null - problematic with upload of legacy users
# -----------------------------------------------------------------------------

academic_status_set = ['Undergraduate', 'Masters Student',
                       'PhD Student', 'Postdoc', 'Research Fellow', 'Faculty',
                       'Volunteer', 'Other', 'SAFE Research Assistant']

titles_set = [None, 'Dr', 'Prof', 'Assist. Prof', 'Assoc. Prof']

auth.settings.extra_fields['auth_user'] = [
    Field('title', 'string', requires=IS_IN_SET(titles_set)),
    Field('nationality', 'string'),
    Field('malaysian_researcher', 'boolean', default=False),
    Field('academic_status', 'string', requires=IS_IN_SET(academic_status_set)),
    Field('supervisor_id', 'reference auth_user'),
    Field('institution', 'string'),
    Field('institution_address', 'string'),
    Field('institution_phone', 'string'),
    Field('phone', 'string'),
    Field('mobile_phone', 'string'),
    Field('alternative_email', 'string', requires=IS_EMPTY_OR(IS_EMAIL())),
    Field('orcid', 'string'),
    Field('website', 'string', requires=IS_EMPTY_OR(IS_URL())),
    Field('thumbnail_picture', 'upload',
          uploadfolder=request.folder + '/uploads/images/user_thumbnails'),
    Field('biography', 'text'),
    Field('scientific_expertise', type='string'),
    Field('legacy_user_id', 'integer'),
    Field('h_and_s_id', 'integer')]

# create auth tables 
auth.define_tables(username=False, signature=False)

# dont show the user the legacy user or H&S
db.auth_user.legacy_user_id.readable = False
db.auth_user.legacy_user_id.writable = False
db.auth_user.h_and_s_id.readable = False
db.auth_user.h_and_s_id.writable = False

# set a default image for the picture
db.auth_user.thumbnail_picture.default = os.path.join(request.folder, 'static',
                                                      'images/default_thumbnails/missing_person.png')

# turn user emails and websites into  links 
# and also make the user id show names for ease of use in impersonate
db.auth_user.email.represent = lambda value, row: A(value, _href='mailto:{}'.format(value))
db.auth_user.website.represent = lambda value, row: A(value, _href=value)

# provide links to user directory for logged in users
# set a string formatting for representing user ID
db.auth_user._format = '%(last_name)s, %(first_name)s'

# make the choice of supervisor a dropdown.
db.auth_user.supervisor_id.requires = IS_EMPTY_OR(IS_IN_DB(db, 'auth_user.id',
                                                           db.auth_user._format))

# # set the password hashing algorithm - now using default
# db.auth_user.password.requires = CRYPT(digest_alg='sha512')

# configure auth policies
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = True
auth.settings.reset_password_requires_verification = True

# send an email to the admin when new users register
auth.settings.register_onaccept.append(lambda form: mail.send(to='info@safeproject.net',
                                                              subject='New website registration',
                                                              message='A new user has registered '
                                                                      'at the website and needs '
                                                                      'approval.'))

# by default, web2py creates a group for each user - we don't want that
auth.settings.create_user_groups = False

# auth.settings.on_failed_authentication = lambda url: redirect(url)

# Turn on captcha for registration
if int(myconf.take('recaptcha.use')):
    auth.settings.captcha = Recaptcha2(request,
                                       myconf.take('recaptcha.site_key'),
                                       myconf.take('recaptcha.secret_key'))

# -----------------------------------------------------------------------------
# IMPORT the CKEDITOR PLUGIN TO GIVE A WYSIWYG EDITOR FOR BLOGS AND NEWS
# -- OK, so this editor is neat but one issue is that it dumps files into the 
#    root of uploads, which is messy
# -- Ordinarily, this would be controlled by the upload_folder setting but
#    this is hardcoded in the module. Could edit it there but you can also use
#    a fs object to provide a folder
# -- You'd think it might be possible to have multiple upload folders but
#    it turns out to be quite hard to switch the settings
# -----------------------------------------------------------------------------

ckeditor = CKEditor(db)

app_root = request.folder
app_root_fs = OSFS(app_root)

if not app_root_fs.exists('uploads/news_and_blogs/'):
    blog_fs = app_root_fs.makeopendir('uploads/news_and_blogs/')
else:
    blog_fs = app_root_fs.opendir('uploads/news_and_blogs/')

ckeditor.settings.uploadfs = blog_fs
ckeditor.settings.table_upload_name = 'ckeditor_uploads'
ckeditor.define_tables()
