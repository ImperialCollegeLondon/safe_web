import shutil
import hashlib
import datetime
from safe_web_global_functions import datepicker_script
from safe_web_datasets import (submit_dataset_to_zenodo, dataset_description, 
                               generate_inspire_xml, update_published_metadata)


def view_datasets():
    """
    Grid view to display datasets that have been published. There
    is a simple internal view, but it basically duplicates the information
    passed to Zenodo.
    
    Dev note: Standard DOI URL shows the DOI and the link redirects
    to the Zenodo record, but this doesn't work for the Zenodo Sandbox
    so for the moment, using the record URL to get to the record directly.
    """


    def _access(row):
        
        row.dataset_access
        ret = SPAN("O", _class='badge', _style="background-color:green;font-size: 1em;")
        
        if row.dataset_access == 'embargo' and row.dataset_embargo > datetime.date.today():
             ret = SPAN("E", _class='badge', _style="background-color:orange;font-size: 1em;",
                        _title=row.dataset_embargo)
        elif row.dataset_access == 'restricted':
             ret = SPAN("R", _class='badge', _style="background-color:red;font-size: 1em;",
                         _title=row.dataset_conditions)
        
        return ret

    
    # format fields for the display
    db.published_datasets.zenodo_concept_badge.represent = lambda value, row:  A(IMG(_src=value), _href=row.zenodo_concept_doi)
    db.published_datasets.publication_date.represent = lambda value, row: value.date().isoformat()
    db.published_datasets.dataset_access.represent = lambda value, row: _access(row)
    
    # hide fields used in table prep
    db.published_datasets.zenodo_record_id.readable = False
    db.published_datasets.zenodo_concept_doi.readable = False
    db.published_datasets.dataset_embargo.readable = False
    db.published_datasets.dataset_conditions.readable = False
    
    # button to link to custom view
    links = [dict(header = '',
                  body = lambda row: A('Details', _class='button btn btn-sm btn-default',
                                       _href=URL("datasets","view_dataset", vars={'id': row.zenodo_record_id})))]
    
    # Display those records as a grid
    form = SQLFORM.grid(db.published_datasets.most_recent == True,
                        fields = [#db.published_datasets.project_id,
                                  db.published_datasets.publication_date,
                                  db.published_datasets.dataset_title,
                                  db.published_datasets.dataset_access,
                                  db.published_datasets.dataset_embargo,
                                  db.published_datasets.dataset_conditions,
                                  db.published_datasets.zenodo_record_id,
                                  db.published_datasets.zenodo_concept_badge,
                                  db.published_datasets.zenodo_concept_doi],
                        headers = {'published_datasets.zenodo_concept_badge': 'DOI'},
                        orderby = [~ db.published_datasets.publication_date],
                        maxtextlength = 100,
                        deletable=False,
                        editable=False,
                        details=False,
                        create=False,
                        csv=False,
                        links=links)
    
    return dict(form=form)


