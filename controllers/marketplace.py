
import datetime

## -----------------------------------------------------------------------------
## Volunteer marketplace
## ----------------------------------------------------x-------------------------

def volunteers():
    
    """
    This controller shows the grid view for approved volunteer positions
    TODO - add a volunteer google calendar
    """
    
    # subset to approved posts with expiry dates in the future
    approved_posts = (db.help_offered.admin_status == 'Approved') & \
                     (db.help_offered.available_to > datetime.date.today())
    
    # hide admin fields in the grid
    db.help_offered.admin_status.readable = False
    db.help_offered.submission_date.readable = False
    db.help_offered.admin_id.readable = False
    db.help_offered.admin_notes.readable = False
    db.help_offered.admin_decision_date.readable = False
    
    form = SQLFORM.grid(query=approved_posts, csv=False, 
                        fields=[db.help_offered.volunteer_id, 
                                db.help_offered.volunteer_type, 
                                db.help_offered.research_statement, 
                                db.help_offered.available_from, 
                                db.help_offered.available_to], 
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        formargs={'showid':False})
    
    return dict(form=form)



@auth.requires_login()
def new_volunteer():
    
    """
    This controller shows a SQLFORM to submit an offer to volunteer
    and then passes the response through validation before sending
    emails out.
    """
    
    form = SQLFORM(db.help_offered,
                   fields =['volunteer_type', 
                            'research_statement', 
                            'available_from', 
                            'available_to'],
                    )
    
    if form.process(onvalidation=validate_new_volunteer).accepted:
        
        # Signal success and email the proposer
        mail.send(to=auth.user.email,
              subject='SAFE volunteer offer submitted',
              message='Welcome to SAFE')
        response.flash = CENTER(B('Offer to volunteer successfully submitted.'), _style='color: green')
        
    elif form.errors:
        response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red') 
    else:
        pass
    
    return dict(form=form)

