import os
import html2text
import datetime
from gluon.contrib import simplejson

## -----------------------------------------------------------------------------
## PREDEFINED LISTS OF VALUES
## - Define some global items 
## -----------------------------------------------------------------------------

# ugly hacked inline style for more visible HR in panel-primary
local_hr = HR(_style='margin-top: 10px; margin-bottom: 0px; border: 0; border-top: 1px solid #325d88;')

n_beds_available = 25
bed_booking_capacity = 32
n_transfers_available = 4

project_roles = ['Lead Researcher', 'Supervisor', 'Co-supervisor', 'PhD Student',
                 'MSc Student', 'Undergraduate', 'PI', 'Co-I', 'Post Doc',
                 'Field Assistant', 'Malaysian Collaborator', 'Coordinator']

output_formats = ["Book Chapter", "Journal Paper", "Field Guide", "Poster", "Presentation",
                  "Masters Thesis", "PhD Thesis", "Video", "Report", "Other", 'Website']

volunteer_type = ['Voluntary experience', 'Undergraduate Honours project', 'Other']

research_tags = ["Water Resources", "Biodiversity", "Plant Science", "Zoology", "Ecology", 
                 "Freshwater Biology", "Agriculture", "Infectious Diseases", "Soil Science", 
                 "Meteorology and Atmospheric Science", "Biogeochemistry", "Microclimate", 
                 "Policy", "Other", "Riparian", "Invasive Species", "Education and training"]

vacancy_type = ['Technical Intern','Field Intern', 'Volunteer', 'Field Assistant', 'PhD Position', 'Other']

data_use_set = ['Undergraduate Project','Masters Project', 'PhD Thesis','Research Grant','Other']

project_status_set = ['Draft', 'Submitted', 'In Review', 'Approved', 'Resubmit']

admin_status_set = ['Pending', 'Rejected', 'Approved']

animal_groups = ['Oligochaetes (earthworms)', 'Hirudinea (leeches)', 
                 'Chelicerata (spiders, scorpions, and kin)', 
                 'Crustacea (crabs, shrimp, woodlice and kin)', 
                 'Hexapoda (insects, springtails and kin)', 
                 'Myriapoda (centipedes and millipedes)', 'Amphibia', 
                 'Mammalia (mammals)', 'Aves (birds)', 'Reptilia (reptiles)', 
                 'Osteichthyes (bony fish)', 'Bivalvia (mussels etc.)', 
                 'Gastropoda (snails and slugs)', 'Nematoda', 'Nematomorpha ', 
                 'Platyhelminthes (flatworms)', 'Rotifera (rotifers)', 
                 'Tardigrada (tardigrades)']

res_assist_set = ['All day at SAFE', 'Morning only at SAFE', 
                  'Afternoon only at SAFE', 'All day at Maliau', 
                  'Morning only at Maliau', 'Afternoon only at Maliau']

transfer_set = ['Tawau to SAFE', 'SAFE to Tawau', 'SAFE to Maliau', 'Maliau to SAFE', 
                'Maliau to Tawau', 'Tawau to Maliau', 'SAFE to Danum Valley', 'Danum Valley to SAFE']

## -----------------------------------------------------------------------------
## GLOBAL DEFINITION OF ICONS
## -----------------------------------------------------------------------------