def view_dataset():
    
    """
    View of a specific version of a dataset, taking the zenodo record id as the
    id parameter, but which also shows other published versions of the dataset concept.
    """
    
    ds_id = request.vars['id']
    
    if ds_id is None:
        # no id provided
        session.flash = "Missing dataset id"
        redirect(URL('datasets','view_datasets'))

    try:
        ds_id = int(ds_id)
    except ValueError:
        session.flash = "Dataset id is not an integer"
        redirect(URL('datasets','view_datasets'))
    
    # Does the record identify a specific version
    record = db(db.published_datasets.zenodo_record_id == ds_id).select().first()
    
    # If not, does it identify a concept, so get the most recent
    if record is None:
        record = db((db.published_datasets.zenodo_concept_id == ds_id) &
                    (db.published_datasets.most_recent == True)).select().first()
        # Otherwise, bail
        if record is None:
            # non-existent id provided
            session.flash = "Database record id does not exist"
            redirect(URL('datasets','view_datasets'))
        else:
            ds_id = record.zenodo_record_id
    
    # get the version history
    qry = ((db.published_datasets.zenodo_concept_id == record.zenodo_concept_id))
    
    history = db(qry).select(db.published_datasets.id,
                             db.published_datasets.publication_date,
                             #db.published_datasets.uploader_id,
                             db.published_datasets.zenodo_record_badge,
                             db.published_datasets.zenodo_record_doi,
                             db.published_datasets.zenodo_record_id,
                             orderby= ~ db.published_datasets.publication_date)
    
    # style that into a table showing the currently viewed version

    view = SPAN(_class="glyphicon glyphicon-eye-open", 
                   _style="color:green;font-size: 1.4em;")
    alt = SPAN(_class="glyphicon glyphicon-eye-close", 
                    _style="color:grey;font-size: 1.4em;", 
                    _title='View this version')
    
    history_table = TABLE(TR(TH('Viewing'), TH('Version publication date'), #TH('Uploaded by'),
                             TH('Zenodo DOI')),
                          *[TR(TD(view) if r.zenodo_record_id == ds_id
                               else TD(A(alt, _href=URL(vars={'id': r.zenodo_record_id}))),
                               TD(r.publication_date),
                               #TD(r.uploader_id.first_name + ' ' + r.uploader_id.last_name),
                               TD(A(IMG(_src=r.zenodo_record_badge), 
                                    _href=r.zenodo_record_doi)))
                            for r in history],
                         _width='100%', _class='table table-striped table-bordered')

    # get the description
    description = XML(dataset_description(record, gemini_id=ds_id))

    # get projects
    #db(db)
    
    return(dict(record=record, description=description, 
                history_table=history_table))


@auth.requires_membership('admin')
def administer_datasets():
    
    """
    Grid view to display datasets to admin.
    """
    
    # format fields for the display, giving the check outcome and zenodo publishing status as icons.
    table = db.submitted_datasets
    
    table.project_id.represent = lambda value, row: A(value, 
                                                      _href=URL('projects','project_view',
                                                                args=[value]))
    table.dataset_check_outcome.represent =  lambda value, row: approval_icons[value]
    table.zenodo_submission_status.represent =  lambda value, row: approval_icons[value]
    
    # alter the file representation to add the dataset id as a variable to the download
    table.file.represent = lambda value, row: A('Download file', 
                                                _href=URL('datasets', 'download_dataset',
                                                          row.file, vars={'dataset_id': row.id}))
                                                          
    # alter the upload datetime representation
    table.upload_datetime.represent = lambda value, row: value.date().isoformat()
    
    # Use the concept_id to indicate update/new status
    def _update_or_new(row):
        
        if row.concept_id is not None:
            publ = db(db.published_datasets.zenodo_concept_id == row.concept_id
                      ).select().first()
            return A(IMG(_src=publ.zenodo_concept_badge), 
                     _href=publ.zenodo_concept_doi)
        else:
            return "New dataset"
    
    
    table.concept_id.represent = lambda value, row: _update_or_new(row)

    # use the metadata to indicate access
    
    def _access(row):
        
        if row.dataset_metadata is None:
            return approval_icons['PENDING']
        else:
            status = row.dataset_metadata['metadata']['access']
        
            if status == 'open':
                return SPAN("O", _class='badge', _style="background-color:green;font-size: 1em;")
            elif status == 'embargo':
                return SPAN("E", _class='badge', _style="background-color:orange;font-size: 1em;",
                            _title=row.dataset_metadata['metadata']['embargo_date'])
            elif status == 'restricted':
                return SPAN("R", _class='badge', _style="background-color:red;font-size: 1em;",
                            _title=row.dataset_metadata['metadata']['access_conditions'])

    table.dataset_metadata.represent = lambda value, row: _access(row)

    # hide field used in preparing the table
    #table.dataset_metadata.readable = False
    table.project_id.readable = False
    #db.submitted_datasets.concept_id.readable = False

    # add buttons to provide options
    # - run check (can only be run if file has not passed)
    def _run_check(row):
        if row.dataset_check_outcome == 'PASS':
            btn =  A('Check', _class='button btn btn-default disabled',
                     _style='padding: 3px 10px 3px 10px')
        else:
            btn =  A('Check', _class='button btn btn-default',
                     _href=URL("datasets","run_verify_dataset",
                               vars={'record_id':row.id, 'email':0, 'manage':''}),
                     _style='padding: 3px 10px 3px 10px;')
        return btn
    
    # - run publish (can only be run if file has passed and not yet been published)
    def _run_publish(row):
        if row.dataset_check_outcome != 'PASS' or row.zenodo_submission_status == 'ZEN_PASS':
            btn = A('Publish', _class='button btn btn-default disabled',
                    _style='padding: 3px 10px 3px 10px;width: 70px;')
        elif ((row.dataset_metadata is not None) and 
              ('metadata' in row.dataset_metadata) and 
              ('external_files' in row.dataset_metadata['metadata']) and
              (row.dataset_metadata['metadata']['external_files'])):
            btn = A('Adopt', _class='button btn btn-default adopt',
                    _href=None,
                    _style='padding: 3px 10px 3px 10px;width: 70px;',
                    _record_id=row.id)
        else:
            btn = A('Publish', _class='button btn btn-default',
                    _href=URL("datasets","run_submit_dataset_to_zenodo",
                              vars={'id':row.id, 'manage':''}),
                    _style='padding: 3px 10px 3px 10px;width: 70px;')
        
        return btn
    
    # - submit page link    
    links = [dict(header = '', body = lambda row: _run_check(row)),
             dict(header = '', body = lambda row: _run_publish(row))]
    
    # provide a grid display of current datasets
    form = SQLFORM.grid(db.submitted_datasets,
                        fields = [db.submitted_datasets.project_id,
                                  db.submitted_datasets.upload_datetime,
                                  db.submitted_datasets.uploader_id,
                                  db.submitted_datasets.concept_id,
                                  db.submitted_datasets.dataset_title,
                                  db.submitted_datasets.dataset_metadata,
                                  db.submitted_datasets.dataset_check_outcome,
                                  db.submitted_datasets.zenodo_submission_status,
                                  db.submitted_datasets.file],
                        headers = {'submitted_datasets.upload_datetime': 'Upload date',
                                   'submitted_datasets.concept_id': 'Updating',
                                   'submitted_datasets.dataset_metadata': 'Access',
                                   'submitted_datasets.dataset_check_outcome': 'Format status',
                                   'submitted_datasets.zenodo_submission_status': 'Published'},
                        orderby = [~ db.submitted_datasets.upload_datetime],
                        links = links,
                        maxtextlength = 100,
                        deletable=True,
                        editable=False,
                        details=True,
                        create=False,
                        csv=False)
    
    return dict(form=form)


