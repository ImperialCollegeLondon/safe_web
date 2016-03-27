import datetime

## -----------------------------------------------------------------------------
## OUTPUTS
## - controllers to view outputs and get a nicely formatted output details view
## - controllers to create new outputs and associate them with projects (or not)
## -----------------------------------------------------------------------------

def outputs():
    
    """
    This controller shows the grid view for outputs
    """
    
    # create a links object that associates a row with the image uploaded for it
    # and adds in a link button to the standalone view controller
    links = [dict(header = '', body = lambda row: IMG(_src = URL('default', 
                  'download', args = row.picture), _width = 100, _height = 100)),
             dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                       SPAN('View', _class="buttontext button"),
                                       _class="button btn btn-default", 
                                       _href=URL("outputs","output_details", args=[row.id], user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;'))]
    
    
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


def output_details():
    
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
    
    membership_panel = LOAD(request.controller,
                            'view_output_membership.html',
                             args=[output_id],
                             ajax=True)
    
    # if the user is a member of the outout then include a list of users to add
    output_members = db(db.output_members.output_id == output_id).select()
    output_member_ids = [r.user_id for r in output_members]
    
    if auth.is_logged_in() and auth.user.id in output_member_ids:
        
        # lock down the value of the output_id locally
        db.output_members.output_id.default = output_id
        
        addform = SQLFORM(db.output_members, 
                          fields = ['user_id'])
        
        if addform.process().accepted:
            response.flash = CENTER(B('New output member added.'), _style='color: green')
            # could email the new member here
            pass
    
    else:
        addform = None
    
    return dict(output = output, 
                projects = projects, 
                membership_panel = membership_panel, 
                addform = addform)


def view_output_membership():
    
    """
    Present a members of a given output
    """
    
    # retrieve the user id from the page arguments passed by the button
    output_id = request.args(0)
    
    form = SQLFORM.grid((db.output_members.output_id == output_id),
                       args=[output_id],
                       fields = [db.output_members.user_id],
                       maxtextlength=250,
                       searchable=False,
                       deletable=False,
                       details=False,
                       selectable=False,
                       create=False,
                       editable=False,
                       csv=False,
                       user_signature=False
                       )  # change to True in production
    return form


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


@auth.requires_login()
def new_output():
    
    """
    This controller shows a SQLFORM to submit an upload. 
    
    It also allows a user to tag that upload to a project and only
    projects for which the logged in user is a member are available.
    
    Because this involves two tables (outputs for details and 
    projects for mapping to projects), we'll use SQLFORM.factory
    
    The controller then passes the response through validation before 
    sending a confirmation email out.
    """
    
    # Restrict the project choices available from projects
    # - find the acceptable project ID numbers
    valid_ids = db(db.project_members.user_id == auth.user.id)._select(db.project_members.project_id)
    query = db(db.project.id.belongs(valid_ids))
    # - modify the outputs project_id requirements within this controller
    db.project.id.requires = IS_EMPTY_OR(IS_IN_DB(query, db.project.id, '%(title)s'))
    
    # Help the user by explaining why project ID might be blank
    if query.count() == 0:
        project_comment = ('You are not registered as a member of any projects'
                           ' but can upload non-project outputs')
    else:
        project_comment = ('Choose from the projects you are a member of or leave blank'
                           ' for non-project outputs')
    
    # create a set of fields to choose from: a list containing a single field with
    # constrained set of project titles, to which we append fields from outputs
    fields = [Field('project_id', 'reference project', 
                         requires = IS_EMPTY_OR(IS_IN_DB(query, db.project.id, '%(title)s')),
                         comment = project_comment)]
    hidden_fields = ['creator_id', 'submission_date', 'admin_status',
                     'admin_id', 'admin_notes', 'admin_decision_date']
    output_fields = [f for f in db.outputs if f.name not in hidden_fields]
    fields.extend(output_fields)
    
    # continue with form - this has to be defined on the fly
    # in order to bring in the project id choices, which are intercepted in accept()
    form = SQLFORM.factory(*fields,
                           submit_button = 'Submit and add output members')
    
    # now intercept and parse the various inputs
    if form.process(onvalidation=validate_new_output).accepted:
        
        # add the content to the database, first filtering out the output fields
        # and getting the row id of the new entry
        new_output_id = db.outputs.insert(**db.outputs._filter_fields(form.vars))
        
        # pair it with a project if requested
        if form.vars.project_id is not None:
            db.project_outputs.insert(project_id = form.vars.project_id,
                                      output_id = new_output_id,
                                      added_by = auth.user.id,
                                      date_added = datetime.date.today().isoformat())
        
        # load the creator into the output members table
        db.output_members.insert(output_id = new_output_id,
                                 user_id = auth.user.id)
        
        # Signal success and email the proposer
        mail.send(to=auth.user.email,
           subject='SAFE project output uploaded',
           message='Many thanks for uploading your output')
        session.flash = CENTER(B('SAFE project output successfully submitted.'), _style='color: green')
        
        # send back to the outputs page
        redirect(URL('outputs', 'outputs'))
    elif form.errors:
        response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
    else:
        pass

    return dict(form=form)


def validate_new_output(form):
    
    """
    Add uploader id and date
    TODO -  could check the file isn't ridiculously big but once it is at this 
            point, in this controller, it has already been uploaded. So dim to 
            block it here.
    """
    
    form.vars.creator_id = auth.user_id
    form.vars.submission_date =  datetime.date.today().isoformat()



@auth.requires_login()
def add_output_to_project():
    
    """
    Function to allow a user to add an output to a project.
    Restrictions here are tricky - only one person 'owns' an output
    so could restrict to them adding an output to a project they belong to
    but that is a bit restrictive. So, currently any project member can claim
    any output (currently with no approval mechanism)
    """
    
    # Restrict the project choices available from projects
    # - find the acceptable project ID numbers
    valid_ids = db(db.project_members.user_id == auth.user.id)._select(db.project_members.project_id)
    query = db.project.id.belongs(valid_ids)
    
    # - modify the outputs project_id requirements within this controller
    db.project_outputs.project_id.requires = IS_IN_DB(db(query), db.project.id, '%(title)s')
    
    form = SQLFORM(db.project_outputs, 
                   fields = ['project_id', 'output_id'],
                   show_id=False,
                   )
    
    # now intercept and parse the various inputs
    if form.process(onvalidation=validate_add_output_to_project).accepted:
        session.flash = CENTER(B('Output successfully added to project.'), _style='color: green')
        redirect(URL('outputs', 'outputs'))
    elif form.errors:
        response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
    else:
        pass
    
    
    return dict(form=form)



def validate_add_output_to_project(form):
    
    """
    Add the id and date added to the project
    """
    
    form.vars.added_by = auth.user_id
    form.vars.date_added =  datetime.date.today().isoformat()



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
    db.outputs.description.readable = False
    db.outputs.citation.writable = False
    db.outputs.format.writable = False
    db.outputs.creator_id.writable = False
    db.outputs.submission_date.writable = False
    db.outputs.description.writable = False
    # hide the background admin fields
    db.outputs.admin_id.readable = False
    db.outputs.admin_id.writable = False
    db.outputs.admin_decision_date.readable = False
    db.outputs.admin_decision_date.writable = False
    
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
                         onvalidation = validate_administer_outputs,
                         onupdate = update_administer_outputs,
                         )
    
    return dict(form=form)


def validate_administer_outputs(form):
    
    # validation handles any checking (none here) and also any 
    # amendments to the form variable  - adding user and date of admin
    form.vars.admin_id = auth.user_id
    form.vars.admin_decision_date =  datetime.date.today().isoformat()


def update_administer_outputs(form):
    
    # Email the decision to the proposer
    # TODO - create and link to a Google Calendar for volunteer periods
    
    # retrieve the whole form record to get at the creator details
    creator = form.record.creator_id
    
    # set a flash message
    flash_message  = CENTER(B('Decision emailed to project member at {}.'.format(creator.email)), _style='color: green')
    
    if form.vars.admin_status == 'Approved':
        mail.send(to=creator.email,
                  subject='SAFE output submission',
                  message='Dear {},\n\nLucky template\n\n {}'.format(creator.first_name, form.vars.admin_notes))
        session.flash = flash_message
    elif form.vars.admin_status == 'Rejected':
        mail.send(to=creator.email,
                  subject='SAFE output submission',
                  message='Dear {},\n\nUnlucky template\n\n {}'.format(creator.first_name, form.vars.admin_notes))
        session.flash = flash_message
    else:
        pass
    