approval_icons = {'Approved': SPAN('',_class="glyphicon glyphicon-ok-sign", 
                                      _style="color:green;font-size: 1.3em;", 
                                      _title='Approved'),
                  'Rejected': SPAN('',_class="glyphicon glyphicon-exclamation-sign", 
                                      _style="color:red;font-size: 1.3em;", 
                                      _title='Changes required'),
                  'Resubmit': SPAN('',_class="glyphicon glyphicon-exclamation-sign", 
                                      _style="color:red;font-size: 1.3em;", 
                                      _title='Changes required'),
                  'In Review':  SPAN('',_class="glyphicon glyphicon-eye-open",
                                      _style="color:orange;font-size: 1.3em;", 
                                      _title='In review'),
                  'Submitted':  SPAN('',_class="glyphicon glyphicon-question-sign",
                                      _style="color:orange;font-size: 1.3em;", 
                                      _title='Submitted'),
                  'Pending':  SPAN('',_class="glyphicon glyphicon-question-sign",
                                      _style="color:orange;font-size: 1.3em;", 
                                      _title='Pending'),
                  'Draft': SPAN('',_class="glyphicon glyphicon-pencil",
                                      _style="color:red;font-size: 1.3em;", 
                                      _title='Draft'),
                  'PASS':  SPAN('',_class="glyphicon glyphicon-ok-sign",
                                      _style="color:green;font-size: 1.3em;", 
                                      _title='Dataset check passed'),
                  'FAIL':  SPAN('',_class="glyphicon glyphicon-remove-sign",
                                      _style="color:orange;font-size: 1.3em;", 
                                      _title='Dataset check failed'),
                  'ERROR':  SPAN('',_class="glyphicon glyphicon-exclamation-sign",
                                      _style="color:red;font-size: 1.3em;", 
                                      _title='Dataset check error'),
                  'PENDING':  SPAN('',_class="glyphicon glyphicon-question-sign",
                                      _style="color:grey;font-size: 1.3em;", 
                                      _title='Dataset not yet checked'),
                  'ZEN_PEND':  SPAN('',_class="glyphicon glyphicon-question-sign",
                                      _style="color:grey;font-size: 1.3em;", 
                                      _title='Not yet submitted to Zenodo'),
                  'ZEN_PASS':  SPAN('',_class="glyphicon glyphicon-ok-sign",
                                      _style="color:green;font-size: 1.3em;", 
                                      _title='Published on Zenodo'),
                  'ZEN_FAIL':  SPAN('',_class="glyphicon glyphicon-exclamation-sign",
                                      _style="color:red;font-size: 1.3em;", 
                                      _title='Zenodo publication failed')}

coordinator_icon = SPAN('',_class="glyphicon glyphicon-ok",
                                      _style="color:grey;font-size: 1.3em;", 
                                      _title='Project Coordinator')

not_coordinator_icon = SPAN('',_class="glyphicon glyphicon-remove",
                               _style="color:grey;font-size: 1.3em;", 
                               _title='Not a Project Coordinator')

hs_ok = SPAN('',_class="glyphicon glyphicon-eye-open", 
               _style="color:green;font-size: 1.4em;", 
               _title='View H&S record')

hs_no = SPAN('',_class="glyphicon glyphicon-eye-close", 
                _style="color:red;font-size: 1.4em;", 
                _title='No H&S record')

remove_member_icon = SPAN('',_class="glyphicon glyphicon-minus-sign",
                             _style="color:red;font-size: 1.6em;padding: 0px 10px;", 
                             _title='Remove member')

add_member_icon = SPAN('',_class="glyphicon glyphicon-plus-sign",
                          _style="color:green;font-size: 1.6em;", 
                          _title='Add member')

# blog and news post visibility icons 

hide_glyph = SPAN('', _class="glyphicon glyphicon-eye-close")
visib_glyph = SPAN('', _class="glyphicon glyphicon-eye-open")
hide_style = "padding:3px 10px;background:darkred"
visib_style = "padding:3px 10px;background:darkgreen"

"""
SAFE TABLE DEFINITIONS

 ON EARTHCAPE INTEGRATION: 
 We'd prefer to use a single shared DB but the two applications use different 
 frameworks and some tables and fields would need to be called 
 something different in the this DB to allow Earthcape to read them.
 This would need use of the rname option to set the real DB name  
 and then the name used by web2py is an internal alias. This is a bit of
 a hack but Earthcape names require capitalisation, where web2py by
 default maps Field_Name to the standard SQL lowercase field_name. We'd also
 need to hand alter primary keys from the default btree on id, to include an
 EC compatible UUID field in the table primary key (id, "Oid"). 
 -     Field('oid', length=64, default=uuid.uuid4),
 We've explored this in some depth and it just engineers in more fragility 
 than is worthwhile to avoid. Commit d6b93a3 is tagged as the last version 
 containing this integration code, which has now been stripped back out to 
 reduce processing complexity.
"""



"""
CONTACTS - a simple table to map users to contacts roles
"""

db.define_table('contacts',
    Field('user_id', 'reference auth_user'),
    Field('contacts_group', 'string', 
          requires=IS_IN_SET(['Management Team', 'Science Advisory Committee',
                              'Malaysian Collaborators','Field Team'])),
    Field('contacts_role', 'string'))