@auth.requires_membership('admin')
def change_dataset_access():

    # populate a select element with the current zenodo records and set the client side
    # AJAX function used to update the form elements
    zenodo_records = db(db.published_datasets).select(db.published_datasets.zenodo_record_id,
                                                      orderby=db.published_datasets.zenodo_record_id)
    zenodo_records = [str(r.zenodo_record_id) for r in zenodo_records]
    select = SELECT(OPTION('Select record ID', _disabled=True, _selected=True), 
                    *zenodo_records, 
                    _id='zenodo_selector', _name='zenodo_selector', _onchange="get_access()")
    
    # Create the form, including hidden components that will be revealed using client side JS
    form = FORM(DIV(DIV(DIV(DIV(B('Zenodo Record ID'), _class='col-sm-3'),
                            DIV(select, _class='col-sm-9'),
                            _class='row'),
                        HR(),
                        DIV(DIV(B('Dataset Title'), _class='col-sm-3'),
                            DIV(_id='title', _class='col-sm-9'),
                            _class='row'),
                        DIV(DIV(B('Current Status'), _class='col-sm-3'),
                            DIV(_id='status', _class='col-sm-9'),
                            _class='row'),
                        DIV(DIV(B('Embargo Date'), _class='col-sm-3'),
                            DIV(_id='embargo', _class='col-sm-9'),
                            _class='row', _id='embargo_display', _hidden=True),
                        DIV(DIV(B('Access conditions'), _class='col-sm-3'),
                            DIV(_id='conditions', _class='col-sm-9'),
                            _class='row', _id='conditions_display', _hidden=True),
                        HR(),
                        DIV(DIV(B('New Status'), _class='col-sm-3'),
                            DIV(SELECT('Open', 'Embargo', 'Restricted', 
                                       _id='set_status', _name='set_status'), 
                                _class='col-sm-6'),
                            DIV(DIV(INPUT(_type='submit')), 
                                _class='col-sm-3 pull-right'),
                            _class='row', _onchange='on_set_status()'),
                        DIV(DIV(B('Set Embargo Date'), _class='col-sm-3'),
                            DIV(INPUT(_id='set_embargo', _name='set_embargo'), _class='col-sm-9'),
                            _class='row', _id='display_set_embargo', _hidden=True),
                        DIV(DIV(B('Set Access Conditions'), _class='col-sm-3'),
                            DIV(TEXTAREA(_id='set_conditions', _name='set_conditions'), _class='col-sm-9'),
                            _class='row', _id='display_set_conditions', _hidden=True),
                        _class='panel-body'),
                    _class='panel panel-default'))

    # Validate the form: bespoke data entry
    if form.validate(onvalidation=validate_change_dataset_access):
        
        record = db(db.published_datasets.zenodo_record_id == form.vars.zenodo_selector).select().first()
        
        # update_record
        new_history = "Access updated {} by {} {}:\nOld: {} {} {}\nNew: {} {} {}\n".format(
                          datetime.date.today().isoformat(),
                          auth.user.first_name,
                          auth.user.last_name,
                          record.dataset_access,
                          record.dataset_embargo,
                          record.dataset_conditions,
                          form.vars.set_status,
                          form.vars.set_embargo,
                          form.vars.set_conditions)
        
        dataset_history = new_history if record.dataset_history is None else record.dataset_history + new_history

        record.update_record(dataset_history=dataset_history,
                             dataset_access=form.vars.set_status,
                             dataset_embargo=form.vars.set_embargo,
                             dataset_conditions=form.vars.set_conditions)
        
        # update Zenodo
        if form.vars.set_status == 'open':
            update = {'access_right': 'open',
                      'embargo_date': None,
                      'access_conditions': None}
        elif form.vars.set_status == 'embargo':
            update = {'access_right': 'embargoed',
                      'embargo_date': form.vars.set_embargo,
                      'access_conditions': None}
        elif form.vars.set_status == 'restricted':
            update = {'access_right': 'restricted',
                      'embargo_date': None,
                      'access_conditions': form.vars.set_conditions}
        
        code, content = update_published_metadata(form.vars.zenodo_selector, update)
        print form.vars.zenodo_selector, update, content
        
        # If the zenodo update failed, flash a message and rollback the record update.
        if code != 0:
            failure_message = 'Failed to update Zenodo ({status}): {message}'.format(**content)
            if 'errors' in content:
                for each_error in content['errors']:
                    failure_message += '{field}: {message};'.format(**each_error)
            
            response.flash = 'Failed to update Zenodo ({status}): {message}'.format(**content)
            db.rollback()
    
    elif form.errors:
        response.flash = 'Errors in upload'
    
    return dict(form=form)


