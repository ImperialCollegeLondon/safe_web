# -*- coding: utf-8 -*-

## ----------------------------------------------------------------------------
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
## ----------------------------------------------------------------------------

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

## app configuration made easy. Look inside private/appconfig.ini
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Recaptcha


## once in production, remove reload=True to gain full speed
myconf = AppConfig(reload=True)


if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    
    # ### postgres External
    # postgres_connection = 'postgres://safe_admin:Safe2016@earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com/safe16'
    # db = DAL(postgres_connection, migrate_enabled=False) #, lazy_tables=True)
    #
    # ### MSSQL EXTERNAL
    # external_db_config = dict(usr = 'earthcape',
    #                           pwd = 'Apollo1978',
    #                           srv = 'dgby1qwd2n.database.windows.net',
    #                           db  = 'SAFE15',
    #                           knd = 'mssql',
    #                           drv = 'FreeTDS',
    #                           prt = 1433,
    #                           dsn = 'earthcape')
    # mssql_str = '{knd}://{usr}:{pwd}@{srv}/{db}?DRIVER={{{drv}}}'
    # # alternative connection strings found on web, none of which work
    # # mssql_str = '{knd}://{usr}:{pwd}@{srv}/{db}'
    # # mssql_str = '{knd}://DRIVER={{{drv}};SERVER={srv}\{db},{prt};UID={usr};PWD={pwd}'
    # db = DAL(mssql_str.format(**external_db_config), migrate_enabled=False)
    
    # PG LOCAL setup
    # NOTE - needs to have a created database: 'createdb dbname'
    connection = "postgres://test:test@localhost/safe_web2py"
    
    # PG REMOTE setup
    # - this is a link to an AWS RDS instance, which could then be shared by Earthcape
    # connection = "postgres://safe_admin:Safe2016@earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com/safe_web2py"    
    
    # # MYSQL database on python_anywhere testing environment
    # connection = "mysql://DavidOrme:MonteCarloOrBust@DavidOrme.mysql.pythonanywhere-services.com/DavidOrme$safe_web2py"
    
    db = DAL(connection, lazy_tables=True, pool_size=5)
    
    
    # TODO - look at the myconf.take functionality and config file rather than hard coding
    # db = DAL(myconf.take('db.uri'), pool_size=myconf.take('db.pool_size', cast=int), check_reserved=['all'])
    
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore+ndb')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## choose a style for forms
response.formstyle = myconf.take('forms.formstyle')  # or 'bootstrap3_stacked' or 'bootstrap2' or other
response.form_label_separator = myconf.take('forms.separator')

## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'
## (optional) static assets folder versioning
# response.static_version = '0.0.0'

## ----------------------------------------------------------------------------
## ENABLE AUTH
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## ----------------------------------------------------------------------------

from gluon.tools import Auth #, Service, PluginManager

auth = Auth(db)
# service = Service()
# plugins = PluginManager()


## -----------------------------------------------------------------------------
## EXTEND THE USER TABLE DEFINITION
## -- defaults are: first_name, last_name, email, password
##                  registration_key, reset_password_key, registration_id
## -- legacy_user_id is purely for matching up imported users
## -- integrate ORCid login
## -- TODO - phone number formatting
## -- TODO - enforcing not null - problematic with upload of legacy users
## -----------------------------------------------------------------------------

academic_status_set = ['Undergraduate', 'Masters Student',
                       'PhD Student', 'Postdoc', 'Research Fellow', 'Faculty',
                       'Volunteer', 'Other', 'SAFE Research Assistant']

titles_set = [None, 'Dr','Prof', 'Assist. Prof', 'Assoc. Prof']

auth.settings.extra_fields['auth_user']= [
    Field('title', 'string', requires=IS_IN_SET(titles_set)), 
    Field('nationality', 'string'),
    Field('academic_status', 'string', requires=IS_IN_SET(academic_status_set)),
    Field('orcid', 'string'),
    Field('phone', 'string'),
    Field('mobile_phone', 'string'),
    Field('alternative_email', 'string', requires=IS_EMPTY_OR(IS_EMAIL())),
    Field('institution', 'string'),
    Field('institution_address', 'string'),
    Field('institution_phone', 'string'),
    Field('supervisor_id', 'reference auth_user'),
    Field('legacy_user_id','integer'),
    Field('h_and_s_id', 'integer')]

