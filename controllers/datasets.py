import hashlib
import datetime
import safe_dataset_checker


def view_datasets():
    """
    Grid view to display datasets that have been published. There
    is a simple internal view, but it basically duplicates the information
    passed to Zenodo.
    
    Dev note: Standard DOI URL shows the DOI and the link redirects
    to the Zenodo record, but this doesn't work for the Zenodo Sandbox
    so for the moment, using the record URL to get to the record directly.
    """
    
    # format fields for the display
    db.datasets.project_id.represent = lambda value, row: A(value, _href=URL('projects','project_view', args=[value])) 
    db.datasets.zenodo_badge.represent = lambda value, row:  A(IMG(_src=value), _href=row.zenodo_doi)
    
    # button to link to custom view
    links = [dict(header = '', body = lambda row: A('Details',_class='button btn btn-sm btn-default'
                  ,_href=URL("datasets","view_dataset", vars={'dataset_id': row.id})))]
    
    # provide a grid display
    form = SQLFORM.grid((db.datasets.dataset_check_outcome == 'PASS') &
                        (db.datasets.zenodo_submission_status == 'ZEN_PASS'),
                        fields = [db.datasets.project_id,
                                  # db.datasets.uploader_id,
                                  db.datasets.dataset_title,
                                  db.datasets.zenodo_doi,
                                  db.datasets.zenodo_badge
                                  ],
                        headers = {'datasets.zenodo_doi': 'Zenodo',
                                   'datasets.zenodo_badge': 'Link',
                                   'datasets.project_id': 'Project'},
                        maxtextlength = 100,
                        deletable=False,
                        editable=False,
                        details=False,
                        create=False,
                        csv=False,
                        links=links)
    
    return dict(form=form)

def view_dataset():
    
    ds_id = request.vars['dataset_id']
    record = db.datasets[ds_id]
    
    if ds_id is None:
        # no id provided
        record = None
    elif record is None:
        # non-existent id provided
        session.flash = "Database record id does not exist"
        redirect(URL('datasets','view_datasets'))
    
    description = _dataset_description(record)
    return(dict(record=record, description=description))



@auth.requires_membership('admin')
def administer_datasets():
    
    """
    Grid view to display datasets to admin.
    """
    
    # format fields for the display, giving the check outcome and zenodo publishing status as icons.
    db.datasets.project_id.represent = lambda value, row: A(value, _href=URL('projects','project_view', args=[value])) 
    db.datasets.dataset_check_outcome.represent =  lambda value, row: approval_icons[value]
    db.datasets.zenodo_submission_status.represent =  lambda value, row: approval_icons[value]
    
    # add buttons to provide options
    # - run check (can only be run if file has not passed)
    def _run_check(row):
        if row.dataset_check_outcome == 'PASS':
            btn =  A('Check', _class='button btn btn-default disabled',
                     _style='padding: 3px 10px 3px 10px')
        else:
            btn =  A('Check', _class='button btn btn-default',
                     _href=URL("datasets","run_verify_dataset", vars={'dataset_id':row.id, 'email':0, 'manage':''}),
                     _style='padding: 3px 10px 3px 10px;')
        return btn
    
    # - run publish (can only be run if file has passed and not yet been published)
    def _run_publish(row):
        if row.dataset_check_outcome != 'PASS' or row.zenodo_submission_status == 'ZEN_PASS':
            btn =  A('Publish', _class='button btn btn-default disabled',
                     _style='padding: 3px 10px 3px 10px')
        else:
            btn =  A('Publish', _class='button btn btn-default',
                     callback=URL("datasets","run_submit_dataset_to_zenodo", vars={'id':row.id, 'manage':''}),
                     _style='padding: 3px 10px 3px 10px;')
        return btn
    
    # - run publish (can only be run if file has passed and not yet been published)
    def _run_delete(row):
        if row.zenodo_submission_status == 'ZEN_PASS':
            btn =  A('Delete', _class='button btn btn-default disabled',
                     _style='padding: 3px 10px 3px 10px')
        else:
            btn =  A('Delete', _class='button btn btn-default',
                     callback=URL("datasets","run_delete_dataset", vars={'id':row.id, 'manage':''}),
                     _style='padding: 3px 10px 3px 10px;')
        return btn
    
    links = [dict(header = '', body = lambda row: _run_check(row)),
             dict(header = '', body = lambda row: _run_publish(row)),
             dict(header = '', body = lambda row: _run_delete(row))]
    
    # provide a grid display
    form = SQLFORM.grid(db.datasets,
                        fields = [db.datasets.project_id,
                                  db.datasets.uploader_id,
                                  db.datasets.dataset_title,
                                  db.datasets.dataset_check_outcome,
                                  db.datasets.zenodo_submission_status,
                                  ],
                        headers = {'datasets.dataset_check_outcome': 'Format status',
                                   'datasets.zenodo_submission_status': 'Published'},
                        links = links, 
                        maxtextlength = 100,
                        deletable=False,
                        editable=False,
                        details=True,
                        create=False,
                        csv=False)
    
    return dict(form=form)