"""
PROJECTS:
 -- Four tables:
    * a permanent table of IDs, matching a project number to version details and 
      containing project info applying  to all versions
    * a table of project details, which can contain new and old versions. As 
      users edit or update a project, the approval process updates the linked
      version on the project_id table
    * a table that matches members to project id
    * a table that links related projects
 -- Populated from fixtures file
 -- 'legacy_project_id': used only to match in links when loading old website data
 -- 'legacy_sampling_scales' and 'legacy_sampling_sites': in previous website but discarded 
"""

db.define_table('project_id', 
    Field('project_details_id', 'integer'),
    Field('merged_to', 'reference project_id', default=None))

db.define_table('project_details',
    Field('project_id', 'reference project_id'),
    Field('version', 'integer'),
    Field('thumbnail_figure','upload', uploadfolder= os.path.join(request.folder, 'uploads/images/projects')),
    Field('title','string', notnull=True),
    Field('research_areas', type='list:string',
          requires=IS_IN_SET(research_tags, multiple=True), 
          widget=SQLFORM.widgets.multiple.widget),
    Field('start_date','date', notnull=True),
    Field('end_date','date', notnull=True),
    Field('data_use', type='list:string', 
          requires=IS_IN_SET(data_use_set, multiple=True),
          widget = SQLFORM.widgets.checkboxes.widget),
    Field('rationale','text', notnull=True),
    Field('methods','text', notnull=True),
    Field('destructive_sampling', 'boolean', default=False),
    Field('destructive_sampling_info', 'text'),
    Field('which_animal_taxa', type='list:string',
          requires=IS_IN_SET(animal_groups, multiple=True), 
          widget=SQLFORM.widgets.multiple.widget),
    Field('ethics_approval_required', 'boolean', default=False),
    Field('ethics_approval_details', 'text'),
    Field('funding', 'string'),
    # this next field basically has to be set to be True in code 
    # before a project can be submitted
    Field('data_sharing','boolean', default=False),
    # this allows us to link project pages on import
    Field('legacy_project_id', 'string', readable = False, writable = False),
    # proposer id and date
    Field('proposer_id','reference auth_user'),
    Field('proposal_date','datetime'),
    # The fields below are to handle approval of new records
    # - admin_history is used to maintain a record of proposal processing
    Field('admin_status','string', requires=IS_IN_SET(project_status_set), default='Pending'), 
    Field('admin_history','text', writable=False), 
    # set the way the row is represented in foreign tables
    format='%(title)s') 

db.define_table('project_members',
    Field('project_id', 'reference project_id', notnull=True),
    Field('user_id', 'reference auth_user', notnull=True),
    Field('project_role', requires=IS_IN_SET(project_roles), notnull=True),
    Field('is_coordinator','boolean', notnull=True, default=False))


db.define_table('project_links',
    Field('user_id', 'reference auth_user', notnull=True),
    Field('link_date','date'))

db.define_table('project_link_pairs',
    Field('link_id', 'reference project_links', notnull=True),
    Field('project_id', 'reference project_id'))

## -----------------------------------------------------------------------------
## OUTPUTS
## -- populated from fixtures file
## -- 'legacy_output_id': used only to match in links when loading old website data
## -----------------------------------------------------------------------------


db.define_table('outputs',
    Field('thumbnail_figure','upload', uploadfolder= request.folder+'/uploads/images/outputs'),
    Field('file','upload', uploadfolder= request.folder+'/uploads/files/outputs'),
    Field('title','string', notnull=True),
    Field('abstract','text', notnull=True),
    Field('lay_summary','text'),
    Field('format','string', requires=IS_IN_SET(output_formats), notnull=True),
    Field('citation','string', length=1024),
    Field('doi','string', requires=IS_EMPTY_OR(IS_URL())),
    Field('url','string', requires=IS_EMPTY_OR(IS_URL())),
    Field('legacy_output_id', 'integer'), 
    # creator id and date
    Field('user_id','reference auth_user'),
    Field('submission_date','date'),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
    Field('admin_history','text'),
    format='%(title)s') # set the way the row is represented in foreign tables


db.define_table('project_outputs',
    Field('project_id', 'reference project_id', notnull=True),
    Field('output_id', 'reference outputs', notnull=True),
    Field('user_id','reference auth_user'),
    Field('date_added','date'))