## create auth tables 
auth.define_tables(username=False, signature=False)

## suppress the legacy_user_id field as a general rule
db.auth_user.legacy_user_id.readable = False
db.auth_user.legacy_user_id.writable = False

# set a string formatting for representing user ID
db.auth_user._format = '%(last_name)s, %(first_name)s'

## configure auth policies
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = True
auth.settings.reset_password_requires_verification = True

# 
#auth.settings.on_failed_authentication = lambda url: redirect(url)

# TODO - turn on captcha for regiastration
# auth.settings.register_captcha = Recaptcha()

## -----------------------------------------------------------------------------
## CONFIGURE EMAIL ACCOUNT SETTINGS 
## -- TODO - change to some kind of project admin email
## -- TODO - implement email logging
## -----------------------------------------------------------------------------

mail = auth.settings.mailer

# # testing from imperial account
# mail.settings.server = 'smtp.cc.ic.ac.uk:25' # 'logging' if request.is_local else myconf.take('smtp.server')
# mail.settings.sender = 'd.orme@imperial.ac.uk'
# mail.settings.login = 'dorme:notactuallymypassword'

# use the hostgator SMTP server
mail.settings.server = 'gator4079.hostgator.com:465'
mail.settings.sender = 'info@safeproject.net'
mail.settings.login = 'info@safeproject.net:info654='
mail.settings.ssl = True

## -----------------------------------------------------------------------------
## SAFE TABLE DEFINITIONS
## -- TODO - look at UUIDs in definitions for integration with EarthCape
##           UUIDs - enable UUID in postgresql
##           CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
##           uuid_generate_v4()
## -----------------------------------------------------------------------------

## -----------------------------------------------------------------------------
## IMPORT the CKEDITOR PLUGIN TO GIVE A WYSIWYG EDITOR FOR BLOGS AND NEWS
## -----------------------------------------------------------------------------

from plugin_ckeditor import CKEditor
ckeditor = CKEditor(db)
ckeditor.define_tables()

## -----------------------------------------------------------------------------
## RCUK PROJECT SUBJECT TAGS
## Populated by fixtures file
## TODO - cut this giant list down to relevant ones
## TODO - rethink implementation
## -----------------------------------------------------------------------------

db.define_table('rcuk_tags',
    Field('level', 'integer', notnull=True),
    Field('subject', 'string'),
    Field('topic', 'string'),
    Field('tag',  'string', notnull=True))


## -----------------------------------------------------------------------------
## -- USERS RESEARCH TAGS
## -----------------------------------------------------------------------------

# db.define_table('user_tags',
#     Field('user_id', 'reference auth_user'),
#     Field('tag_id', 'reference rcuk_tags'))

## -----------------------------------------------------------------------------
## PROJECTS:
## -- A table of the projects and then a table of members
## -- Populated from fixtures file
## -- 'legacy_project_id': used only to match in links when loading old website data
## -- TODO - think about use of list:string - they are a bit fugly but they do save tables
## -- TODO - consider moving 'data_sharing' to a T&C link extra (Manual p370)
## -----------------------------------------------------------------------------

# define some sets for controlled fields

sites_set = ['Old growth controls', 'Logged forest controls',
             'Logged forest edge','Virgin Jungle Reserve',
             'Fragments block A','Fragments block B',
             'Fragments block C','Fragments block D',
             'Fragments block E', 'Fragments block F',
             'Oil palm control','Riparian strips','Other']

spatial_scales_set = ['First order', 'Second order', 'Third order', 'Fourth order', 'Other']

admin_status_set = ['Pending', 'Approved', 'Rejected']

