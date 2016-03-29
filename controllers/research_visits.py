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
    db.research_visit.admin_id.readable = False 
    db.research_visit.admin_notes.readable = False 
    db.research_visit.admin_decision_date.readable = False 
    
    # create a links list that:
    # 1) displays a thumbnail of the  project image
    # 2) creates a custom button to pass the row id to a custom view 

    links = [dict(header = '', body = lambda row: A('View',_class='button btn btn-default'
                  ,_href=URL("research_visits","research_visit_details", args=[row.id])))
            ]

    form = SQLFORM.grid(db.research_visit, csv=False, 
                        fields=[db.research_visit.project_id, db.research_visit.title, 
                                db.research_visit.arrival_date, db.research_visit.departure_date],
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False, 
                        details=False,
                        links=links,
                        links_placement='left',
                        formargs={'showid': False})

    return dict(form=form)



@auth.requires_login()
def new_research_visit():
    
    """
    This controller shows a SQLFORM to propose a research visit. The controller then
    passes the response through validation before sending a confirmation email out.
    """
    
    # Restrict the project choices available
    # - find projects that the logged in user is a member of
    valid_ids = db(db.project_members.user_id == auth.user.id)._select(db.project_members.project_id)
    query = db(db.project.id.belongs(valid_ids))
    
    # - modify the project_id requirements within this controller to only show those projects
    db.research_visit.project_id.requires = IS_EMPTY_OR(IS_IN_DB(query, db.project.id, '%(title)s'))
    
    # Help the user by explaining why project ID might be blank
    if query.count() == 0:
        message = CENTER(B('Sorry, you must have been added as a member of a project'
                           ' to submit a research visit proposal'), _style='color: red')
    else:
        message = None
    
    form = SQLFORM(db.research_visit,
                   fields = ['project_id','title','arrival_date',
                             'departure_date','purpose','licence_details'],
                   labels = {'title':'Reference name for visit'},
                   submit_button = 'Submit and add visit members')
    
    # now intercept and parse the various inputs
    if form.process(onvalidation=validate_new_research_visit).accepted:
        
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
    
    return dict(form=form, message=message)


def validate_new_research_visit(form):
    
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
    

@auth.requires_login()
def research_visit_details():
    
    """
    Controller to show the details of research visits
     - collects a bunch of information and passes it to the view for processing
     - allows members to be added
    """
    
    # get the visit_id from the call
    research_visit_id = request.args(0)
    
    # get the visit information
    visit_record = db.research_visit(research_visit_id)
    
    if visit_record is None:
        redirect(URL('default','index'))
    
    # get project members (who have the right to add themselves or others)
    project_members_query = db.project_members.project_id == visit_record.project_id
    project_members_rows = db(project_members_query).select(db.project_members.user_id)
    
    # get the auth_user records for existing members to display
    visit_members_query = db.research_visit_member.research_visit_id == research_visit_id
    visit_members_select = db(visit_members_query)._select(db.research_visit_member.user_id)
    visit_members_rows = db(db.auth_user.id.belongs(visit_members_select)).select()
    
    # provide form to add new users
    project_member_ids = [r.user_id for r in project_members_rows]
    if auth.user.id in project_member_ids:
        
        # Offer choices of new members to add
        # - find users belonging to the project that this visit is for 
        #   and which are not already members of the visit
        already_visitors = [r.id for r in visit_members_rows]
        
        not_visitors = list(set(project_member_ids) - set(already_visitors))
        query = db(db.auth_user.id.belongs(not_visitors))
        
        # - require the visit members to be in that set
        db.research_visit_member.user_id.requires = IS_IN_DB(query, db.auth_user.id, '%(last_name)s, %(first_name)s')
        
        # lock down the possible value of research_visit_id
        db.research_visit_member.research_visit_id.default = research_visit_id
        db.research_visit_member.research_visit_id.readable = False
        
        form = SQLFORM(db.research_visit_member,
                       fields = ['user_id'],
                       labels = {'user_id':'Project member to add'})
        
        # process and reload the page
        if form.process().accepted:
            redirect(URL('research_visits', 'research_visit_details', args=research_visit_id))
    else:
        form = None
    return dict(visit_record = visit_record, visit_members=visit_members_rows, form=form)

# decorator restricts access to admin users
# - the link is only revealed in the menu for admin users but 
#   that doesn't prevent pasting in the link!
@auth.requires_membership('admin')
def administer_new_research_visits():
    
    """
    This controller handles:
     - presenting admin users with a list of current proposals for research visits 
     - allowing the admin to approve or reject visit requests
     - Currently this locks all but the admin fields. Might also need
       a separate admin visit booking form with fewer restrictions for
       overbooking and special cases?
    """
    
    # don't want the admin to change any of this about a visit
    db.research_visit.project_id.writable = False
    db.research_visit.title.writable = False
    db.research_visit.arrival_date.writable = False
    db.research_visit.departure_date.writable = False
    db.research_visit.writable = False
    db.research_visit.purpose.writable = False
    
    # get a query of pending requests with user_id
    form = SQLFORM.grid(query=(db.research_visit.admin_status == 'Pending'), csv=False,
                        fields=[db.research_visit.project_id, 
                                db.research_visit.title],
                         maxtextlength=250,
                         deletable=False,
                         editable=True,
                         create=False,
                         details=False,
                         editargs = {'fields': ['project_id','title',
                                                'arrival_date','departure_date',
                                                'purpose', 'admin_status','admin_notes'],
                                     'showid': False},
                         onvalidation = validate_administer_new_research_visits,
                         onupdate = update_administer_new_research_visits)
    
    return dict(form=form)

@auth.requires_membership('admin')
def validate_administer_new_research_visits(form):
    
    # validation handles any checking (none here) and also any 
    # amendments to the form variable  - adding user and date of admin
    form.vars.admin_id = auth.user_id
    form.vars.admin_decision_date =  datetime.date.today().isoformat()


@auth.requires_membership('admin')
def update_administer_new_research_visits(form):

    """
    This handler emails the person who made the proposal
    """
    
    # recover the record to get all the stuff that isn't writable
    record = form.record
        
    # email the reserver
    if(form.vars.admin_status == 'Approved'):
        
        # email the proposer
        mail.send(to=record.proposer_id.email,
              subject='SAFE research visit proposal accepted',
              message='Welcome to SAFE')
        session.flash = CENTER(B('Approval email sent to visit proposer'), _style='color: green')
    
    elif(form.vars.admin_status == 'Rejected'):
        
        mail.send(to=record.proposer_id.email,
              subject='SAFE research visit proposal rejected',
              message='Nope')
        session.flash = CENTER(B('Rejection email sent to visit proposer'), _style='color: green')
    else:
        pass
    
    return dict(form=form)
