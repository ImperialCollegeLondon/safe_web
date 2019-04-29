import os
from gluon import current

# -----------------------------------------------------------------------------
# DATASETS
# - holds information on uploaded datasets
# - supports versioning:
#    - a new upload gets a unique id number ('dataset_id')
#    - that id is used as the key for the submit dataset webpage
#    - if the page URL is called with a dataset id as a parameter
#      then changes generate a new record sharing the parent id
#    - Once a dataset is published then changes will inherit the
#      Zenodo concept record DOI and may then gain a new zenodo
#      specific DOI if published as a revision.
# - store the md5 hash for preventing uploads of identical files and for
#   comparison to the md5 output of files published to Zenodo.
# - datasets are stored in dataset_id specific folders, so versions
#   are packaged neatly on the local filesystem
# The dataset_id table is only used to provide a sequence of id values
# to group versions of datasets - it is basically just using the DB
# API to provide a sequence, because those aren't supported directly
# The project_datasets table provides the links between projects and
# datasets. One is created when the dataset is uploaded but others
# can be created, for example when projects are merged.
# -----------------------------------------------------------------------------

db.define_table('dataset_id',
                Field('created', 'datetime'))

db.define_table('datasets',
                # fields to handle the file upload and checking
                Field('dataset_id', 'reference dataset_id'),
                Field('version', 'integer', default=1),
                Field('current', 'boolean', default=True),
                Field('uploader_id', 'reference auth_user'),
                Field('project_id', 'reference project_id'),
                Field('file', 'upload',
                      uploadfolder=os.path.join(request.folder, 'uploads/datasets')),
                Field('file_name', 'string'),
                Field('file_hash', 'string'),
                Field('file_size', 'integer'),
                Field('upload_datetime', 'datetime'),
                # fields to handle the local formatting check
                Field('dataset_check_outcome', 'string', default="PENDING",
                      requires=IS_IN_SET(['PENDING', 'FAIL', 'ERROR', 'PASS'])),
                Field('dataset_check_error', 'text', default=''),
                Field('dataset_check_report', 'text', default=''),
                Field('dataset_title', 'text', default='Title not yet loaded'),
                Field('dataset_access', 'string'),
                Field('dataset_description', 'text'),
                Field('dataset_keywords', 'list:string'),
                Field('dataset_metadata', 'json'),
                Field('dataset_taxon_index', 'json'),
                Field('dataset_location_index', 'json'),
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
                Field('zenodo_version_badge', 'string', requires=IS_EMPTY_OR(IS_URL())),
                Field('geographic_extent', 'geometry()'),
                Field('temporal_extent_start', 'date'),
                Field('temporal_extent_end', 'date'))

db.define_table('project_datasets',
                Field('project_id', 'reference project_id', notnull=True),
                Field('dataset_id', 'reference dataset_id', notnull=True),
                Field('user_id', 'reference auth_user'),
                Field('date_added', 'date'))

# -----------------------------------------------------------------------------
# SAFE DATASET INDEX TABLE DEFINITIONS
# - these tables hold information about published datasets.
# - information is available for each published version 
#   (so datasets.id, not dataset_id.id)
# -----------------------------------------------------------------------------

db.define_table('dataset_taxa',
                Field('dataset_version_id', 'reference datasets'),
                Field('gbif_id', 'integer'),
                Field('gbif_parent_id', 'integer'),
                Field('taxon_name', 'string'),
                Field('taxon_rank', 'string'),
                Field('gbif_status', 'string'))

                                
db.define_table('dataset_locations',
                Field('dataset_version_id', 'reference datasets'),
                Field('name', 'string'),
                Field('new_location', 'boolean'),
                Field('type', 'string'),
                Field('wkt_wgs84', 'geometry()'),
                Field('wkt_utm50n', 'geometry(public, 32650, 2)'))


db.define_table('dataset_worksheets',
                Field('dataset_version_id', 'reference datasets'),
                Field('name', 'string'),
                Field('description', 'text'),
                Field('title', 'string'),
                Field('external', 'string'),
                Field('n_data_row', 'integer'),
                Field('max_col', 'integer'))


db.define_table('dataset_fields',
                Field('dataset_version_id', 'reference datasets'),
                Field('dataset_worksheet_id', 'reference dataset_worksheets'),
                Field('field_type', 'string'),
                Field('description', 'text'),
                Field('levels', 'text'),
                Field('units', 'string'),
                Field('taxon_name', 'string'),
                Field('taxon_field', 'string'),
                Field('interaction_field', 'string'),
                Field('interaction_name', 'string'),
                Field('method', 'text'),
                Field('field_name', 'string'))