def validate_new_volunteer(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.volunteer_id = auth.user_id
    form.vars.submission_date =  datetime.date.today().isoformat()
    
    # check that available_to is after available_from
    if form.vars.available_from >= form.vars.available_to:
        form.errors.available_to = 'The availability end date is earlier than the start date.'
    
    if form.vars.available_from < datetime.date.today():
        form.errors.available_from = 'Your start date is in the past.'
    
    # check the arrival date is more than a fortnight away
    deadline = datetime.date.today() + datetime.timedelta(days=365)
    if form.vars.available_to > deadline:
        form.errors.available_to = 'We only accept offers to volunteer during the next 12 months (ending before {})'.format(deadline.isoformat())


@auth.requires_membership('admin')
def administer_volunteers():
    
    """
    This controller handles:
     - presenting admin users with a list of pending volunteers
     - TODO - editing approved volunteers?
    """
    
    # set the way user name is viewed in this controller
    ## db.help_offered.volunteer_id.represent = '%(last_names)s, %(first_names)s'
    
    # lock down which fields can be changed
    db.help_offered.volunteer_id.writable = False
    db.help_offered.volunteer_type.writable = False
    db.help_offered.submission_date.writable = False
    db.help_offered.available_from.writable = False
    db.help_offered.available_to.writable = False
    db.help_offered.research_statement.writable = False
    db.help_offered.admin_id.readable = False
    db.help_offered.admin_id.writable = False
    db.help_offered.admin_decision_date.readable = False
    db.help_offered.admin_decision_date.writable = False
    
    # get a query of pending requests with user_id
    form = SQLFORM.grid(query=(db.help_offered.admin_status == 'Pending'), csv=False,
                        fields=[db.help_offered.volunteer_id,
                                db.help_offered.volunteer_type,
                                db.help_offered.available_from,
                                db.help_offered.available_to],
                         maxtextlength=250,
                         deletable=False,
                         editable=True,
                         create=False,
                         details=False,
                         editargs = {'showid': False},
                         onvalidation = validate_administer_volunteers,
                         onupdate = update_administer_volunteers,
                         )
    
    return dict(form=form)


def validate_administer_volunteers(form):
    
    # validation handles any checking (none here) and also any 
    # amendments to the form variable  - adding user and date of admin
    form.vars.admin_id = auth.user_id
    form.vars.admin_decision_date =  datetime.date.today().isoformat()


def update_administer_volunteers(form):
    
    # Email the decision to the proposer
    # TODO - create and link to a Google Calendar for volunteer periods
    
    # we are editing a record so, volunteer_id (which references the underlying
    # auth_user table) can be used like this
    volunteer = form.record.volunteer_id
    
    # set a flash message
    flash_message  = CENTER(B('Decision emailed to volunteer at {}.'.format(volunteer.email)), _style='color: green')
    
    if form.vars.admin_status == 'Approved':
        # email the decision
        mail.send(to=volunteer.email,
                  subject='Decision on offer to volunteer at SAFE',
                  message='Dear {},\n\nLucky template {}'.format(volunteer.first_name, form.vars.admin_notes))
        # build the event and add to the volunteer calendar
        event = {'summary': '{} {}'.format(volunteer.first_name, volunteer.last_name),
                 'description': '{}: {}'.format(form.record.volunteer_type, form.record.research_statement),
                 'start': {'date': form.record.available_from.isoformat()},
                 'end':   {'date': form.record.available_to.isoformat()},
                }
        event = post_event_to_google_calendar(event, calID['volunteers'])
        session.flash = flash_message
    elif form.vars.admin_status == 'Rejected':
        mail.send(to=volunteer.email,
                  subject='Decision on offer to volunteer at SAFE',
                  message='Dear {},\n\nUnlucky template {}'.format(volunteer.first_name, form.vars.admin_notes))
        session.flash = flash_message
    else:
        pass
    

## -----------------------------------------------------------------------------
## Help sought marketplace
## -----------------------------------------------------------------------------

def help_requests():
    
    """
    This controller shows the grid view for approved help requests
    TODO - add Google calendar link for approved requests
    """
    
    # subset to approved posts with expiry dates in the future
    approved_posts = (db.help_request.admin_status == 'Approved') & \
                     (db.help_request.end_date > datetime.date.today())
    
    # hide admin fields in the grid
    db.help_request.admin_status.readable = False
    db.help_request.submission_date.readable = False
    db.help_request.admin_id.readable = False
    db.help_request.admin_notes.readable = False
    db.help_request.admin_decision_date.readable = False
    
    # TODO - complete formatting links to projects and users
    #db.help_request.contact_id.represent = lambda contact_id, row: I(contact_id)
    db.help_request.project_id.represent = lambda value, row: A('Link', _href='http://127.0.0.1:8000/SAFE/default/view_projects/view/project/'+str(value))
    
    approved_posts = (db.help_request.admin_status == 'Approved')
    
    form = SQLFORM.grid(query=approved_posts, csv=False, 
                        fields=[db.help_request.project_id,
                                db.help_request.start_date,
                                db.help_request.end_date,
                                db.help_request.work_description], 
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        formargs={'showid':False})
    
    return dict(form=form)


@auth.requires_login()
def new_help_request():
    
    """
    This controller shows a SQLFORM to submit an request for help
    on a project. Only projects for which the logged in user is a 
    member are available.
    
    The controller then passes the response through validation before 
    sending a confirmation email out.
    """
    
    # Restrict the project choices
    # - find the acceptable project ID numbers
    valid_ids = db(db.project_members.user_id == auth.user.id)._select(db.project_members.project_id)
    query = db(db.project.id.belongs(valid_ids))
    # - modify the help_request project_id requirements within this controller
    db.help_request.project_id.requires = IS_IN_DB(query, db.project.id, '%(title)s')

    # check to see if anything is available
    if db(db.project).count() == 0:
        form = CENTER(B('You are not registered as a member of any projects.'), _style='color: red')
    else:
        form = SQLFORM(db.help_request,
                       fields =['project_id',
                                'start_date',
                                'end_date',
                                'work_description'])

        if form.process(onvalidation=validate_new_help_request).accepted:
            # Signal success and email the proposer
            mail.send(to=auth.user.email,
               subject='SAFE help sought submitted',
               message='Welcome to SAFE')
            response.flash = CENTER(B('Request for help on your SAFE project successfully submitted.'), _style='color: green')
        elif form.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass

    return dict(form=form)


def validate_new_help_request(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.contact_id = auth.user_id
    form.vars.submission_date =  datetime.date.today().isoformat()
    
    # check that available_to is after available_from
    if form.vars.start_date >= form.vars.end_date:
        form.errors.available_to = 'The availability end date is earlier than the start date'
    
    if form.vars.start_date < datetime.date.today():
        form.errors.start_date = 'Your start date is in the past.'



def administer_help_requests():
    
    """
    This controller handles:
     - presenting admin users with a list of pending requests for help
     - TODO - editing approved help requests?
    """
    
    # lock down which fields can be changed
    db.help_request.contact_id.writable = False
    db.help_request.project_id.writable = False
    db.help_request.submission_date.writable = False
    db.help_request.start_date.writable = False
    db.help_request.end_date.writable = False
    db.help_request.work_description.writable = False
    db.help_request.admin_id.readable = False
    db.help_request.admin_id.writable = False
    db.help_request.admin_decision_date.readable = False
    db.help_request.admin_decision_date.writable = False
    
    # get a query of pending requests 
    form = SQLFORM.grid(query=(db.help_request.admin_status == 'Pending'), csv=False,
                        fields=[db.help_request.contact_id,
                                db.help_request.project_id,
                                db.help_request.start_date,
                                db.help_request.end_date],
                         maxtextlength=250,
                         deletable=False,
                         editable=True,
                         create=False,
                         details=False,
                         editargs = {'showid': False},
                         onvalidation = validate_administer_help_request,
                         onupdate = update_administer_help_request,
                         )
    
    return dict(form=form)


def validate_administer_help_request(form):
    
    # validation handles any checking (none here) and also any 
    # amendments to the form variable  - adding user and date of admin
    form.vars.admin_id = auth.user_id
    form.vars.admin_decision_date =  datetime.date.today().isoformat()


def update_administer_help_request(form):
    
    # Email the decision to the proposer
    # TODO - create and link to a Google Calendar for volunteer periods
    
    # retrieve the whole form record to get at the contact details
    contact = form.record.contact_id
    
    # set a flash message
    flash_message  = CENTER(B('Decision emailed to project member at {}.'.format(contact.email)), _style='color: green')
    
    if form.vars.admin_status == 'Approved':
        # email the decision
        mail.send(to=contact.email,
                  subject='Decision on request for project help at SAFE',
                  message='Dear {},\n\nLucky template {}'.format(contact.first_name, form.vars.admin_notes))
        # build the event and add to the volunteer calendar
        event = {'summary': form.record.project_id.represent,
                 'description': form.record.work_description,
                 'start': {'date': form.record.start_date.isoformat()},
                 'end':   {'date': form.record.end_date.isoformat()},
                }
        event = post_event_to_google_calendar(event, calID['help_request'])
        session.flash = flash_message
    elif form.vars.admin_status == 'Rejected':
        mail.send(to=contact.email,
                  subject='Decision on request for project help at SAFE',
                  message='Dear {},\n\nUnlucky template\n\n {}'.format(contact.first_name, form.vars.admin_notes))
        session.flash = flash_message
    else:
        pass