def validate_change_dataset_access(form):

    form.vars.set_status = form.vars.set_status.lower()

    if form.vars.set_status not in ['open','embargo','restricted']:
        form.errors.set_status = "Select a new access status" 
    
    if form.vars.set_status == 'embargo' and form.vars.set_embargo == "":
        form.errors.set_embargo = "Set new embargo date"
    elif form.vars.set_status == 'restricted' and form.vars.set_conditions == "":
        form.errors.set_conditions = "Provide access conditions for restricted datasets"


@auth.requires_membership('admin')
def download_dataset():
    
    # if this is a dataset then should be able to point it to the right path
    if 'dataset_id' in request.vars:
        db.datasets.file.uploadfolder = os.path.join(request.folder, 'uploads', 'datasets', request.vars.dataset_id)
    
    return response.download(request, db)


@auth.requires_login()
def submit_dataset():

    """
    Interface for dataset submission. Flow is:
    1) Upload your file along with project ID.
    2) It gets checked in the background and you get an email with the result and a link
    3) If it fails, fix and reupload.
    4) Once it passes, the website admin will check it and publish it.
    
    If users have a file that they think should pass, they can contact the
    website admin team. It may be that the validator program needs modifying!
    """

    # Set up a query to find the projects that a user can submit datasets under
    if auth.has_membership('admin'):
        query = (db.project_id.project_details_id == db.project_details.id)
    else:
        query = ((db.project_members.user_id == auth.user.id) &
                 (db.project_members.project_id == db.project_id.id) &
                 (db.project_id.project_details_id == db.project_details.id))
    
    # Extend that through to find the most recent version of existing datasets
    # associated with project the user belongs to. Used to populate update links
    project_datasets = db(query & 
                          (db.project_datasets.project_id == db.project_id.id) &
                          (db.project_datasets.concept_id == db.published_datasets.zenodo_concept_id) &
                          (db.published_datasets.most_recent == True)
                          ).select(db.published_datasets.zenodo_record_id,
                                   db.published_datasets.zenodo_concept_id,
                                   db.published_datasets.zenodo_concept_doi,
                                   db.published_datasets.dataset_title,
                                   db.published_datasets.zenodo_concept_badge)
    
    
    # Set the list and display format of available projects to submit under
    db.submitted_datasets.project_id.requires = IS_IN_DB(db(query), 'project_details.project_id',
                                                         '%(project_id)s: %(title)s',
                                                         zero='Select project.')
    
    # Controller accepts one variable:
    # - update to update an existing published dataset by reference to its zenodo concept id
    if 'update' in request.vars:
        concept_id = request.vars['update']
        
        try:
            concept_id = int(concept_id)
        except ValueError:
            session.flash = ('The concept_id is not an integer.')
            redirect(URL('datasets', 'submit_dataset'))
            
        most_recent_record = db((db.published_datasets.most_recent == 'T') &
                                (db.published_datasets.zenodo_concept_id == concept_id)
                                ).select().first()
        
        # Does the concept_doi return a record
        if most_recent_record is None:
            session.flash = ('Unknown concept_id.')
            redirect(URL('datasets', 'submit_dataset'))
     
        # Is that in the list of DOIs the user is eligible to resubmit        
        if not any([rw.zenodo_concept_id == concept_id for rw in project_datasets]):
            session.flash = ('You do not have permission to resubmit that dataset.')
            redirect(URL('datasets', 'submit_dataset'))
        
        # If we are updating a existing record, don't provide a set of other update links
        resubmit = DIV()

        # Set the default value of the project selector in the upload form to the existing project
        # choice, but do allow the user to change this.
        db.submitted_datasets.project_id.default = most_recent_record.project_id
        
    else:
                     
        # new datasets don't have a concept id yet
        concept_id = None
        
        # If the user is a member of projects with existing datasets, then provide a set of
        # update links alongside the new submission form
        if len(project_datasets):
        
            # create a table - can't insert the rows directly because the TABLE helper
            # tries to unpack the DIV as a row, rather than as a wrapper around rows.
            user_table = TABLE(#TR(TH('Published datasets'), 
                               #   TH('Link to Zenodo record'#,
                               #      #SPAN(_class='glyphicon glyphicon-plus pull-right clickable',
                               #      #**{'_data-toggle': "collapse", '_data-target':"#accordion"})
                               #      ),
                               #   TH('Select')),
                              _class='table table-striped', _style='margin:0px')
        
            # package up the rows in a collapse DIV
            project_datasets = [TR(TD(A(row.dataset_title, 
                                        _href=URL('datasets', 'view_dataset', 
                                        vars={'id': row.zenodo_record_id}))),
                                   TD(A(IMG(_src=row.zenodo_concept_badge),
                                        _href=row.zenodo_concept_doi)),
                                   TD(A("Submit update", _class='btn btn-default',
                                        _href=URL("datasets","submit_dataset", 
                                                  vars={'update': row.zenodo_concept_id}), 
                                        _style='padding: 5px 10px 5px 10px;')))
                                for row in project_datasets]
        
            project_datasets = TAG.tbody(*project_datasets #, 
                                         #_id="accordion", _class="collapse"
                                         )
        
            # and insert into the table object
            user_table.components.extend([project_datasets])
        
            resubmit = DIV(DIV(H5('Option: Select a dataset to update'),
                               _class='panel-heading'),
                           DIV(P('If you want to update an existing dataset, then click on the appropriate link below. '
                                 'Please ', B('do not create a new dataset'), ' when submitting a new version. '),
                               _class='panel-body'),
                           DIV(user_table),
                           _class='panel panel-default')
        else:
            resubmit = DIV()
    
    # Setup the form
    form = SQLFORM(db.submitted_datasets, 
                   fields=['project_id', 'file'],
                   showid=False,
                   deletable=False,
                   button='Upload',
                   hidden={'concept_id': None})
    
    # Validate the form: bespoke data entry
    if form.validate(onvalidation=validate_dataset_upload):
        
        # Create new record to hold the dataset
        record_id = db.submitted_datasets.insert(
                      project_id=form.vars.project_id,
                      uploader_id=auth.user.id,
                      concept_id=concept_id,
                      file_name=form.vars.file_name,
                      file_hash=form.vars.file_hash,
                      file_size=form.vars.file_size,
                      upload_datetime=datetime.datetime.now(),
                      file = form.vars.file)
            
        # schedule the dataset check
        #  - set timeout to extend the default of 60 seconds.
        #  - no start_time, so defaults to now.
        task = scheduler.queue_task('verify_dataset', 
                                    pvars = {'record_id': record_id, 'email': True},
                                    timeout = 5*60,
                                    repeats=1,
                                    immediate=True)
    
        # notify upload has worked
        session.flash = ('Upload successful. A validation check will be run and '
                         'you will get an email with the results when it finishes.')
    
        # send to the updated page
        redirect(URL('datasets', 'submitted_dataset_status', vars={'id': record_id}))

    elif form.errors:
        response.flash = 'Errors in upload'
    
    # Style the form and embed in a panel
    form.custom.widget.project_id['_style'] = 'height:30px'
    form = DIV(form.custom.begin, 
               DIV(DIV(B('Project'), _class="col-sm-3" ),
                   DIV(form.custom.widget.project_id,  _class="col-sm-9"),
                   _class='row', _style='margin:5px 10px'),
               DIV(DIV(B('File'), _class="col-sm-3" ),
                   DIV(form.custom.widget.file,  _class="col-sm-6"),
                   DIV(DIV(form.custom.submit, _class='pull-right'), _class="col-sm-3"),
                   _class='row', _style='margin:10px 10px'),
               form.custom.end)
    
    if concept_id is None:
        form = DIV(DIV(H5('Option: Submit a new dataset'),
                       _class='panel-heading'),
                   DIV(P('Use this form if you are submitting a completely new dataset:'),
                       form, 
                       _class='panel-body'), 
                   _class='panel panel-default')
    else:
        form = DIV(DIV(DIV(DIV(H5('Option: Submit an update'), _class='col-sm-9'),
                           DIV(DIV(A(IMG(_src=most_recent_record.zenodo_concept_badge), 
                                     _href=most_recent_record.zenodo_concept_doi),
                                   _class='pull-right'),
                               _class='col-sm-3'),
                           _class='row'),
                       _class='panel-heading'),
                   DIV(P('The form below will submit an update to the dataset: ', most_recent_record.dataset_title),
                       form,
                       P('If you want to create a new dataset or update a different dataset, click ',
                         A('here', _href=URL('datasets', 'submit_dataset')), '.'),
                       _class='panel-body'),
                   _class='panel panel-default')
        
    return dict(form=form, resubmit=resubmit)