## -----------------------------------------------------------------------------
## DATASETS 
## - holds information on uploaded datasets
## - supports versioning: 
##    - a new upload gets a unique id number ('dataset_id')
##    - that id is used as the key for the submit dataset webpage
##    - if the page URL is called with a dataset id as a parameter
##      then changes generate a new record sharing the parent id
##    - Once a dataset is published then changes will inherit the
##      Zenodo concept record DOI and may then gain a new zenodo 
##      specific DOI if published as a revision.
## - store the md5 hash for preventing uploads of identical files and for
##   comparison to the md5 output of files published to Zenodo.
## - datasets are stored in dataset_id specific folders, so versions
##   are packaged neatly on the local filesystem
##
## The dataset_id table is only used to provide a sequence of id values
## to group versions of datasets - it is basically just using the DB
## API to provide a sequence, because those aren't supported directly
##
## The project_datasets table provides the links between projects and
## datasets. One is created when the dataset is uploaded but others
## can be created, for example when projects are merged.
##
## -----------------------------------------------------------------------------

db.define_table('dataset_id',
                Field('created', 'datetime'))

db.define_table('datasets',
    # fields to handle the file upload and checking
    Field('dataset_id', 'reference dataset_id'),
    Field('version', 'integer', default=1),
    Field('current', 'boolean', default=True),
    Field('uploader_id', 'reference auth_user'),
    Field('project_id', 'reference project_id'),
    Field('file','upload',
          uploadfolder= os.path.join(request.folder, 'uploads/datasets')),
    Field('file_name', 'string'),
    Field('file_hash', 'string'), 
    Field('file_size', 'integer'),
    Field('upload_datetime','datetime'),
    # fields to handle the local formatting check
    Field('dataset_check_outcome','string', default="PENDING", 
          requires=IS_IN_SET(['PENDING', 'FAIL', 'ERROR','PASS'])),
    Field('dataset_check_error','text', default=''),
    Field('dataset_check_report','text', default=''),
    Field('dataset_title', 'text', default='Title not yet loaded'),
    Field('dataset_metadata', 'json'),
    Field('dataset_taxon_index', 'json'),
    Field('dataset_locations', 'json'),
    # fields to handle zenodo publication - most data is stored in
    # the metadata field as JSON, but for quick recall, a few are store
    # directly.
    Field('zenodo_submission_date', 'datetime'),
    Field('zenodo_submission_status', 'string', default="ZEN_PEND",
          requires=IS_IN_SET(['ZEN_PEND', 'ZEN_FAIL', 'ZEN_PASS'])),
    Field('zenodo_error', 'json'), 
    Field('zenodo_metadata', 'json'),
    Field('zenodo_record_id', 'integer'),
    Field('zenodo_parent_id', 'integer'),
    Field('zenodo_concept_doi', 'string', requires=IS_EMPTY_OR(IS_URL())),
    Field('zenodo_concept_badge', 'string', requires=IS_EMPTY_OR(IS_URL())),
    Field('zenodo_version_doi', 'string', requires=IS_EMPTY_OR(IS_URL())),
    Field('zenodo_version_badge', 'string', requires=IS_EMPTY_OR(IS_URL())))

db.define_table('project_datasets',
    Field('project_id', 'reference project_id', notnull=True),
    Field('dataset_id', 'reference dataset_id', notnull=True),
    Field('user_id','reference auth_user'),
    Field('date_added','date'))

## -----------------------------------------------------------------------------
## GAZETTEER
## - Two tables: one holds the set of recognized locations and the other holds
##   aliases for each location.
## -----------------------------------------------------------------------------

"""
display_order	order to add to leaflet map to make sure nothing gets masked by 
				overlying polygons etc.
				SAFE fragments (1) > carbon plots (2) > TART quadrats (3) >
				Carbon subplots (4) > Polylines (5) > all points (6)
fractal_order	only for SAFE Points
transect_order	only_for SAFE Points
"""

gaz_regions = ['SAFE', 'Maliau', 'Danum']
geom_types = ["MultiPolygon", "Point", "Polygon", "LineString"]

db.define_table('gazetteer',
    Field('location', 'string', unique=True),
    Field('type', 'string'),
    Field('parent', 'string'),
    Field('display_order', 'integer'),
    Field('region','string', requires=IS_IN_SET(gaz_regions)),
    Field('plot_size', 'string'),
    Field('fractal_order', 'integer'),
    Field('transect_order', 'integer'),
    Field('centroid_x', 'float'),
    Field('centroid_y', 'float'),
    Field('bbox_xmin', 'float'),
    Field('bbox_xmax', 'float'),
    Field('bbox_ymin', 'float'),
    Field('bbox_ymax', 'float'),
    Field('geom_type', 'string', requires=IS_IN_SET(geom_types)),
    Field('geom_coords', 'json'),
    Field('source', 'text'))