# define table
# - TODO - work out how to get represemntation to link to project pages
db.define_table('project',
    Field('picture','upload', uploadfolder= request.folder+'/uploads/images/projects'),
    Field('title','string', notnull=True,
          # represent = lambda value, row: A(row.title, _href='www.google.co.uk')
          ),
    Field('project_home_country','string', notnull=True,
          requires=IS_IN_SET(['Malaysian', 'International'])),
    Field('sampling_sites', type='list:string', 
          requires=IS_IN_SET(sites_set, multiple=True), 
          widget=SQLFORM.widgets.checkboxes.widget),
    Field('sampling_scales', type='list:string', 
          requires=IS_IN_SET(spatial_scales_set, multiple=True), 
          widget=SQLFORM.widgets.checkboxes.widget),
    Field('research_areas', type='list:string',
          requires=IS_IN_DB(db, db.rcuk_tags.id, '%(tag)s', multiple=True), 
          widget=SQLFORM.widgets.multiple.widget),
    Field('start_date','date', notnull=True),
    Field('end_date','date', notnull=True),
    Field('rationale','text', notnull=True),
    Field('methods','text', notnull=True),
    Field('requires_ra','boolean', notnull=True, default=False),
    Field('requires_vehicle','boolean', notnull=True, default=False),
    Field('resource_notes','string'),
    Field('legacy_project_id', 'integer'), 
    Field('data_sharing','boolean', notnull=True),
    # proposer id and date
    Field('proposer_id','reference auth_user'),
    Field('proposal_date','date'),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
    Field('admin_id','reference auth_user'),
    Field('admin_notes','text'),
    Field('admin_decision_date','date'),
    # set the way the row is represented in foreign tables
    format='%(title)s'
    ) 

## suppress the legacy_user_id field as a general rule
db.project.legacy_project_id.readable = False
db.project.legacy_project_id.writable = False


## -----------------------------------------------------------------------------
## PROJECT RESEARCH TAGS
## -----------------------------------------------------------------------------

# db.define_table('project',
#     Field('project_id', 'reference project'),
#     Field('tag_id', 'reference rcuk_tags'))

## -----------------------------------------------------------------------------
## PROJECT MEMBERS AND THEIR ROLES
## -- populated from fixtures file
## -----------------------------------------------------------------------------

project_roles = ['Main Contact', 'Supervisor', 'Co-supervisor', 'PhD student', 
                 'MSc student', 'PI', 'Co-I', 'Field Assistant', 'Malaysian Collaborator']

db.define_table('project_members',
    Field('project_id', 'reference project', notnull=True),
    Field('user_id', 'reference auth_user', notnull=True),
    Field('project_role', requires=IS_IN_SET(project_roles), notnull=True))

## -----------------------------------------------------------------------------
## OUTPUTS
## -- populated from fixtures file
## -- 'legacy_output_id': used only to match in links when loading old website data
## -----------------------------------------------------------------------------

formats = ["Book Chapter", "Journal Paper", "Other", "Poster", "Presentation", "MSc Thesis", "PhD Thesis"]

db.define_table('outputs',
    Field('picture','upload', uploadfolder= request.folder+'/uploads/images/outputs'),
    Field('file','upload', uploadfolder= request.folder+'/uploads/files/outputs'),
    Field('title','string', notnull=True),
    Field('description','text', notnull=True),
    Field('format','string', requires=IS_IN_SET(formats), notnull=True),
    Field('citation','string', length=1024),
    Field('doi','string', requires=IS_EMPTY_OR(IS_URL())),
    Field('url','string', requires=IS_EMPTY_OR(IS_URL())),
    Field('legacy_output_id', 'integer'), 
    # creator id and date
    Field('creator_id','reference auth_user'),
    Field('submission_date','date'),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
    Field('admin_id','reference auth_user'),
    Field('admin_notes','text'),
    Field('admin_decision_date','date'),
    format='%(title)s') # set the way the row is represented in foreign tables

# not sure about this - can fall back to a single owner
# but want to be able to flag multiple members, perhaps mostly
# just for the MY_SAFE page
db.define_table('output_members',
    Field('output_id', 'reference outputs', notnull=True),
    Field('user_id', 'reference auth_user', notnull=True))


db.define_table('project_outputs',
    Field('project_id', 'reference project', notnull=True),
    Field('output_id', 'reference outputs', notnull=True),
    Field('added_by', 'reference auth_user', notnull=True),
    Field('date_added', 'date', notnull=True))


## -----------------------------------------------------------------------------
## MARKET PLACE
## -----------------------------------------------------------------------------
#
volunteer_type = ['Voluntary experience', 'Undergraduate Honours project', 'Masters project']

db.define_table('help_offered',
    Field('volunteer_id', 'reference auth_user'),
    Field('submission_date','date'),
    Field('volunteer_type', requires=IS_IN_SET(volunteer_type), notnull=True),
    Field('available_from','date', notnull=True),
    Field('available_to','date', notnull=True),
    Field('research_statement','text', notnull=True),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
    Field('admin_id','reference auth_user'),
    Field('admin_notes','text'),
    Field('admin_decision_date','date'))

