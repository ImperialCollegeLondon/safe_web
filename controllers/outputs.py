import datetime

## -----------------------------------------------------------------------------
## OUTPUTS
## - public controllers to view outputs and get a nicely formatted output details view
## -----------------------------------------------------------------------------

def outputs():
    
    """
    This controller shows the grid view for outputs
    """
    
    # create a links object that associates a row with the image uploaded for it
    # and adds in a link button to the standalone view controller
    links = [dict(header = '', body = lambda row: IMG(_src = URL('default', 
                  'download', args = row.picture), _width = 100, _height = 100)),
            # dict(header = '', 
            #      body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
            #                           SPAN('View', _class="buttontext button"),
            #                           _class="button btn btn-default", 
            #                           _href=URL("outputs","view_output", args=[row.id], user_signature=True),
            #                           _style='padding: 3px 5px 3px 5px;'))
            ]
    
    
    # we need the picture field in the fields fetched, in order to look up
    # the picture to display as a row using links, but we don't want to actually 
    # show the field itself, so:
    db.outputs.picture.readable = False
    
    # subset down to approved projects
    query = (db.outputs.admin_status == 'Approved')
    
    form = SQLFORM.grid(query = query, csv=False, 
                        fields=[db.outputs.picture, db.outputs.title, db.outputs.format],
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False,
                        links=links,
                        links_placement='left',
                        formargs= {'fields': ['title', 'citation','format', 'file',
                                              'description','doi', 'url'],
                                   'showid': False})
   
    return dict(form=form)


def view_output():
    
    # retrieve the output id from the page arguments passed by the button
    # and then get the row and send it to the view
    output_id = request.args(0)
    output = db(db.outputs.id == output_id).select()[0]
     
    # set up a membership and projects panel 
    # - note that these view don't exist, they're just a mechanism to load controllers
    #   and get the contents of sub tables
    projects = LOAD(request.controller,
                    'get_output_projects.html',
                    args=[output_id],
                    ajax=True)
    
    return dict(output = output, 
                projects = projects)


def get_output_projects():
    
    """
    Internal controller, gathering a form requested by LOAD
    """
    
    # retrieve the output id from the page arguments passed by LOAD
    # and find the set of associated projects 
    output_id = request.args(0)
    associated_projects = db(db.project_outputs.output_id == output_id)._select(db.project_outputs.project_id)
    query = db.project.id.belongs(associated_projects)
    
    form = SQLFORM.grid(query,
                       fields = [db.project.title],
                       maxtextlength=250,
                       searchable=False,
                       args = [output_id],
                       deletable=False,
                       details=False,
                       selectable=False,
                       create=False,
                       editable=False,
                       csv=False,
                       #user_signature=False
                       )  # change to True in production
    
    return form

## -----------------------------------------------------------------------------
## OUTPUT CREATION AND EDITING
## - user controllers create new outputs, edit existing ones and pair to projects
## -----------------------------------------------------------------------------


@auth.requires_login()
def output_details():
    
    """
    This controller provides an interface to create a new output 
    (when no request arguments are passed)
    
    shows a SQLFORM to submit an upload and it also exposes a form
    for existing e     a user to tag that upload to a project and only
    projects for which the logged in user is a member are available.
    
    The controller then passes the response through validation before 
    sending a confirmation email out.
    """
    
    # do we have a request for an existing blog post
    output_id = request.args(0)
    
    if output_id is not None:
        record = db.outputs(output_id)
    else:
        record = None
        
    if output_id is not None and record is None:
        
        # avoid unknown blogs
        session.flash = B(CENTER('Invalid output id'), _style='color:red;')
        redirect(URL('outputs','outputs'))
        
    elif output_id is not None and record.user_id <> auth.user.id:
        # security check to stop people editing other users outputs
        session.flash = CENTER(B('You do not have permission to edit these output details.'), _style='color: red')
        redirect(URL('outputs','outputs', args=output_id))
        
    else:
        
        # create the form
        form = SQLFORM(db.outputs, record = output_id,
                       fields = ['picture','file','title','description',
                                 'format', 'citation', 'doi','url'],
                       showid=False,
                       submit_button = 'Submit output')
    
        # now intercept and parse the various inputs
        if form.process(onvalidation=validate_output_details).accepted:
            
            # Signal success and email the proposer
            mail.send(to=auth.user.email,
               subject='SAFE project output created/edited',
               message='Many thanks for uploading your output')
            session.flash = CENTER(B('SAFE project output created/edited.'), _style='color: green')
            
            # add a comment to the history
            new_history = '[{} {}, {}, {}]\\n'.format(auth.user.first_name,
                           auth.user.last_name, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                           'Output created' if output_id is None else "Output edited")
            
            # reload the record
            output_record = db.outputs(form.vars.id)
            
            if output_record.admin_history is None or output_record.admin_history == '':
                output_record.update_record(admin_history = new_history)
            else:
                output_record.update_record(admin_history = output_record.admin_history + '\\n' + new_history)
            
            # now send to the output_details page for the form we've just created
            redirect(URL('outputs', 'output_details', args=form.vars.id))
            
        elif form.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass

        # Now handle adding projects:
        # - provide records of the projects already added and a restricted set
        #   of projects that the user can chose
        if output_id is not None:
            
            # current projects
            current_projects = db(db.project_outputs.output_id == output_id).select()
            
            # restrict the SQLFORM to:
            # a) projects the user is a member of, and which
            # b) are not already linked to this output
            valid_ids = db(db.project_members.user_id == auth.user.id)._select(db.project_members.project_id)
            already_selected = db(db.project_outputs.output_id == output_id)._select(db.project_outputs.project_id)
            query = db(db.project.id.belongs(valid_ids) & ~ db.project.id.belongs(already_selected))
            db.project_outputs.project_id.requires = IS_IN_DB(query, db.project.id, '%(title)s')
            
            # and can only add records to this id
            db.project_outputs.output_id.default = output_id
            
            # create the form
            add_project = SQLFORM(db.project_outputs, fields=['project_id'])
        else:
            current_projects = None
            add_project = None
        
        # - and the processor to add_projects to existing outputs
        # TODO - does adding removing projects add to the admin hisyory
        if add_project is not None:
            if add_project.process(onvalidation=validate_add_project).accepted:
                session.flash = CENTER(B('Output added to new project.'), _style='color: green')
                redirect(URL('outputs', 'output_details', args=output_id))
            elif add_project.errors:
                response.flash = CENTER(B('Problem adding project.'), _style='color: red')
            else:
                pass
    
    return dict(form=form, current_projects=current_projects, add_project=add_project, record=record)


