import datetime

## -----------------------------------------------------------------------------
## RESEARCH VISITS
## -- controllers to register research visits and administer those visits
## -- provide a general grid view of visits for users and a detail view that
##    allows project members to add members to visits
## -----------------------------------------------------------------------------


@auth.requires_login()
def research_visits():
    
    """
    This controller shows the grid view for visits and allows
    logged in users to view details

    It uses a custom button to divert from the SQLFORM.grid view to a
    custom view page that allows project members to add visitors
    """

    # For standard users (need a separate admin projects controller)
    # don't show the authorization fields and don't show a few behind 
    # the scenes fields
    db.research_visit.admin_notes.readable = False 
    
    # create a links list that:
    # 1) displays a thumbnail of the  project image
    # 2) creates a custom button to pass the row id to a custom view 

    links = [dict(header = 'Admin Status', body = lambda row: approval_icons[row.admin_status]),
             dict(header = '', body = lambda row: A('View',_class='button btn btn-default',
                  _href=URL("research_visits","research_visit_details", args=[row.id]),
                  _style='padding: 3px 10px 3px 10px;'))
            ]
    
    # suppress status in  SQLFORM grid whilst making it available for links
    db.research_visit.admin_status.readable = False 
    
    form = SQLFORM.grid(db.research_visit, csv=False, 
                        fields=[db.research_visit.project_id, db.research_visit.title, 
                                db.research_visit.arrival_date, db.research_visit.departure_date,
                                db.research_visit.admin_status],
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False, 
                        details=False,
                        links=links,
                        links_placement='right',
                        formargs={'showid': False})

    return dict(form=form)


@auth.requires_login()
def research_visit_details():
    
    """
    This controller shows a SQLFORM to propose a research visit or to edit one. The
    controller then passes the response through validation before sending a 
    confirmation email out.
    
    It uses the same mechanism as projects etc to provide an add user interface
    """
    
    # look for an existing record, otherwise a fresh start with an empty record
    visit_id = request.args(0)
    if visit_id is not None:
        record = db.research_visit(visit_id)
    else:
        record = None
    

    if visit_id is not None and record is None:
        # If the visit is given as an ID, does it really exist
        session.flash = B(CENTER('Invalid research visit id'), _style='color:red;')
        redirect(URL('research_visits','research_visits'))
        
    else:
        # set up for new or existing project
        if visit_id is not None:
            # is the user is a coordinator of the project associated with this record
            coord_query = db((db.project_members.project_id == record.project_id) &
                             (db.project_members.is_coordinator == 'True')).select()
            project_coords = [r.user_id for r in coord_query]
            readonly = False if  auth.user.id in project_coords else True
            button_text = 'Update research visit proposal'
        else:
            # is the user a coordinator for any project?
            coord_query = db(db.project_members.is_coordinator == 'True').select()
            project_coords = [r.user_id for r in coord_query]
            if auth.user.id in project_coords:
                readonly = False 
                button_text = 'Submit research visit proposal'
            else:
                session.flash = CENTER(B('Sorry, you must be a coordinator of an approved research project'
                               ' to submit a research visit proposal'), _style='color: red')
                redirect(URL('research_visits','research_visits'))
        
        # - modify the project_id requirements to only allow projects 
        #   the user is a coordinator for.
        available_projects = db(db.project_members.is_coordinator == 'True')._select(db.project_members.project_id)
        query = db(db.project.id.belongs(available_projects))
        db.research_visit.project_id.requires = IS_IN_DB(query, db.project.id, '%(title)s')
        
        # Can't change the project associated with a research visit
        if visit_id is not None:
            db.research_visit.project_id.writable = False
        
        # provide the research visit form
        form = SQLFORM(db.research_visit, 
                       record = visit_id,
                       readonly = readonly,
                       fields = ['project_id','title','arrival_date',
                                 'departure_date','purpose','licence_details'],
                       labels = {'title':'Reference name for visit'},
                       submit_button = button_text,
                       showid = False)
    
        # now intercept and parse the various inputs
        if form.process(onvalidation=validate_research_visit_details).accepted:
        
            # Signal success and email the proposer
            mail.send(to=auth.user.email,
               subject='SAFE research visit proposal submitted',
               message='Many thanks for proposing your research visit')
            response.flash = CENTER(B('SAFE research proposal successfully submitted.'), _style='color: green')
            
            # add the proposer to the visit member table
            db.research_visit_member.insert(research_visit_id = form.vars.id,
                                            user_id = auth.user.id)
        
            redirect(URL('research_visits','research_visit_details', args=form.vars.id))
        
        elif form.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
        
        
        # Now handle members:
        if visit_id is not None:
            # if the visit already exists, join the auth records for the members with 
            # their visit membership to get ids for removing members and links to H&S
            query = db(db.research_visit_member.research_visit_id == record.id)
            members = query.select(db.auth_user.id,
                                   db.auth_user.last_name,
                                   db.auth_user.first_name,
                                   db.auth_user.h_and_s_id,
                                   db.research_visit_member.id,
                                   left=db.research_visit_member.on(db.auth_user.id == db.research_visit_member.user_id))
            
            if readonly is False:
                # restrict members that can be added to existing project members
                # who aren't already members of this visit
                valid_ids = db(db.project_members.project_id == record.project_id)._select(db.project_members.user_id)
                already_selected = db(db.research_visit_member.research_visit_id == record.id)._select(db.research_visit_member.user_id)
                query = db(db.auth_user.id.belongs(valid_ids) & ~ db.auth_user.id.belongs(already_selected))
                db.research_visit_member.user_id.requires = IS_IN_DB(query, db.auth_user.id, '%(last_name)s, %(first_name)s')
                
                db.research_visit_member.research_visit_id.default = record.id
                add_member = SQLFORM(db.research_visit_member, fields=['user_id'])
            else:
                add_member = None
        else:
            members = None
            add_member = None
        
        if add_member is not None:
            if add_member.process(onvalidation=validate_new_research_visit_member).accepted:
                session.flash = CENTER(B('New research visit member added.'), _style='color: green')
                redirect(URL('research_visits', 'research_visit_details', args=visit_id))
            elif add_member.errors:
                response.flash = CENTER(B('Problem with adding research visit member.'), _style='color: red')
            else:
                pass
        
    return dict(record=record, form=form, members=members, add_member=add_member, readonly=readonly)


