import os
from gluon import current

# -----------------------------------------------------------------------------
# DATASETS
# - Hold information on uploaded datasets
# - Submitted datasets sit in submitteed_datasets and are checked out
# - Once they pass testing, publication moves the record to published_datasets
#
# - Supports versioning:
#    - New submission can be submitted with an existing Zenodo concept DOI
#      in order to match a new file onto an existing publication.

# - store the md5 hash for preventing uploads of identical files and for
#   comparison to the md5 output of files published to Zenodo.
# - datasets are stored in dataset_id specific folders, so versions
#   are packaged neatly on the local filesystem
# -----------------------------------------------------------------------------


# Holds a submitted dataset for checking. When published the record is moved 
# to the published datasets table, retaining the original submission ID to
# inform submitted_dataset_status.

db.define_table('submitted_datasets',
                # fields to handle the file upload and checking
                Field('uploader_id', 'reference auth_user'),
                Field('project_id', 'reference project_id'),
                Field('concept_id', 'string'), # match to existing concept doi
                Field('file', 'upload',
                      uploadfolder=os.path.join(request.folder, 'uploads', 'submitted_datasets'),
                      autodelete=True),
                Field('file_name', 'string'),
                Field('file_hash', 'string'),
                Field('file_size', 'integer'),
                Field('upload_datetime', 'datetime'),
                # fields to handle the local formatting check
                Field('dataset_check_outcome', 'string', default="PENDING",
                      requires=IS_IN_SET(['PENDING', 'FAIL', 'ERROR', 'PASS'])),
                Field('dataset_check_error', 'text', default=''),
                Field('dataset_check_report', 'text', default=''),
                # These two fields hold the outputs of dataset checking until the dataset is published
                Field('dataset_metadata', 'json'),
                Field('dataset_title', 'string'),
                # fields to handle publication outcome
                Field('zenodo_submission_status', 'string', default="ZEN_PEND",
                      requires=IS_IN_SET(['ZEN_PEND', 'ZEN_FAIL', 'ZEN_PASS'])),
                Field('zenodo_error', 'json'))

db.define_table('published_datasets',
                # fields to handle the file upload and checking
                Field('uploader_id', 'reference auth_user'),
                Field('upload_datetime', 'datetime'),
                # The next field not a reference to the submission row, which will be deleted 
                # on publication, but allows submission ids to be tracked after publication.
                Field('submission_id', 'integer'),
                Field('project_id', 'reference project_id'),
                # Fields to hold the dataset metadata
                Field('dataset_title', 'text'),
                Field('dataset_access', 'string'),
                Field('dataset_embargo', 'date'),
                Field('dataset_description', 'text'),
                Field('dataset_metadata', 'json'),
                # Fields to hold publication data - most data is stored in the metadata
                # field as JSON, but for quick recall, a few are stored directly.
                Field('most_recent', 'boolean'),                
                Field('publication_date', 'datetime'),
                Field('zenodo_metadata', 'json'),
                Field('zenodo_record_id', 'integer'),
                Field('zenodo_record_doi', 'string'),
                Field('zenodo_record_badge', 'string'),
                Field('zenodo_concept_id', 'integer'),
                Field('zenodo_concept_doi', 'string'),
                Field('zenodo_concept_badge', 'string'),
                Field('geographic_extent', 'geometry()'),
                Field('temporal_extent_start', 'date'),
                Field('temporal_extent_end', 'date'))

# Used to link project ids to zenodo concept_ids
db.define_table('project_datasets',
                Field('project_id', 'reference project_id', notnull=True),
                Field('concept_id', 'integer', requires=IS_IN_DB(db, db.published_datasets.zenodo_concept_id)),
                Field('user_id', 'reference auth_user'),
                Field('date_added', 'date'))

## OLD table to remove

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
                #Field('dataset_access', 'string'),
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
                #Field('geographic_extent', 'geometry()'),
                #Field('temporal_extent_start', 'date'),
                #Field('temporal_extent_end', 'date')
                )


# -----------------------------------------------------------------------------
# SAFE DATASET INDEX TABLE DEFINITIONS
# - these tables hold information about published datasets.
# - information is available for each published version 
#   (so datasets.id, not dataset_id.id)
# - In some ways it would be neater for these tables to use the 
#   zenodo record id as the key back to the published datasets 
#   table, but web2py can only achieve that using the IS_IN_DB 
#.  validator rather than a DB level foreign key
# -----------------------------------------------------------------------------

db.define_table('dataset_taxa',
                Field('dataset_id', 'reference published_datasets'),
                Field('gbif_id', 'integer'),
                Field('gbif_parent_id', 'integer'),
                Field('taxon_name', 'string'),
                Field('taxon_rank', 'string'),
                Field('gbif_status', 'string'))

db.define_table('dataset_files',
                Field('dataset_id', 'reference published_datasets'),
                Field('checksum', 'string', length=32),
                Field('filename', 'string'),
                Field('filesize', 'integer'),
                Field('file_zenodo_id', 'string', length=36),
                Field('download_link', 'string'))

db.define_table('dataset_locations',
                Field('dataset_id', 'reference published_datasets'),
                Field('name', 'string'),
                Field('new_location', 'boolean'),
                Field('type', 'string'),
                Field('wkt_wgs84', 'geometry()'),
                Field('wkt_utm50n', 'geometry(public, 32650, 2)'))

db.define_table('dataset_worksheets',
                Field('dataset_id', 'reference published_datasets'),
                Field('name', 'string'),
                Field('description', 'text'),
                Field('title', 'string'),
                Field('external', 'string'),
                Field('n_data_row', 'integer'),
                Field('max_col', 'integer'))

db.define_table('dataset_fields',
                Field('dataset_id', 'reference published_datasets'),
                Field('worksheet_id', 'reference dataset_worksheets'),
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

db.define_table('dataset_authors',
                Field('dataset_id', 'reference published_datasets'),
                Field('affiliation', 'string'),
                Field('email', 'string'),
                Field('name', 'string'),
                Field('orcid', 'string'))

db.define_table('dataset_funders',
                Field('dataset_id', 'reference published_datasets'),
                Field('body', 'string'),
                Field('ref', 'string'),
                Field('type', 'string'),
                Field('url', 'string'))

db.define_table('dataset_permits',
                Field('dataset_id', 'reference published_datasets'),
                Field('authority', 'string'),
                Field('number', 'string'),
                Field('type', 'string'))