def validate_output_details(form):
    
    """
    Add uploader id and date and (re)set the approval status
    TODO -  could check the file isn't ridiculously big but once it is at this 
            point, in this controller, it has already been uploaded. So dim to 
            block it here.
    """
    
    form.vars.user_id = auth.user_id
    form.vars.submission_date =  datetime.date.today().isoformat()
    
    # update the record admin status to make it Pending
    form.vars.admin_status='Pending'


def validate_add_project(form):
    
    
    pass

@auth.requires_login()
def remove_project():

    """
    Removes a row from the project_outputs table and as such needs careful safeguarding
    against use by non-authorised people - must be a logged in as the owner of the output
    """
    
    # get the row id and look up the owner of the related output
    row_id = request.args(0)
    record = db.project_outputs(row_id)
    owner = db.outputs(record.output_id).user_id
    
    print owner
    if record is not None:
        # if the user is the output owner then ok
        if  auth.user.id == owner:
                session.flash =  CENTER(B('Project association removed from output.'), _style='color: green')
                db(db.project_outputs.id == row_id).delete()
                redirect(URL('outputs','output_details', args=record.output_id))
        else:
            session.flash =  CENTER(B('Unauthorised use of outputs/remove_project'), _style='color: red')
            redirect(URL('outputs','outputs'))
    else:
        session.flash = CENTER(B('Unknown row ID in outputs/remove_project'), _style='color: red')
        redirect(URL('outputs','outputs'))



## -----------------------------------------------------------------------------
## OUTPUTS ADMINISTRATION
## - admin controllers to approve submitted outputs.
## -----------------------------------------------------------------------------


@auth.requires_membership('admin')
def administer_outputs():

    """
    This controller handles:
     - presenting admin users with a list of pending output uploads
     - the ability to approve or reject them
    """
    
    # lock down which fields can be changed
    db.outputs.picture.writable = False
    db.outputs.file.writable = False
    db.outputs.url.writable = False
    db.outputs.doi.writable = False
    db.outputs.title.writable = False
    db.outputs.description.writable = False
    db.outputs.citation.writable = False
    db.outputs.format.writable = False
    db.outputs.user_id.writable = False
    db.outputs.submission_date.writable = False
    db.outputs.description.writable = False
    # hide legacy field and lock history
    db.outputs.legacy_output_id.readable = False
    db.outputs.legacy_output_id.writable = False
    db.outputs.admin_history.writable = False
    
    # make the administrator choose rejected or approved
    db.outputs.admin_status.requires = IS_IN_SET(['Rejected', 'Approved'])
    
    # get a query of pending requests 
    form = SQLFORM.grid(query=(db.outputs.admin_status == 'Pending'), csv=False,
                        fields=[db.outputs.title,
                                db.outputs.format],
                         maxtextlength=250,
                         deletable=False,
                         editable=True,
                         create=False,
                         details=False,
                         editargs = {'showid': False},
                         onupdate = update_administer_outputs,
                         )
    
    return dict(form=form)


def update_administer_outputs(form):
    
    # Email the decision to the proposer
    # TODO - create and link to a Google Calendar for volunteer periods
    
    # reload the record
    output_record = db.outputs(form.vars.id)
    
    # update the admin history
    # add a comment to the history
    new_history = '[{} {}, {}, {}]\\n{}\\n'.format(auth.user.first_name,
                   auth.user.last_name, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                   form.vars.admin_status, form.vars.admin_notes)
    
    if output_record.admin_history is None or output_record.admin_history == '':
        output_record.update_record(admin_history = new_history)
    else:
        output_record.update_record(admin_history = output_record.admin_history + '\\n' + new_history)
    
    # set a flash message
    flash_message  = CENTER(B('Decision emailed to project member at {}.'.format(output_record.user_id.email)), _style='color: green')
    
    if form.vars.admin_status == 'Approved':
        mail.send(to=output_record.user_id.email,
                  subject='SAFE output submission',
                  message='Dear {},\n\nLucky template\n\n {}'.format(output_record.user_id.first_name, form.vars.admin_notes))
        session.flash = flash_message
    elif form.vars.admin_status == 'Rejected':
        mail.send(to=output_record.user_id.email,
                  subject='SAFE output submission',
                  message='Dear {},\n\nUnlucky template\n\n {}'.format(output_record.user_id.first_name, form.vars.admin_notes))
        session.flash = flash_message
    else:
        pass
    

