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
                                       _href=URL("projects","project_details", args=[row.id], user_signature=True),
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


def project_details():

    """
    Custom project view - displays the project and any members or outputs
    and allow project members to add more project members. This isn't protected
    by a decorator because it is used to display approved projects to the public.
    
    However we need to protect the interface from being used to query any project 
    id, so there is an initial block of code to handle who is allowed to view what
    project status. This might all be shiftable to decorators, actually...
    """
    
    # retrieve the user id from the page arguments passed by the button
    project_id = request.args(0)
    
    # control access to records based on status
    project_record = db.project(project_id)
    
    if (project_record is not None) and \
       (auth.has_membership('admin') or \
       (auth.is_logged_in() and project_record.admin_status != 'Rejected') or \
       (project_record.admin_status == 'Approved')):
    
        # set up the project form
        this_project = SQLFORM(db.project, project_id,
                       fields = ['project_home_country', 
                                 'sampling_sites', 'sampling_scales',
                                 'research_areas', 'start_date', 'end_date',
                                 'rationale', 'methods'],
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
    
        # if the user is a member of the project then include a list of users to add
        project_members = db(db.project_members.project_id == project_id).select()
        project_member_ids = [r.user_id for r in project_members]
    
        if auth.is_logged_in() and auth.user.id in project_member_ids:
        
            # lock down the value of the project_id locally
            db.project_members.project_id.default = project_id
        
            addform = SQLFORM(db.project_members, 
                              fields = ['user_id', 'project_role'])
        
            if addform.process().accepted:
                response.flash = CENTER(B('New project member added.'), _style='color: green')
                # could email the new member here
                pass
    
        else:
            addform = None
        
        # pass components to the view
        return dict(title=title, pic=pic,
                    this_project=this_project, 
                    membership_panel=membership_panel,
                    outputs_panel=outputs_panel,
                    addform=addform)
    
    # now for non-existant records or attempts to access user/admin only
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
## NEW PROJECT CONTROLLERS
## -- DESIGN NOTES: A project can be created by a single user, who is automatically
##                  added as a project member. A separate form is used to add more
##                  members (and all members of a project can _currently_ add new 
##                  members). This does mean that project membership can change post
##                  approval, but this is probably needed functionality anyway.
## -- TODO - extend new_project to require non-student status?
## -----------------------------------------------------------------------------

@auth.requires_login()
def new_project():

    """
    Controller to handle the creation of new project proposals and to
    insert a check that the user agrees to data sharing
    """

    form = SQLFORM(db.project,
                   fields = ['picture', 'title', 'project_home_country',
                             'sampling_sites', 'sampling_scales',
                             'research_areas', 'start_date', 'end_date',
                             'rationale', 'methods', 'requires_ra',
                             'requires_vehicle','resource_notes', 'data_sharing'],
                   labels = {'requires_ra': 'Will your project require Research Assistant time?',
                             'requires_vehicle': 'Will your project need a vehicle to access sites?',
                             'resource_notes': 'Give details of expected resources needed',
                             'data_sharing': 'I agree to the requirements of the SAFE project and will '
                                             'submit the project data to the SAFE database at the '
                                             'conclusion of this project.'},
                  submit_button = 'Submit and add project members')

    if form.process(onvalidation=validate_new_project).accepted:
        
        # add the proposer as the Main Contact for the project
        db.project_members.insert(user_id = auth.user.id, 
                                  project_id = form.vars.id,
                                  project_role='Main Contact')
        
        # email the proposer
        template =  'email_templates/project_submitted.html'
        message =  response.render(template,
                                   {'name': auth.user.first_name,
                                    'url': URL('projects', 'project_details', args=form.vars.id, scheme=True, host=True)})
        
        print message
        
        msg_status = mail.send(to=auth.user.email,
                               subject='SAFE project proposal submission',
                               message=message)
        
        print msg_status
        
        # signal success
        session.flash = CENTER(B('SAFE project output successfully submitted.'), _style='color: green')
        redirect(URL('projects', 'project_details', args=form.vars.id))
        
    elif form.errors:
        response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
    else:
        pass

    return dict(form=form)


def validate_new_project(form):
    
    form.vars.proposer_id = auth.user_id
    form.vars.proposal_date =  datetime.date.today().isoformat()
    
    if form.vars.data_sharing is False or form.vars.data_sharing is None:
        form.errors.data_sharing = 'Data sharing is a mandatory part of the requirements for working at SAFE.'


## -----------------------------------------------------------------------------
## ADMINISTER NEW PROJECTS
## - viewing these is through the view projects interface so this just adds the
##   ability for project members to edit and add project members but not delete
## -----------------------------------------------------------------------------

@auth.requires_membership('admin')
def administer_new_projects():

    """
    This controller handles:
     - presenting admin users with a list of pending new projects
     - a custom link to a page showing members and project details
    """
    
    # create a new button that passes the project id to a new controller
    links = [dict(header = '', body = lambda row: A('Details',_class='button btn btn-default'
                  ,_href=URL("projects","administer_new_project_details", args=[row.id])))
            ]
    
    # get a query of pending requests 
    form = SQLFORM.grid(query=(db.project.admin_status == 'Pending'), csv=False,
                        fields=[db.project.title,
                                db.project.start_date,
                                db.project.end_date],
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
def administer_new_project_details():

    """
    Custom project view - shows the members and details of a pending project
    and allows the admin to approve or reject the project
    """
    
    # TODO - check the project is pending?
    # retrieve the user id from the page arguments passed by the button
    project_id = request.args(0)
    
    # lock down which fields can be changed
    db.project.picture.writable = False
    db.project.title.writable = False
    db.project.project_home_country.writable = False
    db.project.research_areas.writable = False
    db.project.sampling_sites.writable = False
    db.project.sampling_scales.writable = False
    db.project.start_date.writable = False
    db.project.end_date.writable = False
    db.project.methods.writable = False
    db.project.rationale.writable = False
    db.project.data_sharing.writable = False
    db.project.resource_notes.writable = False
    db.project.resource_notes.writable = False
    db.project.requires_ra.writable = False
    db.project.requires_vehicle.writable = False
    db.project.proposer_id.writable = False
    db.project.proposal_date.writable = False
    # hide the background admin fields
    db.project.admin_id.readable = False
    db.project.admin_id.writable = False
    db.project.admin_decision_date.readable = False
    db.project.admin_decision_date.writable = False
    
    # set up the project form
    this_project = SQLFORM(db.project, project_id,
                   fields = ['project_home_country', 'sampling_sites', 
                             'sampling_scales', 'research_areas', 
                             'start_date', 'end_date',
                             'rationale', 'methods',
                             'admin_status','admin_notes'],
                   showid=False)
    
    # process the form and handle actions
    if this_project.process(onvalidation=validate_administer_new_projects).accepted:
        
        # retrieve the whole form record to get at the creator details
        # TODO - think about who gets emailed. Just the proposer or all members
        proposer = this_project.record.proposer_id
        
        # set a flash message
        flash_message  = CENTER(B('Decision emailed to project proposer at {}.'.format(proposer.email)), _style='color: green')
        
        # pick an decision
        if this_project.vars.admin_status == 'Approved':
            mail.send(to=proposer.email,
                      subject='SAFE project submission',
                      message='Dear {},\n\nLucky template\n\n {}'.format(proposer.first_name, this_project.vars.admin_notes))
            session.flash = flash_message
            redirect(URL('projects','administer_new_projects'))
        elif this_project.vars.admin_status == 'Rejected':
            mail.send(to=proposer.email,
                      subject='SAFE project submission',
                      message='Dear {},\n\nUnlucky template\n\n {}'.format(proposer.first_name, this_project.vars.admin_notes))
            session.flash = flash_message
            redirect(URL('projects','administer_new_projects'))
        else:
            pass
    elif this_project.errors:
        response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
    else:
        pass
    
    # we want the title as a display item not in the SQLFORM
    # so it is excluded from fields above and retrieved below using the record
    title = this_project.record.title
    
    # set up a membership panel - this uses AJAX, which is black box woo to me at the moment
    membership_panel = LOAD(request.controller,
                            'view_project_membership.html',
                             args=[project_id],
                             ajax=True)
    
    # pass components to the view
    return dict(title=title,
                this_project=this_project, 
                membership_panel=membership_panel)



def validate_administer_new_projects(form):
    
    # validation handles any checking (none here) and also any 
    # amendments to the form variable  - adding user and date of admin
    form.vars.admin_id = auth.user_id
    form.vars.admin_decision_date =  datetime.date.today().isoformat()


# ## -----------------------------------------------------------------------------
# ## PROJECT MEMBERS
# ## - viewing these is through the view projects interface so this just adds the
# ##   ability for project members to edit and add project members but not delete
# ## -----------------------------------------------------------------------------
#
# @auth.requires_login()
# def manage_project_members():
#
#     """
#     This controller shows a SQLFORM.grid to edit project members
#     Only projects for which the logged in user is a member are available.
#     """
#
#     # Restrict the project choices
#     # - find the acceptable project ID numbers
#     valid_ids = db(db.project_members.user_id == auth.user.id)._select(db.project_members.project_id)
#     query = db(db.project.id.belongs(valid_ids))
#
#     # - constrain the project_members project_id requirements within this controller
#     #   so that users can only add records for projects they are a member of
#     db.project_members.project_id.requires = IS_IN_DB(query, db.project.id, '%(title)s')
#
#     # lock down project ID and user ID for editing existing rows
#     # and use createargs to ignore these restictions for new projects
#     db.project_members.project_id.writable = False
#     db.project_members.user_id.writable = False
#
#     # check to see if anything is available
#     if db(db.project_members).count() == 0:
#         form = CENTER(B('You are not registered as a member of any projects.'), _style='color: red')
#     else:
#         form = SQLFORM.grid(query=(db.project_members.project_id.belongs(valid_ids)),
#                             fields = [db.project_members.project_id,
#                                       db.project_members.user_id,
#                                       db.project_members.project_role],
#                             deletable=False,
#                             details=False,
#                             csv=False,
#                             formargs = {'showid': False},
#                             createargs = {'ignore_rw': True})
#
#     return dict(form=form)