import datetime

## -----------------------------------------------------------------------------
## Volunteer marketplace
## - volunteers(): controller to provide a public view of available offers
## - new_help_request(): controller for project coordinators to create offers
## - validate_new_volunteer(): checking inputs
## - volunteer_details(): takes over from SQLFORM.grid view from volunteers()
##                        introduces an option for project coordinators to edit and delete
##                        provides an admin interface
## - administer_volunteers(): SQLFORM.grid allowing admins to see Submitted requests 
##                            and jump to admin interface on details page
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
    
    # package in controller
    form.custom.widget.statement_of_interests['_rows'] = 4
    form.custom.widget.available_from['_class'] = "form-control input-sm"
    form.custom.widget.available_to['_class'] = "form-control input-sm"
    
    
    form = FORM(DIV(DIV(H5('Research visit details'), _class="panel-heading"),
                    DIV(form.custom.begin, 
                        DIV(LABEL('Volunteer type:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.volunteer_type,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Statement of interests:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.statement_of_interests,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Research areas:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.research_areas,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Dates:', _class="control-label col-sm-2" ),
                            DIV(DIV(form.custom.widget.available_from,
                                    SPAN('to', _class="input-group-addon input-sm"),
                                    form.custom.widget.available_to,
                                    _class="input-daterange input-group", _id="vol_datepicker"),
                                _class='col-sm-10'),
                            _class='row', _style='margin:10px 10px'),
                        DIV(DIV(form.custom.submit,  _class="col-sm-10 col-sm-offset-2"),
                            _class='row', _style='margin:10px 10px'),
                        form.custom.end,
                       _class='panel_body'),
                    _class="panel panel-primary"),
                    datepicker_script(id = 'vol_datepicker',
                                      autoclose = 'true',
                                      startDate ='"+0d"',
                                      endDate ='"+365d"'))
    
    
    return dict(form=form)



@auth.requires_login()
def validate_new_volunteer(form):
    
    # validation handles any checking and also any amendments to the form variable  - adding user and date 
    # - much of this is now redundant because of the use of the range datepicker
    #   but people could always hijack the form
    
    form.vars.user_id = auth.user_id
    form.vars.submission_date =  datetime.date.today().isoformat()
    new_history = '[{}] {} {}\\n -- Volunteer offer created.\\n'
    form.vars.admin_history = new_history.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                 auth.user.first_name, auth.user.last_name)
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