def validate_research_visit_details(form):
    
    form.vars.proposer_id = auth.user_id
    form.vars.proposal_date = datetime.date.today().isoformat()
    
    # check the arrival date is more than a fortnight away
    deadline = datetime.date.today() + datetime.timedelta(days=14)
    if form.vars.arrival_date < deadline:
        form.errors.arrival_date = '14 days notice required. Arrival date must be later than {}.'.format(deadline.isoformat())
    
    # check the departure date is after the arrival date
    # TODO - think about day visits
    if form.vars.arrival_date >= form.vars.departure_date:
        form.errors.departure_date = 'The departure date must be later than the arrival date'
    
    # set approval to pending to get oversight on edits
    form.vars.admin_status = 'Pending'


def validate_new_research_visit_member(form):
    
    pass


@auth.requires_login()
def remove_member():

    """
    Removes a row from the research visit members table and as such needs careful safeguarding
    against use by non-authorised people - must be a logged in user who is a coordinator
    for the project
    """

    # get the row id
    row_id = request.args(0)
    member_record = db.research_visit_member(row_id)
    visit_record = db.research_visit(member_record.research_visit_id)
    
    if member_record is not None:
    
        # get a set of users who have the right to access this interface for the row
        project_coords = db((db.project_members.project_id == visit_record.project_id) &
                            (db.project_members.is_coordinator == 'True')).select()
        project_coord_id = [r.user_id for r in project_coords]
    
        # if the user is a member then check it makes sense to delete and do so.
        if  auth.user.id in project_coord_id:
            
            # TODO - notify the member that they're being removed?
            session.flash =  CENTER(B('Project member removed'), _style='color: green')
            member_record.delete_record()
            redirect(URL('research_visits','research_visit_details', args=member_record.research_visit_id))
        else:
            session.flash =  CENTER(B('Unauthorised use of research_visits/remove_member'), _style='color: red')
            redirect(URL('research_visits','research_visits'))
    else:
        session.flash = CENTER(B('Unknown row ID in research_visits/remove_member'), _style='color: red')
        redirect(URL('research_visits','research_visits'))


@auth.requires_login()
def research_visit_from_project():

    """
    This controller creates a new research visit record from a project record,
    porting the title and project members into the new visit automatically. This
    means that users don't have to continually reselect groups.
    
    Exposing this controller requires authorization checking that the user is
    a coordinator for the project.
    """
    
    # get the project id
    project_id = request.args(0)
    
    # establish we've got an actual real project ID
    if project_id is not None:
        record = db.project(project_id)
        
        if record is None:
            session.flash = CENTER(B('Unknown project id in research_visits/research_visit_from_project'), _style='color: red')
            redirect(URL('projects','projects'))
    else:
        session.flash = CENTER(B('No project id in research_visits/research_visit_from_project'), _style='color: red')
        redirect(URL('projects','projects'))
    
    # check coordinator privileges
    coord_query = db((db.project_members.project_id == record.id) &
                     (db.project_members.is_coordinator == 'True') &
                     (db.project_members.user_id == auth.user.id)).select()
    
    if len(coord_query) == 0:
        session.flash = CENTER(B('Cannot create a visit for this project: you are not a project coordinator'), _style='color: red')
        redirect(URL('projects','project_details', args=record.id))
    
    # populate the visit record
    new_visit = db.research_visit.insert(project_id = record.id,
                                         title = 'Insert visit title',
                                         arrival_date = '0001-01-01',
                                         departure_date = '0001-01-01',
                                         purpose = 'Insert research visit title',
                                         proposer_id = auth.user.id,
                                         proposal_date = datetime.datetime.utcnow().isoformat())
    
    # populate the members
    project_members = db(db.project_members.project_id == record.id).select()
    for r in project_members:
        member_added = db.research_visit_member.insert(research_visit_id = new_visit,
                                                       user_id = r.user_id)
    
    # send to the new record
    session.flash = CENTER(B('Visit created - please edit the dates, title and purpose.'), _style='color: green')
    redirect(URL('research_visits','research_visit_details', args=new_visit))


