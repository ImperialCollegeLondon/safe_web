import shutil
import hashlib
import datetime
import safe_dataset_checker
from gluon.contenttype import contenttype

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
    db.datasets.zenodo_version_badge.represent = lambda value, row:  A(IMG(_src=value), _href=row.zenodo_version_doi)
    db.datasets.zenodo_version_doi.readable = False
    
    # button to link to custom view
    links = [dict(header = '', body = lambda row: A('Details',_class='button btn btn-sm btn-default'
                  ,_href=URL("datasets","view_dataset", vars={'id': row.id})))]

    # Get the ids of the most recently published version of each dataset_id
    records = db.executesql("""select id from datasets d1
                                inner join (
                                    select max(zenodo_submission_date) mrp,
                                        dataset_id
                                    from datasets
                                    where zenodo_submission_status = 'ZEN_PASS'
                                    group by dataset_id) d2
                                  on d1.dataset_id = d2.dataset_id
                                  and d1.zenodo_submission_date = d2.mrp;""")
    records = (r[0] for r in records)
    
    # Display those records as a grid
    form = SQLFORM.grid(db.datasets.id.belongs(records),
                        fields = [db.datasets.project_id,
                                  # db.datasets.dataset_id,
                                  # db.datasets.version,
                                  db.datasets.zenodo_submission_date,
                                  db.datasets.dataset_title,
                                  db.datasets.zenodo_version_badge,
                                  db.datasets.zenodo_version_doi],
                        headers = {'datasets.zenodo_version_badge': 'DOI',
                                   'datasets.project_id': 'Project',
                                   'datasets.zenodo_submission_date': 'Publication date'},
                        orderby = [~ db.datasets.zenodo_submission_date],
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
    View of a specific version of a dataset, taking the record id as the
    id parameter, but which also shows the other versions of the dataset.
    """
    
    ds_id = request.vars['id']
    record = db.datasets[ds_id]
    
    if ds_id is None:
        # no id provided
        record = None
    elif record is None:
        # non-existent id provided
        session.flash = "Database record id does not exist"
        redirect(URL('datasets','view_datasets'))
    
    # get the version history
    qry = ((db.datasets.dataset_id == record.dataset_id) &
           (db.datasets.zenodo_submission_status == 'ZEN_PASS'))
    
    history = db(qry).select(db.datasets.id,
                             db.datasets.zenodo_submission_date,
                             db.datasets.uploader_id,
                             db.datasets.zenodo_version_badge,
                             db.datasets.zenodo_version_doi,
                             orderby= ~ db.datasets.zenodo_submission_date)
    
    # style that into a table showing the currently viewed version

    view = SPAN(_class="glyphicon glyphicon-eye-open", 
                   _style="color:green;font-size: 1.4em;")
    alt = SPAN(_class="glyphicon glyphicon-eye-close", 
                    _style="color:grey;font-size: 1.4em;", 
                    _title='View this version')
    
    history_table = TABLE(TR(TH('Viewing'), TH('Version publication date'), 
                             TH('Uploaded by'), TH('Zenodo DOI')),
                          *[TR(TD(view) if r.id == int(ds_id) else TD(A(alt, _href=URL(vars={'id': r.id}))),
                               TD(r.zenodo_submission_date),
                               TD(r.uploader_id.first_name + ' ' + r.uploader_id.last_name),
                               TD(A(IMG(_src=r.zenodo_version_badge), 
                                    _href=r.zenodo_version_doi)))
                            for r in history],
                         _width='100%', _class='table table-striped table-bordered')

    # get the description
    description = XML(_dataset_description(record, include_gemini=True))

    return(dict(record=record, description=description, 
                history_table=history_table))


@auth.requires_membership('admin')
def administer_datasets():
    
    """
    Grid view to display datasets to admin.
    """
    
    # format fields for the display, giving the check outcome and zenodo publishing status as icons.
    db.datasets.project_id.represent = lambda value, row: A(value, _href=URL('projects','project_view', args=[value])) 
    db.datasets.dataset_check_outcome.represent =  lambda value, row: approval_icons[value]
    db.datasets.zenodo_submission_status.represent =  lambda value, row: approval_icons[value]
    
    # alter the file representation to add the dataset id as a variable to the download
    db.datasets.file.represent = lambda value, row: A('Download file', _href=URL('datasets', 'download_dataset', row.file, vars={'dataset_id': row.dataset_id}))
    
    # add buttons to provide options
    # - run check (can only be run if file has not passed)
    def _run_check(row):
        if row.dataset_check_outcome == 'PASS':
            btn =  A('Check', _class='button btn btn-default disabled',
                     _style='padding: 3px 10px 3px 10px')
        else:
            btn =  A('Check', _class='button btn btn-default',
                     _href=URL("datasets","run_verify_dataset", vars={'record_id':row.id, 'email':0, 'manage':''}),
                     _style='padding: 3px 10px 3px 10px;')
        return btn
    
    # - run publish (can only be run if file has passed and not yet been published)
    def _run_publish(row):
        if row.dataset_check_outcome != 'PASS' or row.zenodo_submission_status == 'ZEN_PASS':
            btn =  A('Publish', _class='button btn btn-default disabled',
                     _style='padding: 3px 10px 3px 10px')
        else:
            btn =  A('Publish', _class='button btn btn-default',
                     _href=URL("datasets","run_submit_dataset_to_zenodo", vars={'id':row.id, 'manage':''}),
                     _style='padding: 3px 10px 3px 10px;')
        return btn
    
    # - submit page link
    def _resubmit(row):
        btn =  A('Resubmit', _class='button btn btn-default',
                  _href=URL("datasets","submit_dataset", vars={'dataset_id':row.dataset_id}),
                     _style='padding: 3px 10px 3px 10px;')
        return btn
    
    links = [dict(header = '', body = lambda row: _run_check(row)),
             dict(header = '', body = lambda row: _run_publish(row)),
             dict(header = '', body = lambda row: _resubmit(row))]
    
    # provide a grid display of current datasets
    form = SQLFORM.grid(db.datasets.current == True,
                        fields = [db.datasets.dataset_id,
                                  db.datasets.version,
                                  db.datasets.project_id,
                                  db.datasets.upload_datetime,
                                  db.datasets.uploader_id,
                                  db.datasets.dataset_title,
                                  db.datasets.dataset_check_outcome,
                                  db.datasets.zenodo_submission_status],
                        headers = {'datasets.upload_datetime': 'Upload date',
                                   'datasets.dataset_check_outcome': 'Format status',
                                   'datasets.zenodo_submission_status': 'Published'},
                        orderby = [~ db.datasets.upload_datetime],
                        links = links,
                        maxtextlength = 100,
                        deletable=False,
                        editable=False,
                        details=True,
                        create=False,
                        csv=False)
    
    return dict(form=form)


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
    3) That provides the opportunity to replace the file with an updated one
    4) Once it passes, the website admin will check it and publish it.
    
    If users have a file that they think should pass, they can contact the
    website admin team. It may be that the validator program needs modifying!
    """
    
    # controller has one variable: dataset_id
    ds_id = request.vars['dataset_id']
    
    # get the records associated with this ds_id and the uploaders,
    # which will the original owner and any admins
    qry = db.datasets.dataset_id == ds_id
    records = db(qry).select(orderby= ~ db.datasets.version)
    owners = [rw.uploader_id for rw in records]
    
    # check that ds_id makes sense and the user has the right to access the form
    if ds_id is None:
        # no id provided, so new form and draw a new id
        record = None
    elif records is None:
        # non-existent id provided
        session.flash = "Database record id does not exist"
        redirect(URL('datasets','view_datasets'))
    elif auth.user.id not in owners and not auth.has_membership('admin'):
        # check if uploader is trying to view this submission
        session.flash = "Dataset uploaded by a different user"
        redirect(URL('datasets','view_datasets'))
    else:
        # get the record with the most recent version, which 
        # will be the first row
        record = records.first()
        new_ds_id = record.dataset_id
    
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
    db.datasets.project_id.requires = IS_IN_DB(query, 'project_details.project_id',
                                              '%(project_id)s: %(title)s',
                                               zero='Select project.')
    
    # Setup the form
    form = SQLFORM(db.datasets, 
                   record = record, 
                   fields=['project_id', 'file'],
                   showid=False,
                   deletable=False,
                   button='Upload')
    
    # Validate the form: bespoke data entry
    if form.validate(onvalidation=validate_dataset_upload):
        
        # Get new blank record to hold the dataset
        new_id = db.datasets.insert()
        new_record = db.datasets[new_id]
        
        # set the fields that differ if this is new dataset or an update
        if record is not None:
            # uploading a new version. If the dataset version is already 
            # published, then we need to use a previous Zenodo record id
            # to launch a new draft deposit from the Zenodo API.
            
            if record.zenodo_record_id is not None:
                # zenodo record id is only populated on publication, so
                # the parent record here was successful
                parent = record.zenodo_record_id
            else:
                # otherwise, what is currently in the parent record,
                # which is either none or the last successful record
                parent = record.zenodo_parent_id
            
            ds_id = record.dataset_id
            new_record.update(dataset_id = ds_id,
                              version = record.version + 1,
                              project_id = form.vars.project_id,
                              zenodo_parent_id = parent)
            
            # previous version loses its current status
            record.update_record(current=False)
        else:
            # get a value from the dataset_id table
            ds_id = db.dataset_id.insert(created=datetime.datetime.now())
            new_record.update(dataset_id = ds_id,
                              project_id = form.vars.project_id)
        
        # now update the other fields and commit the updates
        new_record.uploader_id = auth.user.id
        new_record.file_name = form.vars.file_name
        new_record.file_hash = form.vars.file_hash
        new_record.file_size = form.vars.file_size
        new_record.upload_datetime = datetime.datetime.now()
        new_record.file = form.vars.file
        new_record.update_record()
        
        # I can't figure out how to stop the FORM automatically saving the file
        # under its safe name in the default directory, so now move it
        dataset_dir = os.path.join(request.folder, 'uploads', 'datasets', str(ds_id))
        if not os.path.exists(dataset_dir):
            os.makedirs(dataset_dir)
        
        src = os.path.join(request.folder, 'uploads', 'datasets', form.vars.file)
        dst = os.path.join(request.folder, 'uploads', 'datasets', str(ds_id), form.vars.file)
        shutil.move(src, dst)
        
        # schedule the dataset check
        #  - set timeout to extend the default of 60 seconds.
        #  - no start_time, so defaults to now.
        task = scheduler.queue_task('verify_dataset', 
                                    pvars = {'record_id': new_id, 'email': True},
                                    timeout = 5*60,
                                    repeats=1,
                                    immediate=True)
        
        # notify upload has worked
        session.flash = ('Upload successful. A validation check will be run and '
                          'you will get an email with the results when it finishes.')
        
        # send to the updated page
        redirect(URL('datasets', 'submit_dataset', vars={'dataset_id': new_record.dataset_id}))
    
    elif form.errors:
        response.flash = 'Errors in upload'
    
    # Package the page contents - this is a panel that contains
    # 1) Information on the uploaded file verification (if a dataset id is provided)
    # 2) Information on the publication status (if a dataset id is provided and it is published)
    # 3a) Form controls to validate a replacement file (if check outcome is Fail or Error)
    # 3b) Form controls to create a new version (if file is published)
    
    # Tone down the height of the project selector
    form.custom.widget.project_id['_style'] = 'height:30px'
    
    form =  DIV(form.custom.begin, 
                DIV(DIV(B('Project'), _class="col-sm-3" ),
                    DIV(form.custom.widget.project_id,  _class="col-sm-9"),
                    _class='row', _style='margin:5px 10px'),
                DIV(DIV(B('File'), _class="col-sm-3" ),
                    DIV(form.custom.widget.file,  _class="col-sm-6"),
                    DIV(DIV(form.custom.submit, _class='pull-right'), _class="col-sm-3"),
                    _class='row', _style='margin:10px 10px'),
                   form.custom.end)
    
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
        # There is no file check information, report, description or resubmit header
        chk_panel = ""
        chk_rprt = ""
        dataset_desc = ""
        resubmit_head = ""
    else:
        
        # basic check information for any upload
        project = db((db.project_id.id == record.project_id) &
                     (db.project_id.project_details_id == db.project_details.id)).select(db.project_details.title).first()
        
        chk_info = [_row('Project assignment', '(' + str(record.project_id) + ') ' + project.title),
                    _row('File name', record.file_name),
                    _row('File size', '{:0.2f} MB'.format(record.file_size / 1024.0 ** 2)),
                    _row('Uploaded', record.upload_datetime.strftime('%Y-%m-%d %H:%M')),
                    _row('Current version', record.version)]
        
        # Status check
        chk_stat = [_row('Check outcome', CAT(approval_icons[record.dataset_check_outcome],
                                              XML('&nbsp') * 3, record.dataset_check_outcome)),
                    _row('Check report', A('View details', _href='#show_check', **{'_data-toggle': 'collapse'}))]
        
        # Check report
        chk_rprt =  DIV(DIV(XML(record.dataset_check_report), _class="panel-body"),
                        _id="show_check", _class="panel-collapse collapse")
        
        # Resubmit header is only needed when a dataset version is checked or published
        resubmit_head = ""
        
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
        
        elif record.dataset_check_outcome == 'FAIL':
            # Set the heading for the form
            panel_head = DIV(DIV(H4('Dataset failed verification', _class="panel-title col-sm-8"),
                                 _class='row'),
                             _class="panel-heading")
            
            # include the status outcome and the resubmit panel is available
            chk_info += chk_stat
            resubmit_head = DIV('Upload a new version', _class='panel-heading')
            
        elif record.dataset_check_outcome == 'ERROR':
            # Set the heading for the form
            panel_head = DIV(DIV(H4('Dataset verification error', _class="panel-title col-sm-8"),
                                 _class='row'),
                             _class="panel-heading")
            
            form  = DIV(P('There has been a problem with verification process on your dataset. '
                          'Please bear with us while we investigate this and then update your '
                          'dataset status'), _class='panel-body')
            
        elif record.dataset_check_outcome == 'PASS':
            
            # prepare the dataset description
            metadata = record.dataset_metadata
            if record.zenodo_submission_status == 'ZEN_PASS':
                desc_content = XML(_dataset_description(record, include_gemini=True))
            else:
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
                # New versions can still be submitted
                resubmit_head = DIV('Upload a new version', _class='panel-heading')
                
            elif record.zenodo_submission_status == 'ZEN_FAIL':
                # Set the heading for the form
                panel_head = DIV(DIV(H4('Dataset publication failed', _class="panel-title col-sm-8"),
                                     _class='row'),
                                 _class="panel-heading")
                # include the status outcome
                chk_info += chk_stat
                # No option to resubmit
                form = ""
            elif record.zenodo_submission_status == 'ZEN_PASS':
                # Set the heading for the form
                panel_head = DIV(DIV(H4('Dataset published', _class="panel-title col-sm-12"),
                                     _class='row'),
                                 _class="panel-heading")
                # include the status outcome
                chk_info += chk_stat
                # publication_status - put right at the top (partly so that it doesn't have to
                # go below the outcome panel-collapse, and complicate the structure)
                chk_info = [_row('Version DOI', A(IMG(_src=record.zenodo_version_badge), 
                                 _href=record.zenodo_version_doi)),
                            _row('Concept DOI', A(IMG(_src=record.zenodo_concept_badge),
                                 _href=record.zenodo_concept_doi))] + chk_info
                # New versions can be submitted to a published dataset
                resubmit_head = DIV('Upload a new version', _class='panel-heading')
        
        # unpack the rows into a panel
        chk_panel = DIV(*chk_info, _class='panel_body')
    
    form = DIV(panel_head, chk_panel, chk_rprt, dataset_desc, resubmit_head, form, _class="panel panel-default")
    
    if ds_id is None:
        vsn_hist = DIV()
    else:
        # Generate a collapsible version history
        version_table = TABLE(TR(TH('Version'), TH('Date'), TH('Uploader'), 
                                 TH('Project'), TH('Name'), TH('Size'),
                                 TH('Checked'), TH('Published')), 
                            *[TR(TD(r.version), TD(r.upload_datetime), 
                                 TD(r.uploader_id), TD(r.project_id), 
                                 TD(r.file_name), TD('{0:.2f} Mb'.format(r.file_size / 1024**2.0)),
                                 TD(approval_icons[r.dataset_check_outcome]),
                                 TD(approval_icons[r.zenodo_submission_status])) 
                              for r in records],
                       _width='100%', _class='table table-striped')
    
        vsn_hist  = DIV(DIV(DIV(H4('Version history', _class="panel-title col-sm-12"),
                                _class='row'),
                            _class="panel-heading"),
                            version_table,
                        _class='panel panel-default')
    
    return dict(form=form, vsn_hist=vsn_hist)


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
        
        # Check if the file has already been published - Zenodo 
        # won't publish deposits with unchanged file complements
        if form.record is not None:
            # are there any published version
            qry = ((db.datasets.dataset_id == form.record.dataset_id) &
                   (db.datasets.zenodo_submission_status == 'ZEN_PASS'))
            pub_md5 = db(qry).select(db.datasets.file_hash)
            pub_md5 = pub_md5.column('file_hash')
            
            if form.vars.file_hash in pub_md5:
                form.errors.file = "This file has already been published to Zenodo"


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
    on a dataset with a given row id. The extra key 'sandbox' can be
    specified to publish to the Zenodo sandbox instead, but at present
    this isn't exposed anywhere except via a manual url
    """
    
    record_id = request.vars['id']
    manage = 'manage' in request.vars
    sandbox = 'sandbox' in request.vars
    err = []
    
    if record_id is None:
        err += ["Record ID missing"]
    else:
        try:
            record_id = int(record_id)
        except ValueError:
            err += ["Record ID not an integer"]
    
    if len(err) == 0:
        res = submit_dataset_to_zenodo(record_id, sandbox=sandbox)
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
    
    dataset_row_id = request.vars['id']
    
    if dataset_row_id is None:
        return XML("No dataset id provided")
    
    try:
        dataset_row_id = int(dataset_row_id)
    except ValueError:
        return XML("Non-integer dataset id")
    
    record = db.datasets[dataset_row_id]
    
    if record is None:
        return XML("Invalid dataset id")
    else:
        xml = generate_inspire_xml(record)
        raise HTTP(200, xml,
                   **{'Content-Type':'text/xml',
                      'Content-Disposition': 'attachment;filename={}.xml;'.format(record.zenodo_metadata['doi'])})
    