# Load the gazetteer types directly from the database. Typically this is bulk updated
# as sites are added, so synchronizing the list of types here is fragile. Instead, 
# set the requirement using the available data once the table has been declared.
gaz_types = [r.type for r in db().select(db.gazetteer.type, distinct=True)]
db.gazetteer.type.requires = IS_IN_SET(gaz_types)

# Aliases location names - cannot use a value already in the gazeetteer locations
db.define_table('gazetteer_alias',
    Field('location', 'string', requires=IS_IN_DB(db, 'gazetteer.locations')),
    Field('location_alias', 'string', requires=IS_NOT_IN_DB(db, 'gazetteer.locations'), unique=True))

## -----------------------------------------------------------------------------
## MARKET PLACE
## -----------------------------------------------------------------------------


db.define_table('help_offered',
    Field('user_id', 'reference auth_user'),
    Field('submission_date','date'),
    Field('volunteer_type', requires=IS_IN_SET(volunteer_type), notnull=True),
    Field('available_from','date', notnull=True),
    Field('available_to','date', notnull=True),
    Field('research_areas', type='list:string',
          requires=IS_IN_SET(research_tags, multiple=True), 
          widget=SQLFORM.widgets.multiple.widget),
    Field('statement_of_interests','text', notnull=True),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Submitted'), 
    Field('admin_history','text'))

db.define_table('help_request',
    Field('user_id', 'reference auth_user', notnull=True),
    Field('project_id', 'reference project_id', notnull=True),
    Field('submission_date','date'),
    Field('start_date','date', notnull=True),
    Field('end_date','date', notnull=True),
    Field('work_description','text', notnull=True),
    Field('vacancy_type', requires=IS_IN_SET(vacancy_type), notnull=True, default='Other'),
    Field('paid_position','boolean', notnull=True, default=False),
    Field('url', 'string',requires = IS_NULL_OR(IS_URL())),
    Field('available', 'boolean', default=False),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Submitted'), 
    Field('admin_history','text'))

## -----------------------------------------------------------------------------
## VISITS
## - 1) A description of the RV.
## - 2) A list of research visit members (RVM)
## - 3) Tables matching beds, transfers to RVM and research assistant suppor to RV
##
## Note - all RVs are reviewed and approved at the level of research visit not at
##        the level of individual components 
## -----------------------------------------------------------------------------

db.define_table('research_visit',
    Field('project_id', 'reference project_id'), # can be null for look see visits
    Field('title', 'string', notnull=True),
    Field('arrival_date','date', notnull=True),
    Field('departure_date','date', notnull=True),
    Field('purpose','text', notnull=True),
    Field('licence_details', 'string'),
    # The fields below identify who made the reservation and when
    Field('proposer_id', 'reference auth_user'),
    Field('proposal_date', 'date'),
    # The fields below are to handle approval of new records
    Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Draft'), 
    Field('admin_notes','text'),
    Field('admin_history','text'))

# this defines a list of people who are attending a research visit
# - note that user_id can be NULL for unknown visitors and can be
#   switched to change the user associated with a set of bookings
db.define_table('research_visit_member',
    Field('research_visit_id', 'reference research_visit', notnull=True),
    Field('user_id', 'reference auth_user'))

# the following tables links back to the row in research visit member

db.define_table('bed_reservations_safe',
    Field('research_visit_id', 'reference research_visit'),
    Field('research_visit_member_id', 'reference research_visit_member'), # 
    Field('arrival_date','date', notnull=True),
    Field('departure_date','date', notnull=True))

db.define_table('bed_reservations_maliau',
    Field('research_visit_id', 'reference research_visit'),
    Field('research_visit_member_id', 'reference research_visit_member'), # 
    Field('arrival_date','date', notnull=True),
    Field('departure_date','date', notnull=True),
    Field('type', 'string', requires=IS_IN_SET(['Hostel','Annex']), default='Annex'),
    Field('breakfast', 'boolean', default=False),
    Field('lunch', 'boolean', default=False),
    Field('dinner', 'boolean', default=False))

