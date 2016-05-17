
import datetime

## -----------------------------------------------------------------------------
## Volunteer marketplace
## - volunteers(): controller to provide a public view of available volunteers
## - new_volunteer(): controller for registered users to sign up
## - validate_new_volunteer(): checking inputs
## - volunteer_details(): takes over from SQLFORM.grid view from volunteers
##                        and introduces an option for users to delete their own
##                        volunteer offers
## - volunteer_delete(): runs actions to delete a volunteer record, available from a 
##                       button on the volunteer details page when a volunteer is logged in
## - administer_volunteers(): SQLFORM.grid allowing admins to approve/reject offers of help 
## - validate_administer_volunteers(): Inserts date and admin ID into record
## - update_administer_volunteers(): Handles accept/reject actions
## -----------------------------------------------------------------------------

def volunteers():
    
    """
    This controller shows the grid view for approved volunteer positions
    TODO - add a volunteer google calendar
    """
    
    # subset to approved posts with expiry dates in the future
    approved_posts = (db.help_offered.admin_status == 'Approved') & \
                     (db.help_offered.available_to > datetime.date.today())
    
    # links to custom view page
    links = [dict(header = '', 
                 body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                      SPAN('View', _class="buttontext button"),
                                      _class="button btn btn-default", 
                                      _href=URL("marketplace","volunteer_details", 
                                      args=[row.id], user_signature=True),
                                      _style='padding: 3px 5px 3px 5px;'))]
    
    
    # hide admin fields in the grid
    db.help_offered.admin_status.readable = False
    db.help_offered.submission_date.readable = False
    db.help_offered.admin_id.readable = False
    db.help_offered.admin_notes.readable = False
    db.help_offered.admin_decision_date.readable = False
    
    form = SQLFORM.grid(query=approved_posts, csv=False, 
                        fields=[db.help_offered.user_id, 
                                db.help_offered.volunteer_type, 
                                db.help_offered.research_areas, 
                                db.help_offered.available_from, 
                                db.help_offered.available_to], 
                        links=links,
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False)
    
    return dict(form=form)


@auth.requires_login()
def new_volunteer():
    
    """
    This controller shows a SQLFORM to submit an offer to volunteer
    and then passes the response through validation before sending
    emails out.
    """
    
    db.help_offered.research_areas.comment = 'Select at least one research area of interest to help match you to projects.'
    
    form = SQLFORM(db.help_offered,
                   fields =['volunteer_type',
                            'statement_of_interests',
                            'research_areas',
                            'available_from',
                            'available_to'],
                    comments=True,
                    showid = False
                    )
    
    if form.process(onvalidation=validate_new_volunteer).accepted:

        # Signal success and email the proposer
        mail.send(to=auth.user.email,
              subject='SAFE volunteer offer submitted',
              message='Welcome to SAFE')
        
        session.flash = CENTER(B('Offer to volunteer successfully submitted.'), _style='color: green')
        redirect(URL('marketplace', 'volunteers'))
    elif form.errors:
        response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
    else:
        pass
    
    return dict(form=form)