@auth.requires_login()
def volunteer_details():
    
    """
    Custom public project view - displays the project and any members or outputs
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.help_offered(record_id)
    
    if record is None:
            session.flash = CENTER(B('Not an approved volunteer offer record'), _style='color: red')
            redirect(URL('marketplace', 'volunteers'))
    else:
        
        # viewing permissions
        if auth.user.id == record.user_id and record.admin_status != 'Submitted':
            # Submitter can edit Approved and Resubmit and delete
            buttons = [TAG.BUTTON('Update and resubmit', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='update'), 
                       XML('&nbsp;')*10,
                       TAG.BUTTON('Delete', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='delete')]
            readonly = False
        elif auth.user.id == record.user_id or record.admin_status == 'Approved':
            # Submitter can always _view_ Submitted 
            # anyone can  view approved ones
            buttons = []
            readonly = True
        else:
            session.flash = CENTER(B('Not an approved volunteer offer record'), _style='color: red')
            redirect(URL('marketplace', 'volunteer_details'))
        
        # get a SQLFORM to edit the record
        form = SQLFORM(db.help_offered,
                        fields = ['available_from','available_to',
                                  'statement_of_interests', 
                                  'research_areas','volunteer_type'],
                        record=record,
                        buttons=buttons,
                        readonly=readonly)
        
        if form.process().accepted:
            keys =  request.vars.keys()
            if 'update' in keys:
                # update and resubmit for approval
                session.flash = CENTER(B('Volunteer offer updated and resubmitted.'), _style='color: green')
                admin_str = '[{}] {} {}\\n -- Volunteer offer updated\\n'
                new_history = admin_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                           auth.user.first_name,
                                                           auth.user.last_name) + record.admin_history
                record.update_record(admin_history = new_history,
                                     admin_status = 'Submitted')
                redirect(URL('marketplace','volunteer_details', args=[record.id]))
            if 'delete' in keys:
                # delete
                record.delete_record()
                session.flash = CENTER(B('Volunteer offer deleted.'), _style='color:red')
                redirect(URL('marketplace','volunteers'))
        else:
            pass
        
        # package in controller
        if not readonly:
            form.custom.widget.statement_of_interests['_rows'] = 4
            form.custom.widget.available_from['_class'] = "form-control input-sm"
            form.custom.widget.available_to['_class'] = "form-control input-sm"
        
        panel_header = DIV(H5('Volunteer details', _class='col-sm-9'),
                           DIV(approval_icons[record.admin_status], XML('&nbsp'),
                               'Status: ', XML('&nbsp'), record.admin_status, 
                               _class='col-sm-3',
                               _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;'),
                           _class='row', _style='margin:0px 0px')
        
        # form is a mix of some fixed details (Name/Institution/Type) and some editable ones
        vol = FORM(form.custom.begin,
                    DIV(DIV(panel_header, _class="panel-heading"),
                        DIV(LABEL('Volunteer:', _class="control-label col-sm-2" ),
                            DIV(A(record.user_id.last_name + ", " + record.user_id.first_name, 
                                  _href = URL('people', 'users', args=('view','auth_user', record.user_id),
                                  user_signature=True)), _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Institution:', _class="control-label col-sm-2" ),
                            DIV(record.user_id.institution, _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Email:', _class="control-label col-sm-2" ),
                            DIV(A(record.user_id.email, _href="mailto:" + record.user_id.email), _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Dates:', _class="control-label col-sm-2" ),
                             DIV(DIV(form.custom.widget.available_from,
                                     SPAN('to', _class="input-group-addon input-sm"),
                                     form.custom.widget.available_to,
                                     _class="input-daterange input-group", _id="vol_datepicker"),
                                 _class='col-sm-10'),
                             _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Statement of interests:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.statement_of_interests,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Volunteer type:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.volunteer_type, _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Research areas:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.research_areas,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(form.custom.submit, _class='panel-footer'),
                        _class="panel panel-primary"),
                        form.custom.end,
                        datepicker_script(id = 'vol_datepicker',
                                          autoclose = 'true',
                                          startDate ='"+0d"',
                                          endDate ='"+365d"'))
    
    # admin history display
    if record is not None and record.admin_history is not None:
        admin_history = DIV(DIV(H5('Admin History', ), _class="panel-heading"),
                            DIV(XML(record.admin_history.replace('\\n', '<br />'),
                                    sanitize=True, permitted_tags=['br/']),
                                _class = 'panel_body'),
                            DIV(_class="panel-footer"),
                            _class='panel panel-primary')
    else:
        admin_history = DIV()
    
    ## ADMIN INTERFACE
    if record is not None and auth.has_membership('admin') and record.admin_status == 'Submitted':
        
        admin = admin_decision_form(['Resubmit','Approved'])
        
        if admin.process(formname='admin').accepted:
            
            # update record with decision
            admin_str = '[{}] {} {}\\n ** Decision: {}\\n ** Comments: {}\\n'
            new_history = admin_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                       auth.user.first_name,
                                                       auth.user.last_name,
                                                       admin.vars.decision,
                                                       admin.vars.comment) + record.admin_history
            
            record.update_record(admin_status = admin.vars.decision,
                                 admin_history = new_history)
            
            # pick an decision
            proposer = record.user_id
            
            if admin.vars.decision == 'Approved':
                mail.send(to=proposer.email,
                          subject='SAFE volunteer offer submission',
                          message='Dear {},\n\nLucky template\n\n {}'.format(proposer.first_name, admin.vars.comment))
            elif admin.vars.decision == 'Resubmit':
                mail.send(to=proposer.email,
                          subject='SAFE volunteer offer resubmission',
                          message='Dear {},\n\nChanges needed\n\n {}'.format(proposer.first_name, admin.vars.comment))
            else:
                pass
            
            redirect(URL('marketplace','administer_volunteers'))
            session.flash = CENTER(B('Decision emailed to volunteer at {}.'.format(proposer.email)), _style='color: green')
            
        elif admin.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
    else:
        admin = DIV()
    
    # pass components to the view
    return dict(vol = vol, admin_history=admin_history, admin=admin)


@auth.requires_membership('admin')
def administer_volunteers():
    
    """
    This controller handles:
     - presenting admin users with a list of submitted volunteer offers
     - forwarding to volunteer details page, which provides admin interface
    """
    
    links = [dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                      SPAN('View', _class="buttontext button"),
                                      _class="button btn btn-default", 
                                      _href=URL("marketplace","volunteer_details", 
                                      args=[row.id], user_signature=True),
                                      _style='padding: 3px 5px 3px 5px;'))]
    
    # get a query of pending requests with user_id
    form = SQLFORM.grid(query=(db.help_offered.admin_status == 'Submitted'), csv=False,
                        fields=[db.help_offered.user_id,
                                db.help_offered.volunteer_type,
                                db.help_offered.available_from,
                                db.help_offered.available_to],
                         maxtextlength=250,
                         deletable=False,
                         editable=False,
                         create=False,
                         details=False,
                         links=links)
    
    return dict(form=form)


## -----------------------------------------------------------------------------
## Help sought marketplace
## - help_requests(): controller to provide a public view of available requests
## - new_help_request(): controller for project coordinators to create requests
## - validate_new_help_request(): checking inputs
## - help_request_details(): takes over from SQLFORM.grid view from help_requests()
##                           introduces an option for project coordinators to edit and delete
##                           provides an admin interface
## - administer_help_requests(): SQLFORM.grid allowing admins to see Submitted requests 
##                               and jump to admin interface on details page
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
               (db.project_members.project_id == db.project_id.id) &
               (db.project_details.project_id == db.project_id.id))
    
    # - modify the help_request project_id requirements within this controller
    db.help_request.project_id.requires = IS_IN_DB(query, db.project_details.project_id, '%(title)s', zero=None)
    
    # check to see if anything is available
    if query.count() == 0:
        form =  CENTER(B('You are not registered as a coordinator of any projects.'), _style='color: red')
    else:
        form =  SQLFORM(db.help_request,
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
    
    # package in controller
    form.custom.widget.work_description['_rows'] = 4
    form.custom.widget.start_date['_class'] = "form-control input-sm"
    form.custom.widget.end_date['_class'] = "form-control input-sm"
    
    form = FORM(DIV(DIV(H5('Research visit details'), _class="panel-heading"),
                    DIV(form.custom.begin, 
                        DIV(LABEL('Project:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.project_id,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Work description:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.work_description,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Dates:', _class="control-label col-sm-2" ),
                            DIV(DIV(form.custom.widget.start_date,
                                    SPAN('to', _class="input-group-addon input-sm"),
                                    form.custom.widget.end_date,
                                    _class="input-daterange input-group", _id="help_datepicker"),
                                _class='col-sm-10'),
                            _class='row', _style='margin:10px 10px'),
                        DIV(DIV(form.custom.submit,  _class="col-sm-10 col-sm-offset-2"),
                            _class='row', _style='margin:10px 10px'),
                        form.custom.end,
                       _class='panel_body'),
                    _class="panel panel-primary"),
                    datepicker_script(id = 'help_datepicker',
                                      autoclose = 'true',
                                      startDate ='"+0d"',
                                      endDate ='""'))
    
    return dict(form=form)


def validate_new_help_request(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.user_id = auth.user.id
    form.vars.submission_date =  datetime.date.today().isoformat()
    new_history = '[{}] {} {}\\n -- Help request created.\\n'
    form.vars.admin_history = new_history.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                 auth.user.first_name, auth.user.last_name)
    
    # check that available_to is after available_from
    if form.vars.start_date >= form.vars.end_date:
        form.errors.available_to = 'The availability end date is earlier than the start date'
    
    if form.vars.start_date < datetime.date.today():
        form.errors.start_date = 'Your start date is in the past.'


@auth.requires_login()
def help_request_details():
    
    """
    Custom request detail view
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.help_request(record_id)
    
    if record is None:
            session.flash = CENTER(B('Not an approved help request record'), _style='color: red')
            redirect(URL('marketplace', 'help_requests'))
    else:
        # get the intersection of the set of project coordinators 
        # for the record and this users id
        query = db((db.project_members.user_id == auth.user.id) &
                   (db.project_members.is_coordinator == 'T') & 
                   (db.project_members.project_id == db.project_id.id))
        
        # viewing permissions
        if (query.count() > 0 and record.admin_status != 'Submitted') or auth.has_membership('admin'):
            # coordinators can edit Approved and Rejected
            buttons = [TAG.BUTTON('Update and resubmit', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='update'), 
                       XML('&nbsp;')*10,
                       TAG.BUTTON('Delete', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='delete')]
            readonly = False
        elif query.count() > 0 or record.admin_status == 'Approved':
            # coordinators can always view Submitted but not edit
            # anyone can  view approved ones
            buttons = []
            readonly = True
        else:
            session.flash = CENTER(B('Not an approved help request record'), _style='color: red')
            redirect(URL('marketplace', 'help_requests'))
        
        # get a row with all the joined details needed
        query =  db((db.help_request.id == record_id) &
                    (db.help_request.project_id == db.project_id.id) &
                    (db.project_details.project_id == db.project_id.id))
        
        row = query.select().first()
        
        # get a SQLFORM to edit the record
        form = SQLFORM(db.help_request,
                        fields = ['start_date','end_date','work_description'],
                        record=record,
                        buttons=buttons,
                        readonly=readonly)
        
        if form.process().accepted:
            keys =  request.vars.keys()
            if 'update' in keys:
                # update and resubmit for approval
                session.flash = CENTER(B('Help request updated and resubmitted.'), _style='color: green')
                admin_str = '[{}] {} {}\\n -- Help request updated\\n'
                new_history = admin_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                           auth.user.first_name,
                                                           auth.user.last_name) + record.admin_history
                record.update_record(admin_history = new_history,
                                     admin_status = 'Submitted')
                redirect(URL('marketplace','help_request_details', args=[record.id]))
            if 'delete' in keys:
                # delete
                record.delete_record()
                session.flash = CENTER(B('Help request deleted.'), _style='color:red')
                redirect(URL('marketplace','help_requests'))
        else:
            pass
        
        # package in controller
        if not readonly:
            form.custom.widget.work_description['_rows'] = 4
            form.custom.widget.start_date['_class'] = "form-control input-sm"
            form.custom.widget.end_date['_class'] = "form-control input-sm"
        
        panel_header = DIV(H5('Project help request', _class='col-sm-9'),
                           DIV(approval_icons[record.admin_status], XML('&nbsp'),
                               'Status: ', XML('&nbsp'), record.admin_status, 
                               _class='col-sm-3',
                               _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;'),
                           _class='row', _style='margin:0px 0px')
        
        # form is a mix of fixed project details and possibly editable request details
        req = FORM(form.custom.begin,
                    DIV(DIV(panel_header, _class="panel-heading"),
                        DIV(LABEL('Project title:', _class="control-label col-sm-2" ),
                            DIV(A(row.project_details.title, 
                                  _href=URL("marketplace","help_request_details", args=[record_id])),
                                _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Research areas:', _class="control-label col-sm-2" ),
                            DIV(', '.join(row.project_details.research_areas),  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Dates:', _class="control-label col-sm-2" ),
                             DIV(DIV(form.custom.widget.start_date,
                                     SPAN('to', _class="input-group-addon input-sm"),
                                     form.custom.widget.end_date,
                                     _class="input-daterange input-group", _id="help_datepicker"),
                                 _class='col-sm-10'),
                             _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Work description:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.work_description,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV('Contact details', _class='panel-footer'),
                        DIV(LABEL('Project contact:', _class="control-label col-sm-2" ),
                            DIV(A(record.user_id.last_name + ", " + record.user_id.first_name,
                                  _href = URL('people', 'users', args=('view','auth_user', record.user_id),
                                              user_signature=True)), 
                                _class='col-sm-4'),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Institution:', _class="control-label col-sm-2" ),
                            DIV(record.user_id.institution, _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Email:', _class="control-label col-sm-2" ),
                            DIV(A(record.user_id.email, _href="mailto:" + record.user_id.email), _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(form.custom.submit, _class='panel-footer'),
                        _class="panel panel-primary"),
                        form.custom.end,
                        datepicker_script(id = 'help_datepicker',
                                          autoclose = 'true',
                                          startDate ='"+0d"',
                                          endDate ='""'))
    
    # admin history display
    if record is not None and record.admin_history is not None:
        admin_history = DIV(DIV(H5('Admin History', ), _class="panel-heading"),
                            DIV(XML(record.admin_history.replace('\\n', '<br />'),
                                    sanitize=True, permitted_tags=['br/']),
                                _class = 'panel_body'),
                            DIV(_class="panel-footer"),
                            _class='panel panel-primary')
    else:
        admin_history = DIV()
    
    ## ADMIN INTERFACE
    if record is not None and auth.has_membership('admin') and record.admin_status == 'Submitted':
        
        admin = admin_decision_form(['Resubmit','Approved'])
        
        if admin.process(formname='admin').accepted:
            
            # update record with decision
            admin_str = '[{}] {} {}\\n ** Decision: {}\\n ** Comments: {}\\n'
            new_history = admin_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                       auth.user.first_name,
                                                       auth.user.last_name,
                                                       admin.vars.decision,
                                                       admin.vars.comment) + record.admin_history
            
            record.update_record(admin_status = admin.vars.decision,
                                 admin_history = new_history)
            
            # pick an decision
            proposer = record.user_id
            
            if admin.vars.decision == 'Approved':
                mail.send(to=proposer.email,
                          subject='SAFE project help request submission',
                          message='Dear {},\n\nLucky template\n\n {}'.format(proposer.first_name, admin.vars.comment))
            elif admin.vars.decision == 'Resubmit':
                mail.send(to=proposer.email,
                          subject='SAFE project help request resubmission',
                          message='Dear {},\n\nChanges needed\n\n {}'.format(proposer.first_name, admin.vars.comment))
            else:
                pass
            
            redirect(URL('marketplace','administer_help_requests'))
            session.flash = CENTER(B('Decision emailed to proposer at {}.'.format(proposer.email)), _style='color: green')
            
        elif admin.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
    else:
        admin = DIV()
    
    # pass components to the view
    return dict(req = req, admin_history=admin_history, admin=admin)


def administer_help_requests():
    
    """
    This controller handles:
     - presenting admin users with a list of submiteed requests for help
     - forwarding to help request details page, which provides admin interface
    """
    
    links = [dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                      SPAN('View', _class="buttontext button"),
                                      _class="button btn btn-default", 
                                      _href=URL("marketplace","help_request_details", 
                                      args=[row.id], user_signature=True),
                                      _style='padding: 3px 5px 3px 5px;'))]
    
    # get a query of pending requests 
    form = SQLFORM.grid(query=(db.help_request.admin_status == 'Submitted'), csv=False,
                        fields=[db.help_request.user_id,
                                db.help_request.project_id,
                                db.help_request.start_date,
                                db.help_request.end_date],
                         maxtextlength=250,
                         deletable=False,
                         editable=False,
                         create=False,
                         details=False,
                         links = links)
    
    return dict(form=form)