db.define_table('help_request',
    Field('contact_id', 'reference auth_user', notnull=True),
    Field('project_id', 'reference project', notnull=True),
    Field('submission_date','date'),
    Field('start_date','date', notnull=True),
    Field('end_date','date', notnull=True),
    Field('work_description','text', notnull=True),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
    Field('admin_id','reference auth_user'),
    Field('admin_notes','text'),
    Field('admin_decision_date','date'))

## -----------------------------------------------------------------------------
## VISITS
## - two classes of thing:
##   1) approval of a bed reservation to stay at SAFE. Can be entirely unassociated
##      with a research visit for a project for look-see type bookings
##   2) a booking for people working on an existing approved visit
## -----------------------------------------------------------------------------

# not sure where to put global variable definitions!
n_beds_available = 25

db.define_table('research_visit',
    Field('project_id', 'reference project', notnull=True),
    Field('title', 'string', notnull=True),
    Field('arrival_date','date', notnull=True),
    Field('departure_date','date', notnull=True),
    Field('purpose','text', notnull=True),
    Field('licence_details', 'string'),
    # The fields below identify who made the reservation and when
    Field('proposer_id', 'reference auth_user'),
    Field('proposal_date', 'date'),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
    Field('admin_id','reference auth_user'),
    Field('admin_notes','text'),
    Field('admin_decision_date','date'))


db.define_table('research_visit_member',
    Field('research_visit_id', 'reference research_visit', notnull=True),
    Field('user_id', 'reference auth_user', notnull=True))

# project and visit ID _can_ be null for look-see visits, so don't make them 
# a fixed 'reference' and let the controllers handle validation
# could limit number_of_visitors using  requires=IS_INT_IN_RANGE(1,n_beds_available)
# but let the controllers handle that, so we don't restrict admin bookings
db.define_table('bed_reservations',
    Field('research_visit_id', 'integer', requires=IS_EMPTY_OR(IS_IN_DB(db, db.research_visit.id, '%(title)s'))),
    Field('arrival_date','date', notnull=True),
    Field('departure_date','date', notnull=True),
    Field('number_of_visitors','integer', notnull=True),
    Field('purpose','text', notnull=True),
    Field('look_see_visit','boolean', notnull=True, default=False),
    # The fields below identify who made the reservation and when
    Field('reserver_id', 'reference auth_user'),
    Field('reservation_date', 'date'),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
    Field('admin_id','reference auth_user'),
    Field('admin_notes','text'),
    Field('admin_decision_date','date'))


db.define_table('bed_reservation_member',
    Field('bed_reservation_id', 'reference bed_reservations', notnull=True),
    Field('user_id', 'reference auth_user', notnull=True))


# this table is used internally to keep track of available beds
db.define_table('bed_data',
    Field('day','date'),
    Field('approved', 'integer'),
    Field('pending', 'integer'))


## -----------------------------------------------------------------------------
## H & S
## -- visitor details and health and safety at user level
## -- full H&S for all named users for now.
## -----------------------------------------------------------------------------

db.define_table('health_and_safety',
    Field('user_id', 'reference auth_user'),
    # Field('project_id', 'reference project'),
    # Field('visit_id', 'reference visit'),
    Field('passport_number', 'string', notnull=True),
    Field('emergency_contact_name', 'string', notnull=True),
    Field('emergency_contact_address', 'text', notnull=True),
    Field('emergency_contact_phone', 'string', notnull=True),
    Field('emergency_contact_email', 'string', requires=IS_EMAIL()),
    Field('insurance_company', 'string', notnull=True),
    Field('insurance_emergency_phone', 'string', notnull=True),
    Field('insurance_policy_number', 'string', notnull=True),
    Field('medical_conditions', 'text'),
    Field('date_last_edited', 'date'),
    #Field('sbc_access_licence', 'string'),
    #Field('local_collaborator', 'reference auth_user')
    )

# -- in order to book in a visit, may need to book RA time
#
# -- associate an RA with a booking
# -- TODO but this also needs to integrate with RA bookings for core research
# CREATE TABLE project_admin.research_associate_booking (
#     ra_booking_id SERIAL PRIMARY KEY,
#     visit_id integer reference project_admin.visit not null,
#     research_associate_id integer reference project_admin.user not null
# );
#
# -- create a trigger to check that Ewers, R has not been selected from the the user list?
#
#
# -- could create server side triggers to verify:
# --  * that an RA isn't booked
# --  * that the number of bunks is ok
#