@auth.requires_login()
def submit_dataset():

    """
    Interface for dataset submission. Flow is:
    1) Upload your file along with project ID.
    2) It gets checked in the background and you get an email with the result and a link
    3) That provides the opportunity to replace the file with an updated one
    4) Once it passes, the website admin will check it and publish it.
    
    If users have a file that they think should pass, they can contact the
    website admin team. It may be that the validator program needs modifying!
    """
    
    # controller has one variable: ID, which allows users to return to 
    # a submission to replace the file and submit a checked file.
    ds_id = request.vars['dataset_id']
    record = db.datasets[ds_id]
    
    if ds_id is None:
        # no id provided
        record = None
    elif record is None:
        # non-existent id provided
        session.flash = "Database record id does not exist"
        redirect(URL('datasets','view_datasets'))
    else:
        # check if uploader is trying to view this submission
        if record.uploader_id != auth.user.id:
            session.flash = "Dataset uploaded by a different user"
            redirect(URL('datasets','view_datasets'))
    
    # Set up the form
    #  - restrict choice of projects for standard users 
    #    but let admins submit to any project
    if auth.has_membership('admin'):
        query = db(db.project_id.project_details_id == db.project_details.id)
    else:
        query = db((db.project_members.user_id == auth.user.id) &
                   (db.project_members.project_id == db.project_id.id) &
                   (db.project_id.project_details_id == db.project_details.id))
    
    # display ID and title of projects
    db.datasets.project_id.requires = IS_IN_DB(query, 'project_details.project_id', '%(project_id)s: %(title)s',
                                               zero='Select project.')
    
    # setup the form
    form = SQLFORM(db.datasets, 
                   record = record, 
                   fields=['project_id', 'file'],
                   showid=False,
                   deletable=False,
                   button='Upload')
    
    # Process the form
    if form.process(onvalidation=validate_dataset_upload).accepted:
        # notify upload has worked
        session.flash = ('Upload successful. A validation check will be run and '
                          'you will get an email with the results when it finishes.')
        
        # if this is an update, then reset dataset check fields 
        if record is not None:
            record.update_record(dataset_check_outcome = 'PENDING',
                                 dataset_check_error = '',
                                 dataset_check_report = '')
        
        # schedule the dataset check
        #  - set timeout to extend the default of 60 seconds. (If large files run
        #    longer than this then the safe_dataset_checker code is going to need optimizing!)
        #  - no start_time, so defaults to now.
        task = scheduler.queue_task('verify_dataset', 
                                    pvars = {'dataset_id': form.vars.id, 'email': True},
                                    timeout = 5*60,
                                    repeats=1,
                                    immediate=True)
        
        # send to the updated page
        redirect(URL('datasets', 'submit_dataset', vars={'dataset_id':form.vars.id}))
    
    elif form.errors:
        response.flash = 'Errors in upload'
    
    # Package the page contents - this is a panel that contains
    # 1) Information on the uploaded file verification (if a dataset id is provided)
    # 2) Information on the publication status (if a dataset id is provided and it is published)
    # 3a) Form controls to validate a replacement file (if check outcome is Fail or Error)
    # 3b) Form controls to create a new version (if file is published)
    
    # repack the form into a panel body
    form.custom.widget.project_id['_style'] = 'height:30px'
    
    form =  DIV(form.custom.begin, 
                DIV(DIV(B('Project'), _class="col-sm-2" ),
                    DIV(form.custom.widget.project_id,  _class="col-sm-10"),
                    _class='row', _style='margin:5px 10px'),
                DIV(DIV(B('File'), _class="col-sm-2" ),
                    DIV(form.custom.widget.file,  _class="col-sm-7"),
                    DIV(DIV(form.custom.submit, _class='pull-right'), _class="col-sm-3"),
                    _class='row', _style='margin:10px 10px'),
                   form.custom.end, _class='panel-body')
    
    # local function to pack rows
    def _row(head, body):
        
        return  DIV(DIV(B(head), _class='col-sm-3'), DIV(body, _class='col-sm-9'),
                    _class='row', _style='margin:5px 10px')
    
    # Work through the alternative states
    if record is None:
        # Set the heading for the form
        panel_head = DIV(DIV(H4('Upload new dataset', _class="panel-title col-sm-8"),
                             _class='row'),
                         _class="panel-heading")
        # There is no file check information or report
        chk_panel = ""
        chk_rprt = ''
        dataset_desc = ""
    else:
        
        # basic check information for any upload
        project = db((db.project_id.project_details_id == record.project_id) &
                     (db.project_id.id == db.project_details.project_id)).select(db.project_details.title).first()
        
        chk_info = [_row('File name', record.file_name),
                    _row('File size', '{:0.2f} MB'.format(record.file_size / 1024.0 ** 2)),
                    _row('Uploaded', record.upload_datetime.strftime('%Y-%m-%d %H:%M')),
                    _row('Project', '(' + str(record.project_id) + ') ' + project.title)]
        
        # Status check
        chk_stat = [_row('Check outcome', CAT(approval_icons[record.dataset_check_outcome],
                                              XML('&nbsp') * 3, record.dataset_check_outcome)),
                    _row('Check report', A('View details', _href='#show_check', **{'_data-toggle': 'collapse'}))]
        
        # Check report
        chk_rprt =  DIV(DIV(XML(record.dataset_check_report), _class="panel-body"),
                        _id="show_check", _class="panel-collapse collapse")
        
        # No description unless created further down
        dataset_desc = ""
        
        if record.dataset_check_outcome == 'PENDING':
            # Set the heading for the form
            panel_head = DIV(DIV(H4('Dataset awaiting verification', _class="panel-title col-sm-8"),
                                 _class='row'),
                             _class="panel-heading")
            # Don't display the form or the check report
            form = ""
            chk_rprt = ""
        
        elif record.dataset_check_outcome == 'FAIL' or record.dataset_check_outcome == 'ERROR':
            # Set the heading for the form
            panel_head = DIV(DIV(H4('Dataset did not pass verification', _class="panel-title col-sm-8"),
                                 _class='row'),
                             _class="panel-heading")
            
            # include the status outcome
            chk_info += chk_stat
        
        elif record.dataset_check_outcome == 'PASS':
            
            # prepare the dataset description
            metadata = record.dataset_metadata
            desc_content = XML(_dataset_description(record))
            
            dataset_desc = CAT(_row('Dataset description', A('View details', _href='#show_desc', 
                                                             **{'_data-toggle': 'collapse'})),
                                DIV(DIV(DIV(desc_content, _class="well"), _class='container'),
                                    _id="show_desc", _class="panel-collapse collapse"))
            
            if record.zenodo_submission_status == 'ZEN_PEND':
                # Set the heading for the form
                panel_head = DIV(DIV(H4('Dataset awaiting publication', _class="panel-title col-sm-8"),
                                     _class='row'),
                                 _class="panel-heading")
                # include the status outcome
                chk_info += chk_stat
                # don't show the form
                form = ''
            
            elif record.zenodo_submission_status == 'ZEN_PASS':
                # Set the heading for the form
                panel_head = DIV(DIV(H4('Dataset published', _class="panel-title col-sm-8"),
                                     _class='row'),
                                 _class="panel-heading")
                # include the status outcome
                chk_info += chk_stat
                # publication_status - put right at the top (partly so that it doesn't have to
                # go below the outcome panel-collapse, and complicate the structure)
                chk_info = [_row('Zenodo URL', A(record.zenodo_doi, _href=record.zenodo_doi))] + chk_info
                # don't show the form
                form = ''
        
        # unpack the rows into a panel
        chk_panel = DIV(*chk_info, _class='panel_body')
    
    form = DIV(panel_head, chk_panel, chk_rprt, dataset_desc, form, _class="panel panel-default")
    
    return dict(form=form)


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
    elif request.vars.file.filename[-5:] != '.xlsx':
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
        
        # # has this file already been submitted?
        # hash_match = db(db.datasets.file_hash == form.vars.file_hash).select()
        # if len(hash_match):
        #      form.errors.file = "An identical file has already been submitted"


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
    
    dataset_id = request.vars['dataset_id']
    email = request.vars['email']
    manage = 'manage' in request.vars
    err = []
    
    if dataset_id is None:
        err += ["Record ID missing"]
    else:
        try:
            dataset_id = int(dataset_id)
        except ValueError:
            err += ["Record ID not an integer"]
    
    if email is None:
        err += ["Email option missing"]
    elif not email in ['0', '1']:
        err += ["Email option must be 0 or 1"]
    else:
        email = True if email == '1' else False
    
    if len(err) == 0:
        res = verify_dataset(dataset_id, email)
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
    on a dataset with a given row id.
    """
    
    record_id = request.vars['id']
    manage = 'manage' in request.vars
    err = []
    
    if record_id is None:
        err += ["Record ID missing"]
    else:
        try:
            record_id = int(record_id)
        except ValueError:
            err += ["Record ID not an integer"]
    
    if len(err) == 0:
        res = submit_dataset_to_zenodo(record_id)
    else:
        res = ', '.join(err)
    
    if manage:
        session.flash = res
        redirect(URL('datasets','administer_datasets'))
    else:
        return res


@auth.requires_membership('admin')
def run_delete_dataset():
    """
    Controller to allow an admin to delete unpublished datasets.
    """
    
    record_id = request.vars['id']
    manage = 'manage' in request.vars
    err = []
    
    if record_id is None:
        err += ["Record ID missing"]
    else:
        try:
            record_id = int(record_id)
        except ValueError:
            err += ["Record ID not an integer"]
    
    if len(err) == 0:
        record = db.datasets[record_id]
        if record is None:
            err += ["Invalid record ID"]
    else:
        record = None
    
    # now double check we're not doing this to a published dataset
    if record is not None and record.zenodo_submission_status == 'ZEN_PASS':
        err += ["Dataset published: not deletable"]
    
    if len(err) == 0:
        res = record.delete_record()
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
    metadata record for a dataset passed as an id
    """
    
    dataset_id = request.vars['dataset_id']
    
    if dataset_id is None:
        return XML("No dataset id provided")
    
    try:
        dataset_id = int(dataset_id)
    except ValueError:
        return XML("Non-integer dataset id")
    
    record = db.datasets[dataset_id]
    
    if record is None:
        return XML("Invalid dataset id")
    else:
        xml = generate_inspire_xml(record)
        raise HTTP(200, xml,
                   **{'Content-Type':'text/xml',
                      'Content-Disposition': 'attachment;filename={}.xml;'.format(record.zenodo_metadata['doi'])})
    