@auth.requires_login()
def validate_new_volunteer(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.user_id = auth.user_id
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
    
    if form.vars.research_areas == []:
        form.errors.research_areas = 'You must select at least one research area.'


def volunteer_details():
    
    """
    Custom public project view - displays the project and any members or outputs
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.help_offered(record_id)
    
    if record is not None:
        
        # only allow volunteers to see rejected or pending records
        if record.user_id == auth.user.id:
            delete = CAT('Click here to permanently remove your offer to volunteer at the SAFE project:', 
                         XML('&nbsp;') * 5,
                         A(SPAN('Delete', _class="buttontext button"),
                           _class="button btn btn-default", 
                           _href=URL("marketplace","volunteer_delete", args=[record_id], user_signature=True),
                           _style='padding: 3px 5px 3px 5px;'))
        elif record.admin_status == 'Approved':
            delete = DIV()
        else:
            session.flash = CENTER(B('Not an approved volunteer record'), _style='color: red')
            redirect(URL('marketplace', 'volunteers'))
        
        
        vol = DIV(DIV(H5('Volunteer details'), _class="panel-heading"),
                  DIV(LABEL('Volunteer:', _class="control-label col-sm-2" ),
                      DIV(record.user_id.last_name + ", " + record.user_id.first_name, _class="col-sm-8"),
                      DIV(A('[User details]', _href = URL('people', 'users', 
                                        args=('view','auth_user', record.user_id),
                                        user_signature=True)),
                          _class="col-sm-2"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Institution:', _class="control-label col-sm-2" ),
                      DIV(record.user_id.institution, _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Email:', _class="control-label col-sm-2" ),
                      DIV(A(record.user_id.email, _href="mailto:" + record.user_id.email), _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Available from:', _class="control-label col-sm-2" ),
                      DIV(record.available_from,  _class="col-sm-4"),
                      LABEL('Available to:', _class="control-label col-sm-2" ),
                      DIV(record.available_to,  _class="col-sm-4"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Statement of interests:', _class="control-label col-sm-2" ),
                      DIV(record.statement_of_interests,  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Volunteer type:', _class="control-label col-sm-2" ),
                      DIV(record.volunteer_type, _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Research areas:', _class="control-label col-sm-2" ),
                      DIV(', '.join(record.research_areas),  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV('Admin record', _class='panel-footer'),
                  DIV(LABEL('Admin status:', _class="control-label col-sm-2" ),
                      DIV(record.admin_status,  _class="col-sm-4"),
                      LABEL('Decision date:', _class="control-label col-sm-2" ),
                      DIV(record.admin_decision_date,  _class="col-sm-4"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Admin notes:', _class="control-label col-sm-2" ),
                      DIV(record.admin_notes,  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(delete, _class='panel-footer'),
                  _class="panel panel-primary")
    else:
        session.flash = CENTER(B('Invalid volunteer record number.'), _style='color: red')
        redirect(URL('marketplace', 'volunteers'))
    
    # pass components to the view
    return dict(vol=vol)
    

@auth.requires_login()
def volunteer_delete():
    
    """
    Custom delete function
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.help_offered(record_id)
    
    if (record is None) or (record.user_id <> auth.user.id):
        session.flash = CENTER(B('Unauthorised attempt to delete volunteer offer.'), _style='color: red')
        redirect(URL('marketplace', 'volunteers'))
    else:
        record.delete_record()
        redirect(URL('marketplace', 'volunteers'))




@auth.requires_membership('admin')
def administer_volunteers():
    
    """
    This controller handles:
     - presenting admin users with a list of pending volunteers
     - TODO - editing approved volunteers?
    """
    
    # lock down which fields can be changed
    db.help_offered.user_id.writable = False
    db.help_offered.volunteer_type.writable = False
    db.help_offered.submission_date.writable = False
    db.help_offered.available_from.writable = False
    db.help_offered.available_to.writable = False
    db.help_offered.statement_of_interests.writable = False
    db.help_offered.research_areas.writable = False

    db.help_offered.admin_id.readable = False
    db.help_offered.admin_id.writable = False
    db.help_offered.admin_decision_date.readable = False
    db.help_offered.admin_decision_date.writable = False
    
    # get a query of pending requests with user_id
    form = SQLFORM.grid(query=(db.help_offered.admin_status == 'Pending'), csv=False,
                        fields=[db.help_offered.user_id,
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
    
    # we are editing a record so, user_id (which references the underlying
    # auth_user table) can be used like this
    volunteer = form.record.user_id
    
    # set a flash message
    flash_message  = CENTER(B('Decision emailed to volunteer at {}.'.format(volunteer.email)), _style='color: green')
    
    if form.vars.admin_status == 'Approved':
        # email the decision
        mail.send(to=volunteer.email,
                  subject='Decision on offer to volunteer at SAFE',
                  message='Dear {},\n\nLucky template {}'.format(volunteer.first_name, form.vars.admin_notes))
        # build the event and add to the volunteer calendar
        # event = {'summary': '{} {}'.format(volunteer.first_name, volunteer.last_name),
        #          'description': '{}: {}'.format(form.record.volunteer_type, form.record.statement_of_interests),
        #          'start': {'date': form.record.available_from.isoformat()},
        #          'end':   {'date': form.record.available_to.isoformat()},
        #         }
        # event = post_event_to_google_calendar(event, calID['volunteers'])
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
## - help_requests(): controller to provide a public view of available requests
## - new_help_request(): controller for project coordinators to create requests
## - validate_new_help_request(): checking inputs
## - help_request_details(): takes over from SQLFORM.grid view from help_requests()
##                        and introduces an option for project coordinators to delete
##                        requests offers
## - volunteer_delete(): runs actions to delete a volunteer record, available from a 
##                       button on the volunteer details page when a volunteer is logged in
## - administer_volunteers(): SQLFORM.grid allowing admins to approve/reject offers of help 
## - validate_administer_volunteers(): Inserts date and admin ID into record
## - update_administer_volunteers(): Handles accept/reject actions
## -----------------------------------------------------------------------------

def help_requests():
    
    """
    This controller shows the grid view for approved help requests
    TODO - add Google calendar link for approved requests
    """
    
    # subset to approved posts with expiry dates in the future
    approved_posts = (db.help_request.admin_status == 'Approved') & \
                     (db.help_request.end_date > datetime.date.today())
    
    # links to custom view page
    links = [dict(header = '', 
                 body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                      SPAN('View', _class="buttontext button"),
                                      _class="button btn btn-default", 
                                      _href=URL("marketplace","help_request_details", 
                                      args=[row.id], user_signature=True),
                                      _style='padding: 3px 5px 3px 5px;'))]
    
    # hide admin fields in the grid
    db.help_request.admin_status.readable = False
    db.help_request.submission_date.readable = False
    db.help_request.admin_id.readable = False
    db.help_request.admin_notes.readable = False
    db.help_request.admin_decision_date.readable = False
    
    # TODO - complete formatting links to projects and users
    #db.help_request.contact_id.represent = lambda contact_id, row: I(contact_id)
    db.help_request.project_id.represent = lambda value, row: A('Project', _href=URL('projects','project_view', args=value))
    
    approved_posts = (db.help_request.admin_status == 'Approved')
    
    form = SQLFORM.grid(query=approved_posts, csv=False, 
                        fields=[db.help_request.project_id,
                                db.help_request.start_date,
                                db.help_request.end_date,
                                db.help_request.work_description], 
                        headers = {'help_request.project_id': 'Project link'},
                        maxtextlength=250,
                        links=links,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False,
                        formargs={'showid':False})
    
    return dict(form=form)


@auth.requires_login()
def new_help_request():
    
    """
    This controller shows a SQLFORM to submit an request for help
    on a project. Only projects for which the logged in user is a 
    coordinator are available.
    
    The controller then passes the response through validation before 
    sending a confirmation email out.
    """
    
    # Restrict the project choices
    # - find the acceptable project ID numbers
    query = db((db.project_members.user_id == auth.user.id) &
               (db.project_members.is_coordinator == 'T') & 
               (db.project_members.project_id == db.project.id))
    
    # - modify the help_request project_id requirements within this controller
    db.help_request.project_id.requires = IS_IN_DB(query, db.project.id, '%(title)s', zero=None)
    
    # check to see if anything is available
    if query.count() == 0:
        form = CENTER(B('You are not registered as a coordinator of any projects.'), _style='color: red')
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
    form.vars.user_id = auth.user.id
    form.vars.submission_date =  datetime.date.today().isoformat()
    
    # check that available_to is after available_from
    if form.vars.start_date >= form.vars.end_date:
        form.errors.available_to = 'The availability end date is earlier than the start date'
    
    if form.vars.start_date < datetime.date.today():
        form.errors.start_date = 'Your start date is in the past.'



def help_request_details():
    
    """
    Custom request detail view
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.help_request(record_id)
    
    if record is not None:
        
        # get the intersection of the set of project coordinators 
        # for the record and this users id
        query = db((db.project_members.user_id == auth.user.id) &
                   (db.project_members.is_coordinator == 'T') & 
                   (db.project_members.project_id == db.project.id))
        
        # only allow coordinators to see rejected or pending records
        if query.count() > 0 :
            delete = CAT('Click here to permanently remove your request for project help:', 
                         XML('&nbsp;') * 5,
                         A(SPAN('Delete', _class="buttontext button"),
                           _class="button btn btn-default", 
                           _href=URL("marketplace","help_request_delete", args=[record_id], user_signature=True),
                           _style='padding: 3px 5px 3px 5px;'))
        elif record.admin_status == 'Approved':
            delete = DIV()
        else:
            session.flash = CENTER(B('Not an approved help request record'), _style='color: red')
            redirect(URL('marketplace', 'help_request'))
        
        
        req = DIV(DIV(H5('Project help request'), _class="panel-heading"),
                  DIV(LABEL('Project title:', _class="control-label col-sm-2" ),
                      DIV(A(record.project_id.title, 
                            _href=URL("marketplace","help_request_details", args=[record_id])),
                          _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Start date:', _class="control-label col-sm-2" ),
                      DIV(record.start_date,  _class="col-sm-4"),
                      LABEL('End date:', _class="control-label col-sm-2" ),
                      DIV(record.end_date,  _class="col-sm-4"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Research areas:', _class="control-label col-sm-2" ),
                      DIV(', '.join(record.project_id.research_areas),  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Work description:', _class="control-label col-sm-2" ),
                      DIV(record.work_description,  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV('Contact details', _class='panel-footer'),
                  DIV(LABEL('Project contact:', _class="control-label col-sm-2" ),
                      DIV(record.user_id.last_name + ", " + record.user_id.first_name, _class="col-sm-8"),
                      DIV(A('[Contact details]', _href = URL('people', 'users', 
                                        args=('view','auth_user', record.user_id),
                                        user_signature=True)),
                          _class="col-sm-2"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Institution:', _class="control-label col-sm-2" ),
                      DIV(record.user_id.institution, _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Email:', _class="control-label col-sm-2" ),
                      DIV(A(record.user_id.email, _href="mailto:" + record.user_id.email), _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV('Admin record', _class='panel-footer'),
                  DIV(LABEL('Admin status:', _class="control-label col-sm-2" ),
                      DIV(record.admin_status,  _class="col-sm-4"),
                      LABEL('Decision date:', _class="control-label col-sm-2" ),
                      DIV(record.admin_decision_date,  _class="col-sm-4"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Admin notes:', _class="control-label col-sm-2" ),
                      DIV(record.admin_notes,  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(delete, _class='panel-footer'),
                  _class="panel panel-primary")
    else:
        session.flash = CENTER(B('Invalid volunteer record number.'), _style='color: red')
        redirect(URL('marketplace', 'volunteers'))
    
    # pass components to the view
    return dict(req = req)
    

def administer_help_requests():
    
    """
    This controller handles:
     - presenting admin users with a list of pending requests for help
     - TODO - editing approved help requests?
    """
    
    # lock down which fields can be changed
    db.help_request.user_id.writable = False
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
                        fields=[db.help_request.user_id,
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
    contact = form.record.user_id
    
    # set a flash message
    flash_message  = CENTER(B('Decision emailed to project member at {}.'.format(contact.email)), _style='color: green')
    
    if form.vars.admin_status == 'Approved':
        # email the decision
        mail.send(to=contact.email,
                  subject='Decision on request for project help at SAFE',
                  message='Dear {},\n\nLucky template {}'.format(contact.first_name, form.vars.admin_notes))
        # # build the event and add to the volunteer calendar
        # event = {'summary': form.record.project_id.represent,
        #          'description': form.record.work_description,
        #          'start': {'date': form.record.start_date.isoformat()},
        #          'end':   {'date': form.record.end_date.isoformat()},
        #         }
        # event = post_event_to_google_calendar(event, calID['help_request'])
        session.flash = flash_message
    elif form.vars.admin_status == 'Rejected':
        mail.send(to=contact.email,
                  subject='Decision on request for project help at SAFE',
                  message='Dear {},\n\nUnlucky template\n\n {}'.format(contact.first_name, form.vars.admin_notes))
        session.flash = flash_message
    else:
        pass