## -----------------------------------------------------------------------------
## SPECIES PROFILES
## TODO - provide static photo upload
## -----------------------------------------------------------------------------

db.define_table('species_profile',
                Field('binomial', 'string'),
                Field('common_name', 'string'),
                Field('iucn_status', 'string', 
                      requires=IS_IN_SET(['Not Evaluated', 'Data Deficient', 'Least Concern', 'Near Threatened',
                                          'Vulnerable', 'Endangered', 'Critically Endangered','Extinct in the Wild', 'Extinct'])),
                Field('global_population', 'string',
                      requires=IS_IN_SET(['increasing', 'decreasing', 'unknown','stable'])),
                Field('local_abundance', 'string',
                      requires=IS_IN_SET(['commonly seen','often seen','sometimes seen','rarely seen'])),
                Field('in_primary', 'boolean'),
                Field('in_logged', 'boolean'),
                Field('in_plantation', 'boolean'),
                Field('animal_facts', 'text'),
                Field('where_do_they_live', 'text'),
                Field('habitat', 'text'),
                Field('what_do_they_eat', 'text'),
                Field('who_eats_them', 'text'),
                Field('threatened_by', 'text'),
                Field('image_link', 'string', requires=IS_NULL_OR(IS_URL())), # e.g. link to static flickr farm
                Field('image_href', 'string', requires=IS_NULL_OR(IS_URL())), # e.g. link to flickr user photo page 
                Field('image_title', 'string'),
                Field('google_scholar_link', 'string', requires=IS_NULL_OR(IS_URL())),
                Field('wikipedia_link', 'string', requires=IS_NULL_OR(IS_URL())),
                Field('eol_link', 'string', requires=IS_NULL_OR(IS_URL())),
                Field('iucn_link', 'string', requires=IS_NULL_OR(IS_URL())),
                Field('arkive_link', 'string', requires=IS_NULL_OR(IS_URL())),
                Field('gbif_link', 'string', requires=IS_NULL_OR(IS_URL())))


## -----------------------------------------------------------------------------
## CONTACTS
## - this is purely used to populate the contact table and to provide an admin
##   interface to maintaining it.
## -----------------------------------------------------------------------------

db.define_table('safe_contacts',
                Field('display_name', 'string'), # i.e. Title etc
                Field('contact_type', 'string', 
                      requires=IS_IN_SET(['Management Team', 'Science Advisory Committee',
                                          'Malaysian Collaborators','Field Team'])),
                Field('role', 'string'),
                Field('picture','upload', uploadfolder= request.folder+'/uploads/images/contacts'),
                Field('institution', 'string'),
                Field('address', 'string'),
                Field('email', 'string', requires=IS_NULL_OR(IS_EMAIL())),
                Field('website', 'string', requires=IS_NULL_OR(IS_URL())),
                Field('taxonomic_speciality', 'string'))
                

## -----------------------------------------------------------------------------
## BLOG
## -- a simple table to get blog posts into the website
## -----------------------------------------------------------------------------

db.define_table('blog_posts',
                Field('thumbnail_figure', 'upload', uploadfolder= request.folder+'/uploads/images/blog_thumbnails'),
                Field('authors', 'string'),
                Field('title', 'string'),
                Field('content', 'text', widget=ckeditor.widget),
                # who posted it and when
                Field('poster_id', 'reference auth_user'),
                Field('date_posted', 'date'),
                # The fields below are to handle approval of new records
                Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
                Field('admin_id','reference auth_user'),
                Field('admin_notes','text'),
                Field('admin_decision_date','date'))


## -----------------------------------------------------------------------------
## NEWS
## -- a simple table to hold news post contents
## -- these have to be posted by an admin, so no approval fields
## -- they don't have authors (although the poster is recorded)
## -----------------------------------------------------------------------------

db.define_table('news_posts',
                Field('thumbnail_figure', 'upload', uploadfolder= request.folder+'/uploads/images/news_thumbnails'),
                Field('title', 'string'),
                Field('content', 'text', widget=ckeditor.widget),
                # who posted it and when
                Field('poster_id', 'reference auth_user'),
                Field('date_posted', 'date'))

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)