def validate_dataset_upload(form):
    """
    Validation function for the dataset upload form
    Args:
        form: The SQLFORM object returned
    """
        
    if isinstance(form.vars.file, str):
        # Check that the file isn't a string, which it is when 
        # submit is pushed with no file selected.
        form.errors.file = "No file selected"
    elif request.vars.file.filename[-5:].lower() != '.xlsx':
        # Is the file at least nominally an Excel file?
        form.errors.file = "File is not in XLSX format"
    elif ' ' in request.vars.file.filename:
        # Do not use spaces in filenames
        form.errors.file = "Please do not use spaces in filenames"
    else:
        # Process the file to check it before uploading it
        # - populate dataset info fields
        form.vars.file_name = request.vars.file.filename
        form.vars.file_hash = hashlib.md5(form.vars.file.value).hexdigest()
        form.vars.file_size= len(form.vars.file.value)
        form.vars.uploader_id = auth.user.id
        form.vars.upload_datetime = datetime.datetime.utcnow().isoformat()
        
        # This validation does not check if the Excel file has been submitted
        # before (by hash comparison) because it is possible that only external
        # files have changed.

def submitted_dataset_status():
    
    """
    Controller to display the outcome of a dataset submission.    
    """
    
    if 'id' in request.vars:
        record = db.submitted_datasets[request.vars['id']]
        
        if record is None:
            record = db(db.published_datasets.submission_id == request.vars['id']
                        ).select().first()
            
            if record is None:
                session.flash = 'Unknown submitted dataset record id.'
                redirect(URL('datasets', 'submit_dataset'))
            else:
                redirect(URL('datasets', 'view_dataset', vars={'id': record.zenodo_record_id}))
    else:
        session.flash = 'Submitted dataset record id missing.'
        redirect(URL('datasets', 'submit_dataset'))
    
    # local function to pack rows
    def _row(head, body):
        
        return  DIV(DIV(B(head), _class='col-sm-3'), DIV(body, _class='col-sm-9'),
                    _class='row', _style='margin:5px 10px')

    # The dataset could be a new dataset, in which case a project is assigned,
    # or a resubmission, in which case the project id is None and the dataset
    # is associated with an existing Zenodo concept ID and the projects 
    # associated with that concept ID
    
    if record.concept_id is None:
        # basic check information for any upload
        project = db((db.project_id.id == record.project_id) &
                     (db.project_id.project_details_id == db.project_details.id)
                     ).select(db.project_details.title).first()
        status_table = [_row('Project assignment', '(' + str(record.project_id) + ') ' + project.title)]
    else:
        status_table = [_row('Update to ', record.concept_id)]

    status_table += [_row('File name', record.file_name),
                     _row('File size', '{:0.2f} MB'.format(record.file_size / 1024.0 ** 2)),
                     _row('Uploaded', record.upload_datetime.strftime('%Y-%m-%d %H:%M')),
                     _row('Uploaded by', record.uploader_id.first_name + " " + record.uploader_id.last_name),
                     _row('Check outcome', CAT(approval_icons[record.dataset_check_outcome],
                                               XML('&nbsp') * 3, record.dataset_check_outcome))]

    # Check report    
    if record.dataset_check_outcome == 'PENDING':
        # Set the heading for the form
        panel_head = DIV(DIV(H4('Dataset awaiting verification', _class="panel-title col-sm-8"),
                             _class='row'),
                         _class="panel-heading")
                         
        panel_foot = DIV(P('Please contact us if you have any questions about the verification process'), 
                         _class='panel-footer')
        
    elif record.dataset_check_outcome == 'FAIL':
        # Set the heading for the form
        panel_head = DIV(DIV(H4('Dataset failed verification', _class="panel-title col-sm-8"),
                             _class='row'),
                         _class="panel-heading")

        # include the check report
        status_table.append(_row('Check report', A('View details', _href='#show_check', **{'_data-toggle': 'collapse'})))
        status_table.append(_row('', DIV(XML(record.dataset_check_report),
                                         _id="show_check", _class="panel-collapse collapse")))

        panel_foot = DIV(P('Please fix the issues described in the check report and '
                           'resubmit your dataset.'), 
                         _class='panel-footer')
                      
    elif record.dataset_check_outcome == 'ERROR':
        # Set the heading for the form
        panel_head = DIV(DIV(H4('Dataset verification error', _class="panel-title col-sm-8"),
                             _class='row'),
                         _class="panel-heading")

        panel_foot  = DIV(P('There has been a problem with verification process on your dataset. '
                      'Please bear with us while we investigate this and then update your '
                      'dataset status'), _class='panel-footer')

    elif record.dataset_check_outcome == 'PASS':
        # Set the heading for the form
        panel_head = DIV(DIV(H4('Dataset passed verification', _class="panel-title col-sm-8"),
                             _class='row'),
                         _class="panel-heading")

        # include the check report
        status_table.append(_row('Check report', A('View details', _href='#show_check', **{'_data-toggle': 'collapse'})))
        status_table.append(_row('', DIV(XML(record.dataset_check_report),
                                         _id="show_check", _class="panel-collapse collapse")))
                
        # preview description
        status_table.append(_row('Dataset description', A('Preview', _href='#desc_preview', **{'_data-toggle': 'collapse'})))
        desc_preview = dataset_description(record)

        status_table.append(_row('', DIV(XML(desc_preview),
                                         _id="desc_preview", _class="panel-collapse collapse")))
        
        panel_foot = DIV(P('Your dataset has passed dataset checking and will be published soon.'), 
                         _class='panel-footer')

    panel = DIV(panel_head, DIV(*status_table, _class='panel_body'), panel_foot, _class="panel panel-default")

    return dict(panel=panel)