db.define_table('transfers',
    Field('transfer', 'string', requires=IS_IN_SET(transfer_set)),
    Field('research_visit_id', 'reference research_visit'),
    Field('research_visit_member_id', 'reference research_visit_member'), # 
    Field('transfer_date','date', notnull=True))

db.define_table('research_assistant_bookings',
    Field('research_visit_id', 'reference research_visit'),
    Field('start_date','date', notnull=True),
    Field('finish_date','date', notnull=True),
    Field('site_time','string', requires=IS_IN_SET(res_assist_set)),
    Field('work_type', 'string', requires=IS_IN_SET(['Standard', 'Rope work','Night work'])))

## -----------------------------------------------------------------------------
## H & S
## -- visitor details and health and safety at user level
## -- full H&S for all named users for now.
## -- putting notnull means that you can only update everything in a oner
## -----------------------------------------------------------------------------

db.define_table('health_and_safety',
    Field('user_id', 'reference auth_user'),
    Field('passport_number', 'string'),
    Field('emergency_contact_name', 'string'),
    Field('emergency_contact_address', 'text'),
    Field('emergency_contact_phone', 'string'),
    Field('emergency_contact_email', 'string', requires=IS_NULL_OR(IS_EMAIL())),
    Field('insurance_company', 'string'),
    Field('insurance_emergency_phone', 'string'),
    Field('insurance_policy_number', 'string'),
    Field('medical_conditions', 'text'),
    Field('date_last_edited', 'date'),
    #Field('sbc_access_licence', 'string'),
    #Field('local_collaborator', 'reference auth_user')
    )


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
    Field('gbif_link', 'string', requires=IS_NULL_OR(IS_URL())),
    Field('updated_by', 'reference auth_user'),
    Field('updated_on', 'date'))

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
                Field('user_id', 'reference auth_user'),
                Field('date_posted', 'date'),
                # The fields below are to handle approval of new records
                Field('admin_status','string', requires=IS_IN_SET(admin_status_set), default='Pending'), 
                Field('admin_history','text'),
                Field('hidden','boolean', default=False))


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
                Field('date_posted', 'date'),
                Field('admin_history','text'),
                Field('hidden', 'boolean', default = False))

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)

## -----------------------------------------------------------------------------
## Group membership requests
## -- Could do this via the existing appadmin interface but need a mechanism
# 
##    for users to request group membership
## -----------------------------------------------------------------------------

db.define_table('group_request',
                Field('user_id', 'reference auth_user'),
                Field('group_id', 'reference auth_group'),
                Field('justification', 'string'),
                # The fields below are to handle approval of new records
                Field('admin_status','string', 
                      requires=IS_IN_SET(admin_status_set),
                      default='Pending'), 
                Field('admin_id','reference auth_user'),
                Field('admin_decision_date','date'))

## -----------------------------------------------------------------------------
## Discussion board
## -- Simple, single board discussion group
## -----------------------------------------------------------------------------

db.define_table('discussion_topics',
                Field('topic', 'string'),
                Field('topic_user_id', 'reference auth_user'),
                Field('topic_date','date'),
                Field('n_views', 'integer'),
                Field('n_messages', 'integer'))

db.define_table('discussion_message',
                Field('parent_id', 'integer'),
                Field('depth', 'integer'),
                Field('topic_id', 'reference discussion_topics'),
                Field('message','text'),
                Field('message_user_id', 'reference auth_user'),
                Field('message_date','datetime'))

db.discussion_message.parent_id.requires=IS_NULL_OR(IS_IN_DB(db, 'discussion_message.id'))

## -----------------------------------------------------------------------------
## Email log
## - db table just to record who got emailed what and when. Doesn't record message
##   content since these emails are all from templates - record the template and
##   the dictionary of info used to fill out the template to save bits.
## -----------------------------------------------------------------------------

db.define_table('safe_web_email_log',
                Field('subject', 'string'),
                Field('email_to', 'text'),
                Field('email_cc', 'text'),
                Field('email_bcc', 'text'),
                Field('reply_to', 'text'),
                Field('template','string'),
                Field('template_dict','json'),
                Field('status', 'string'),
                Field('message_date','datetime'))

## -----------------------------------------------------------------------------
## Ancilliary tables to support website
## -----------------------------------------------------------------------------

# - this table is used to provide an admin editable list of dates
#   to highlight in datepickers 
db.define_table('public_holidays',
                Field('date','date'),
                Field('title','string'))
