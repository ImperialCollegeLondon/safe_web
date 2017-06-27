import hashlib
import datetime
import openpyxl
import safe_dataset_checker


#@auth.requires_membership('admin')

@auth.requires_login()
def view_datasets():

    # # get passed datasets
    # qry = db(db.dataset)
    
    # provide a grid display
    form = SQLFORM.grid(db.datasets.check_outcome == 'FAIL',
                        fields = [db.datasets.project_id,
                                  db.datasets.uploader_id,
                                  db.datasets.file_name],
                        maxtextlength = 100,
                        deletable=False,
                        editable=False,
                        details=False,
                        create=False,
                        csv=False)
    
    return dict(form=form)


@auth.requires_login()
def submit_dataset():

    """
    Controller to upload a dataset to the website for checking
    """
    
    # restrict choice of projects for standard users
    query = db((db.project_members.user_id == auth.user.id) &
               (db.project_members.project_id == db.project_id.id) &
               (db.project_id.project_details_id == db.project_details.id))
    
    # TODO - figure out how to get this displayed as (#) Title
    #  '(%(db.project_id.id)s) %(db.project_details.title)s',

    db.datasets.project_id.requires = IS_IN_DB(query, 'project_details.project_id', '(%(project_id)s) %(title)s',
                                               zero='Select project.')
    
    form = SQLFORM(db.datasets, fields=['project_id', 'file'])
    
    # Is there a file - this is None on load and can be 'str' if submit is pressed
    # without a file selected. With a file selected type(file) is 'instance'
    if request.vars.file != None and not isinstance(request.vars.file, str):
        form.vars.file_name = request.vars.file.filename
        form.vars.file_hash = hashlib.sha256(request.vars.file.value).hexdigest()
        form.vars.file_size= len(request.vars.file.value)
    if form.process(onvalidation=validate_dataset_upload).accepted:
        # notify upload has worked
        response.flash = ('Upload successful. A validation check will be run and '
                          'you will get an email with the results when it finishes.')
        
        # schedule the file check
        scheduler.queue_task('verify_dataset',
                             start_time=datetime.datetime.now(),
                             pvars = {'id': form.vars.id},
                             repeats=0)
    
    elif form.errors:
        response.flash = 'Errors in upload'

    return dict(form=form)

@auth.requires_membership('admin')
def run_dataset_check():
    """
    Controller to allow an admin to (re)run dataset verification
    on a dataset with a given row id.
    """
    
    res = verify_dataset(request.vars['id'])
    
    return res


@auth.requires_membership('admin')
def run_submit_dataset_to_zenodo():
    """
    Controller to allow an admin to (re)run dataset verification
    on a dataset with a given row id.
    """
    
    res = submit_dataset_to_zenodo(request.vars['id'])
    
    return res



def validate_dataset_upload(form):
    """
    Validation function for the dataset upload form
    Args:
        form: The SQLFORM object returned
    """
    
    # Check that the file isn't a string, which it is when submit is pushed
    # with no file selected.
    if isinstance(form.vars.file, str):
        form.errors.file = "No file selected"
    else:
        # look for valid files
        if form.vars.file_name[-5:] != '.xlsx':
            form.errors.file = "File is not in XLSX format"
        
        # # has this file already been submitted?
        # hash_match = db(db.datasets.file_hash == form.vars.file_hash).select()
        # if len(hash_match):
        #      form.errors.file = "An identical file has already been submitted"
        
        # input a bunch of housekeeping information
        form.vars.uploader_id = auth.user.id
        form.vars.upload_datetime = datetime.datetime.utcnow().isoformat()
