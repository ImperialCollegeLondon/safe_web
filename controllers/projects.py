import datetime

## -----------------------------------------------------------------------------
## VIEW PROJECT CONTROLLERS
## -- uses recipe from:
##    http://www.web2pyslices.com/article/show/1542/manage-users-and-memebership-in-the-same-form
## -- This setup is moderately complicated: there is a SQLFORM.grid to display all
##    projects, but then we want the view to include project details, members and
##    outputs, so:
##      1) the SQLFORM.grid has a custom button, redirecting to ...
##      2) a custom view_project_details controller, which also loads
##      3) a controller returning a SQLFORM.grid of project_members for the project
##      4) a controller returning a SQLFORM.grid of outputs for the project
##
## -- This is all public facing, so the project_view page provides access to
##    the main areas of public interest and not the underlying resources/ethics/approval
## -----------------------------------------------------------------------------

def projects():
    
    """
    This controller shows the grid view for projects and allows
    users to look at project details but creating new ones is handled
    by a standalone form
    
    It uses a custom button to divert from the SQLFORM.grid view to a
    custom view page that displays project members and outputs as well
    """
    
    # For standard users (need a separate admin projects controller)
    # don't show the authorization fields and don't show a few behind 
    # the scenes fields
    db.project.admin_id.readable = False 
    db.project.admin_status.readable = False 
    db.project.admin_notes.readable = False 
    db.project.admin_decision_date.readable = False 
    db.project.proposer_id.readable = False 
    db.project.proposal_date.readable = False 
    db.project.data_sharing.readable = False 
    db.project.legacy_project_id.readable = False 
    
    # hide picture link - we need it in the fields, to use it in the links
    # but we don't want to show the field itself
    db.project.picture.readable = False
        
    # create a links list that:
    # 1) displays a thumbnail of the  project image
    # 2) creates a custom button to pass the row id to a custom view 
    
    links = [dict(header = '', body = lambda row: A(IMG(_src = URL('default', 
                  'download', args = row.picture), _height = 100))),
             dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                       SPAN('View', _class="buttontext button"),
                                       _class="button btn btn-default", 
                                       _href=URL("projects","project_view", args=[row.id], user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;'))]
    
    form = SQLFORM.grid(db.project, csv=False, 
                        fields=[db.project.title,
                                # db.project.start_date, 
                                # db.project.end_date, 
                                db.project.picture],
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False, 
                        details=False,
                        links=links,
                        links_placement='left',
                        formargs={'showid': False})
    
    return dict(form=form)


def project_view():
    
    """
    Custom public project view - displays the project and any members or outputs
    """
    
    # retrieve the user id from the page arguments passed by the button
    project_id = request.args(0)
    
    # control access to records based on status
    project_record = db.project(project_id)
    
    if (project_record is not None) and \
       (project_record.admin_status == 'Approved'):
    
        # set up the project form
        # TODO - what new fields to add for public consumption?
        this_project = SQLFORM(db.project, project_id,
                       fields = [#'project_home_country', 
                                 'start_date', 'end_date',
                                 'rationale', 'methods', 'research_areas'],
                       readonly=True,
                       showid=False
                      )
    
        # we want the title as a display item not in the SQLFORM
        # so it is excluded from fields above and retrieved below using the record
        title = this_project.record.title
        pic = this_project.record.picture
    
        # set up a membership panel - this uses AJAX, which is black box woo to me at the moment
        # - not that these view don't exist, they're just a mechanism to load controllers
        #   and get the contents of sub tables
        membership_panel = LOAD(request.controller,
                                'view_project_membership.html',
                                 args=[project_id],
                                 ajax=True)
    
        # set up an outputs panel
        outputs_panel = LOAD(request.controller,
                                'view_project_outputs.html',
                                 args=[project_id],
                                 ajax=True)
        
        # pass components to the view
        return dict(title=title, pic=pic,
                    this_project=this_project, 
                    membership_panel=membership_panel,
                    outputs_panel=outputs_panel)
    
    # now for non-existant records
    else:
        session.flash = CENTER(B('Invalid project id number.'), _style='color: red')
        redirect(URL('projects','projects'))

def view_project_membership():
    
    """
    Present a subset of project_members, showing users for a given project
    TODO - allow links to auth_user records? Only for login?
    """
    
    # retrieve the user id from the page arguments passed by the button
    project_id = request.args(0)
    
    form = SQLFORM.grid((db.project_members.project_id == project_id),
                       args=[project_id],
                       fields = [db.project_members.user_id,
                                 db.project_members.project_role],
                       maxtextlength=250,
                       searchable=False,
                       deletable=False,
                       details=False,
                       selectable=False,
                       create=False,
                       editable=False,
                       csv=False,
                       #user_signature=False
                       )  # change to True in production
    return form


def view_project_outputs():
    
    """
    Present a subset of outputs to the user as a grid. This is almost
    identical to view_projects, except for the built in subset to a project_id
    -- TODO - may be possible to merge these two controllers?
    -- TODO - redirect view buttons page to the already defined output view?
              output_view/view/outputs/output_id
              At the moment it pops up a subpage, but we'd want the controller back
              button to go back to the project_details.
    """
    
    # retrieve the project id from the page arguments 
    # and grab the associated projects
    project_id = request.args(0)
    associated_outputs = db(db.project_outputs.project_id == project_id)._select(db.project_outputs.output_id)
    query = db.outputs.id.belongs(associated_outputs)
    
    
    form = SQLFORM.grid(query,
                       fields=[db.outputs.title,
                               db.outputs.format],
                       maxtextlength=250,
                       args=[project_id],
                       searchable=False,
                       deletable=False,
                       details=True,
                       editable=False,
                       create=False,
                       selectable=False,
                       csv=False,
                       #user_signature=False
                       )  # change to True in production
    return form

## -----------------------------------------------------------------------------
## PROJECT DETAIL CONTROLLERS
## -- DESIGN NOTES: A project can be created by a single user, who is automatically
##                  added as a project member and coordinator. Once a new project
##                  is created via a form accept then the view is refreshed to add 
##                  a project members view.
##                  
##                  The view for this controller contains a lot of code to provide
##                  a single URL for a project that can expose either an editing
##                  interface or a detailed record for oversight
##                  
## -- TODO - extend new_project to require non-student status?
## -----------------------------------------------------------------------------

@auth.requires_login()
def project_details():

    """
    Controller to handle the managment of project proposals. This needs to be a 
    form that users can return to to fix problems etc, so this controller accepts project_id
    as an argument to reload existing records. We therefore also need access control.
    """

    # look for an existing record, otherwise a fresh start with an empty record
    project_id = request.args(0)
    if project_id is not None:
        record = db.project(project_id)
    else:
        record = None
    
    # need access control here for existing projects and provide:
    # - default readonly access to all users to allow project oversight.
    # - but give write access to project coordinator members
    
    if project_id is not None and db.project(project_id) is None:
        # avoid unknown projects
        session.flash = B(CENTER('Invalid project id'), _style='color:red;')
        redirect(URL('projects','projects'))
    else:
        
        if project_id is not None:
            project_coords = db((db.project_members.project_id == project_id) &
                                (db.project_members.is_coordinator == 'True')).select()
            project_coords = [r.user_id for r in project_coords]
            readonly = False if  auth.user.id in project_coords else True
            button_text = 'Submit project edits'
        else:
            readonly = False
            button_text = 'Submit new project'
        
        # this passes through admin fields as well and lets the view code
        # handle what is exposed to users.
        form = SQLFORM(db.project, record = record, readonly=readonly,
                       fields = ['picture', 'title', #'project_home_country',
                                 'research_areas', 'start_date', 'end_date', 'data_use',
                                 'rationale', 'methods', 'which_animal_taxa',
                                 'destructive_sampling','destructive_sampling_info',
                                 'ethics_approval_required','ethics_approval_details',
                                 'funding', 'requires_ra',
                                 'requires_vehicle','resource_notes', 'data_sharing',
                                 #'admin_status', 'admin_notes'
                                 ],
                      submit_button = button_text)
        
        if form.process(onvalidation=validate_project).accepted:
        
            # actions depend on whether this is a new project or an update
            if record is None:
                # add the proposer as the Main Contact for the project
                db.project_members.insert(user_id = auth.user.id, 
                                          project_id = form.vars.id,
                                          project_role = 'Main Contact',
                                          is_coordinator = True)
        
                # email the proposer
                template =  'email_templates/project_submitted.html'
                message =  response.render(template,
                                           {'name': auth.user.first_name,
                                            'url': URL('projects', 'project_details', args=form.vars.id, scheme=True, host=True)})
        
                msg_status = mail.send(to=auth.user.email,
                                       subject='SAFE project proposal submission',
                                       message=message)
            
                # signal success and load the newly created record in a details page
                session.flash = CENTER(B('SAFE project  successfully submitted.'), _style='color: green')
                redirect(URL('projects', 'project_details', args=form.vars.id))
            else:
                # signal success 
                session.flash = CENTER(B('SAFE project successfully updated.'), _style='color: green')
                redirect(URL('projects', 'project_details', args=form.vars.id))
                
        elif form.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
            print form.errors
        else:
            pass
        
        # Now handle members:
        # - provide a view of the project members if the project exists
        if project_id is not None:
            members = db(db.project_members.project_id == project_id).select()
            if readonly is False:
                db.project_members.project_id.default = project_id
                add_member = SQLFORM(db.project_members, fields=['user_id','project_role','is_coordinator'])
            else:
                add_member = None
        else:
            members = None
            add_member = None
        
        if add_member is not None:
            if add_member.process(onvalidation=validate_new_project_member).accepted:
                session.flash = CENTER(B('New project member added.'), _style='color: green')
                redirect(URL('projects', 'project_details', args=project_id))
            elif add_member.errors:
                response.flash = CENTER(B('Problem with adding project member.'), _style='color: red')
            else:
                pass
        
        # pass the form and record, for info look up on admin status
        # - this could be implemented by setting writable = FALSE and getting fields
        #   contents through the widget

        return dict(form=form, record=record, readonly=readonly, members=members, add_member=add_member)


def validate_project(form):
    
    # insert proposal time and proposer if blank (new proposal)
    if form.vars.proposer_id is None:
        form.vars.proposer_id = auth.user_id
        form.vars.proposal_date =  datetime.date.today().isoformat()
    
    # must agree to share data
    if form.vars.data_sharing is False or form.vars.data_sharing is None:
        form.errors.data_sharing = 'Data sharing is a mandatory part of the requirements for working at SAFE.'
    
    # must provide ethics  details if needed
    if form.vars.ethics_approval_required == 'on' and \
      (form.vars.ethics_approval_details == '' or form.vars.ethics_approval_details is None):
        form.errors.ethics_approval_details = 'You must provide details of the ethics approval you will need and how you plan to obtain it.'
    
    # must provide destructive sampling details if needed
    if form.vars.destructive_sampling == 'on' and \
      (form.vars.destructive_sampling_info == '' or form.vars.destructive_sampling_info is None):
        form.errors.destructive_sampling_info = 'You must provide justification for destructive sampling in your project.'
    
    # must provide at least one research area
    if form.vars.research_areas == []:
        form.errors.research_areas = 'You must select at least one research area'
    
    # must provide at least one data use
    if form.vars.data_use == []:
        form.errors.data_use = 'You must select at least one data use option'


def validate_new_project_member(form):
    
    pass

@auth.requires_login()
def remove_member():

    """
    Removes a row from the project_member table and as such needs careful safeguarding
    against use by non-authorised people - must be a logged in user who is a coordinator
    for the project
    """

    # get the row id
    row_id = request.args(0)
    record = db.project_members(row_id)
    
    if record is not None:
    
        # get a set of users who have the right to access this interface for the row
        project_coords = db((db.project_members.project_id == record.project_id) &
                            (db.project_members.is_coordinator == 'True')).select()
        project_coord_id = [r.user_id for r in project_coords]
    
        # if the user is a member then check it makes sense to delete and do so.
        if  auth.user.id in project_coord_id:
            
            # are we removing the last coordinator?
            if len(project_coord_id) == 1 and int(row_id) == project_coords.first().id:
                 session.flash =  CENTER(B('You may not remove the last coordinator from a project'), _style='color: red')
                 redirect(URL('projects','project_details', args=record.project_id))
            else:
                # TODO - notify the member that they're being removed?
                session.flash =  CENTER(B('Project member removed'), _style='color: green')
                db(db.project_members.id == row_id).delete()
                redirect(URL('projects','project_details', args=record.project_id))
        else:
            session.flash =  CENTER(B('Unauthorised use of projects/remove_member'), _style='color: red')
            redirect(URL('projects','projects'))
    else:
        session.flash = CENTER(B('Unknown row ID in projects/remove_member'), _style='color: red')
        redirect(URL('projects','projects'))


## -----------------------------------------------------------------------------
## ADMINISTER NEW PROJECTS
## - viewing these is through the view projects interface so this just adds the
##   ability for project members to edit and add project members but not delete
## -----------------------------------------------------------------------------

@auth.requires_membership('admin')
def administer_projects():

    """
    This controller handles:
     - presenting admin users with a list of pending new projects
     - a custom link to a page showing members and project details
    """
    
    # create an icon showing project status and a new button that
    # passes the project id to a new controller
    links = [dict(header = '', body = lambda row: approval_icons[row.admin_status]),
             dict(header = '', body = lambda row: A('Details',_class='button btn btn-default'
                  ,_href=URL("projects","administer_project_details", args=[row.id])))
            ]
    
    # hide the text of the admin_status
    db.project.admin_status.readable = False
    
    # get a query of pending requests 
    form = SQLFORM.grid(query=(db.project.admin_status.belongs(['Pending','In Review'])), csv=False,
                        fields=[db.project.proposal_date,
                                db.project.title,
                                #db.project.start_date,
                                #db.project.end_date
                                db.project.admin_status,
                                ],
                         orderby = db.project.proposal_date,
                         maxtextlength=250,
                         deletable=False,
                         editable=False,
                         create=False,
                         details=False,
                         links = links,
                         editargs = {'showid': False},
                         )
    
    return dict(form=form)

@auth.requires_membership('admin')
def administer_project_details():

    """
    Custom project view - shows the members and details of a project
    and allows the admin to approve or reject the project
    """

    # look for an existing record, otherwise a fresh start with an empty record
    project_id = request.args(0)
    
    if project_id is None or (project_id is not None and db.project(project_id) is None):
        # avoid unknown projects
        session.flash = B(CENTER('Invalid or missing project id'), _style='color:red;')
        redirect(URL('projects','administer_projects'))
    else:
        
        # get project members 
        members = db(db.project_members.project_id == project_id).select()
        record = db.project(project_id)
        
        # pass the admin fields through as a field and the rest as a record
        form = SQLFORM(db.project, record = project_id, showid=False,
                       fields = ['admin_status', 'admin_notes'],
                       submit_button = 'Submit decision')
        
        # process the form and handle actions
        if form.process(onvalidation=validate_administer_projects).accepted:
        
            # retrieve the whole form record to get at the creator details
            # TODO - think about who gets emailed. Just the proposer or all members
            proposer = record.proposer_id
        
            # set a flash message
            flash_message  = CENTER(B('Decision emailed to project proposer at {}.'.format(proposer.email)), _style='color: green')
        
            # pick an decision
            if form.vars.admin_status == 'Approved':
                mail.send(to=proposer.email,
                          subject='SAFE project submission',
                          message='Dear {},\n\nLucky template\n\n {}'.format(proposer.first_name, form.vars.admin_notes))
                session.flash = flash_message
                redirect(URL('projects','administer_projects'))
            elif form.vars.admin_status == 'Resubmit':
                mail.send(to=proposer.email,
                          subject='SAFE project resubmission',
                          message='Dear {},\n\nChanges needed\n\n {}'.format(proposer.first_name, form.vars.admin_notes))
                session.flash = flash_message
                redirect(URL('projects','administer_projects'))
            elif form.vars.admin_status == 'In Review':
                mail.send(to=proposer.email,
                          subject='SAFE project in review',
                          message='Dear {},\n\nSent to reviewers\n\n {}'.format(proposer.first_name, form.vars.admin_notes))
                # TODO - send email to review panel
                session.flash = flash_message
                redirect(URL('projects','administer_projects'))
            elif form.vars.admin_status == 'Rejected':
                mail.send(to=proposer.email,
                          subject='SAFE project submission',
                          message='Dear {},\n\nUnlucky template\n\n {}'.format(proposer.first_name, form.vars.admin_notes))
                session.flash = flash_message
                redirect(URL('projects','administer_projects'))
            else:
                pass
        elif form.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
        
        
        # pass components to the view
        return dict(record=record, members=members, form=form)

def validate_administer_projects(form):
    
    # validation handles any checking (none here) and also any 
    # amendments to the form variable  - adding admin user, date of admin decision 
    # and decision
    form.vars.admin_id = auth.user.id
    today = datetime.date.today().isoformat()
    form.vars.admin_decision_date = today
    
    # update the history
    new_history = '[{} {}, {}, {}]\\n {}'.format(auth.user.first_name, 
                   auth.user.last_name, today, form.vars.admin_status, 
                   form.vars.admin_notes)
    if form.vars.admin_history is None:
        form.vars.admin_history = new_history
    else:
        form.vars.admin_history += new_history