"""
These controllers provide an API to carry out dataset checks etc. They can operate
in two modes - normally they just return a web page containing text but with manage
in the variables, they will reload the dataset management page. This feels hacky!
"""

@auth.requires_membership('admin')
def run_verify_dataset():
    """
    Controller to allow an admin to (re)run dataset verification
    on a dataset with a given row id, and control whether the 
    uploader gets emailed with the outcome.
    """
    
    record_id = request.vars['record_id']
    email = request.vars['email']
    manage = 'manage' in request.vars
    err = []
    
    if record_id is None:
        err += ["Record ID missing"]
    else:
        try:
            record_id = int(record_id)
        except ValueError:
            err += ["Record ID not an integer"]
    
    if email is None:
        err += ["Email option missing"]
    elif not email in ['0', '1']:
        err += ["Email option must be 0 or 1"]
    else:
        email = True if email == '1' else False
    
    if len(err) == 0:
        res = verify_dataset(record_id, email)
    else:
        res = ', '.join(err)
    
    if manage:
        session.flash = res
        redirect(URL('datasets','administer_datasets'))
    else:
        return res


@auth.requires_membership('admin')
def run_submit_dataset_to_zenodo():
    """
    Controller to allow an admin to (re)run dataset publication
    on a dataset with a given row id. The key 'zenodo' can be passed
    in as well - this is used to adopt existing zenodo deposits to allow
    for non-Excel datasets. The app config contains a switch that allows
    the application to use the Zenodo sandbox rather than the main site.
    """

    record_id = request.vars['id']
    manage = 'manage' in request.vars
    err = []

    if 'zenodo' in request.vars:
        deposit_id = int(request.vars['zenodo'])
    else:
        deposit_id = None

    if record_id is None:
        err += ["Record ID missing"]
    else:
        try:
            record_id = int(record_id)
        except ValueError:
            err += ["Record ID not an integer"]

    if len(err) == 0:
        res = submit_dataset_to_zenodo(record_id, deposit_id=deposit_id)
    else:
        res = ', '.join(err)
    
    if manage:
        session.flash = res
        redirect(URL('datasets','administer_datasets'))
    else:
        return res


def xml_metadata():
    
    """
    A controller that just acts to spit out an GEMINI/INSPIRE XML 
    metadata record for a dataset Zenodo id passed as 'id'
    """
    
    zenodo_id = request.vars['id']
    
    if zenodo_id is None:
        return XML("No dataset id provided")
    
    try:
        zenodo_id = int(zenodo_id)
    except ValueError:
        return XML("Non-integer dataset id")
    
    record = db(db.published_datasets.zenodo_record_id == zenodo_id).select().first()
    
    if record is None:
        return XML("Invalid dataset id")
    else:
        xml = generate_inspire_xml(record)
        raise HTTP(200, xml,
                   **{'Content-Type':'text/xml',
                      'Content-Disposition': 'attachment;filename={}.xml;'.format(record.zenodo_metadata['doi'])})
    