## -----------------------------------------------------------------------------
## ADMINISTER NEW VISITS
## -----------------------------------------------------------------------------


# decorator restricts access to admin users
# - the link is only revealed in the menu for admin users but 
#   that doesn't prevent pasting in the link!
@auth.requires_membership('admin')
def administer_research_visits():
    
    """
    This controller handles:
     - presenting admin users with a list of current proposals for research visits 
     - allowing the admin to approve or reject visit requests
     - Currently this locks all but the admin fields. Might also need
       a separate admin visit booking form with fewer restrictions for
       overbooking and special cases?
    """
    
    links = [dict(header = '', body = lambda row: approval_icons[row.admin_status]),
             dict(header = '', body = lambda row: A('Details',_class='button btn btn-default'
                  ,_href=URL("research_visits","administer_research_visit_details", args=[row.id])))
            ]
    
    db.research_visit.admin_status.readable = False
    
    # get a query of pending requests with user_id
    form = SQLFORM.grid(query=(db.research_visit.admin_status == 'Pending'), csv=False,
                        fields=[db.research_visit.project_id, 
                                db.research_visit.title,
                                db.research_visit.admin_status],
                         maxtextlength=250,
                         deletable=False,
                         editable=False,
                         create=False,
                         details=False,
                         links=links
                         )
    
    return dict(form=form)


@auth.requires_membership('admin')
def administer_research_visit_details():

    """
    Custom project view - shows the members and details of a visit
    and allows the admin to approve or reject it
    """

    # look for an existing record, otherwise a fresh start with an empty record
    visit_id = request.args(0)
    
    if visit_id is None or (visit_id is not None and db.research_visit(visit_id) is None):
        # avoid unknown projects
        session.flash = B(CENTER('Invalid or missing visit id'), _style='color:red;')
        redirect(URL('research_visits','administer_research_visits'))
    else:
        
        # get project members 
        member_ids = db(db.research_visit_member.research_visit_id == visit_id)._select(db.research_visit_member.user_id)
        members = db(db.auth_user.id.belongs(member_ids)).select()
        record = db.research_visit(visit_id)
        
        # pass the admin fields through as a field and the rest as a record
        form = SQLFORM(db.research_visit, record = visit_id, showid=False,
                       fields = ['admin_status', 'admin_notes'],
                       submit_button = 'Submit decision')
        
        # process the form and handle actions
        if form.process(onvalidation=validate_administer_research_visits).accepted:
        
            # retrieve the whole form record to get at the creator details
            # TODO - think about who gets emailed. Just the proposer or all members
            proposer = record.proposer_id
            
            # reload the record to get at fresh admin details
            # and update the admin history
            record = db.research_visit(visit_id)
            new_history = '[{} {}, {}, {}]\\n {}\\n'.format(auth.user.first_name,
                           auth.user.last_name, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                           record.admin_status, record.admin_notes)
        
            # immediately pass the admin notes into the history and 
            # clear the admin notes field
            if record.admin_history is None or record.admin_history == '':
                record.update_record(admin_history = new_history,
                                     admin_notes = '')
            else:
                record.update_record(admin_history = record.admin_history + '\\n' + new_history,
                                     admin_notes = '')
            
            # set a flash message
            flash_message  = CENTER(B('Decision emailed to project proposer at {}.'.format(proposer.email)), _style='color: green')
        
            # pick an decision
            if form.vars.admin_status == 'Approved':
                mail.send(to=proposer.email,
                          subject='SAFE research visit submission',
                          message='Dear {},\n\nLucky template\n\n {}'.format(proposer.first_name, form.vars.admin_notes))
                session.flash = flash_message
                redirect(URL('research_visits','administer_research_visits'))
            elif form.vars.admin_status == 'Rejected':
                mail.send(to=proposer.email,
                          subject='SAFE research visit submission',
                          message='Dear {},\n\nUnlucky template\n\n {}'.format(proposer.first_name, form.vars.admin_notes))
                session.flash = flash_message
                redirect(URL('research_visits','administer_research_visits'))
            else:
                pass
        elif form.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
        
        
        # pass components to the view
        return dict(record=record, members=members, form=form)


@auth.requires_membership('admin')
def validate_administer_research_visits(form):
    
    # validation handles any checking (none here) and also any 
    # amendments to the form variable  - adding user and date of admin
    form.vars.admin_id = auth.user_id
    form.vars.admin_decision_date =  datetime.date.today().isoformat()

