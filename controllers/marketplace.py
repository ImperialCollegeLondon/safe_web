import datetime
from safe_web_global_functions import (link_button, admin_decision_form,
                                       safe_mailer, datepicker_script)

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
    links = [link_button("marketplace","view_volunteer", 'id')]
    
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


def view_volunteer():
    
    """
    Custom public volunteer detail view
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.help_offered(record_id)
    
    if record is None or record.admin_status != 'Approved':
            session.flash = CENTER(B('Not an approved volunteer offer record'), _style='color: red')
            redirect(URL('marketplace', 'volunteers'))
    else:
        
        # package up the information
        if auth.is_logged_in():
            email = DIV(LABEL('Email:', _class="control-label col-sm-2" ),
                        DIV(A(record.user_id.email, _href="mailto:" + record.user_id.email), _class="col-sm-10"),
                        _class='row', _style='margin:10px 10px')
        else:
            email = DIV()
        
        # form is a mix of some fixed details (Name/Institution/Type) and some editable ones
        vol = DIV(DIV(H5('Volunteer Offer'), _class="panel-heading"),
                  DIV(LABEL('Volunteer:', _class="control-label col-sm-2" ),
                      DIV(A(record.user_id.last_name + ", " + record.user_id.first_name, 
                            _href = URL('people', 'user_details', args=(record.user_id))),
                          _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Institution:', _class="control-label col-sm-2" ),
                      DIV(record.user_id.institution, _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  email,
                  DIV(LABEL('Dates:', _class="control-label col-sm-2" ),
                      DIV(CAT(record.available_from, ' to ', record.available_to),
                          _class='col-sm-10'),
                       _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Statement of interests:', _class="control-label col-sm-2" ),
                      DIV(record.statement_of_interests.replace('\n', '<br />'),  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Volunteer type:', _class="control-label col-sm-2" ),
                      DIV(record.volunteer_type, _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Research areas:', _class="control-label col-sm-2" ),
                      DIV(', '.join(record.research_areas), _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  _class="panel panel-primary")
    
    return dict(vol = vol)


@auth.requires_login()
def volunteer_details():
    
    """
    This controller shows a SQLFORM to submit or update an offer to
    volunteer at the SAFE project.
    
    The controller then passes the response through validation before 
    sending a confirmation email out.
    """
    
    # do we have a request for an existing help request post?
    request_id = request.args(0)
    
    if request_id is not None:
        record = db.help_offered(request_id)
    else:
        record = None
        
    if request_id is not None and record is None:
        # avoid unknown blogs
        session.flash = B(CENTER('Invalid volunteer offer id'), _style='color:red;')
        redirect(URL('marketplace','volunteers'))
        
    elif record is None or record.user_id == auth.user.id or auth.has_membership('admin'):
        
        if record is None:
            buttons =  [TAG.BUTTON('Submit', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='create')]
            readonly = False
        else:
            readonly = True if record.admin_status == 'Submitted' else False
            buttons =  [TAG.BUTTON('Update and resubmit', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='update')]
        
        db.help_offered.research_areas.comment = 'Select at least one research area of interest to help match you to projects.'
        
        form = SQLFORM(db.help_offered,
                       fields =['volunteer_type',
                                'statement_of_interests',
                                'research_areas',
                                'available_from',
                                'available_to'],
                        record = record,
                        buttons = buttons,
                        comments=True,
                        showid = False,
                        readonly = readonly)
        
        if form.validate(onvalidation=validate_volunteer):
            
            req_keys = list(request.vars.keys())
            
            # get and add a comment to the history
            hist_str = '[{}] {} {}\\n -- {}\\n'
            new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                       auth.user.first_name,
                                                       auth.user.last_name,
                                                       'Volunteer offer created' if request_id is None else "Volunteer offer updated")
            
            if 'update' in req_keys:
                id = record.update_record(admin_status = 'Submitted',
                                          admin_history = new_history + record.admin_history,
                                          **db.help_offered._filter_fields(form.vars))
                id = id.id
                msg = CENTER(B('Volunteer offer updated and resubmitted for approval.'), _style='color: green')
            elif 'create' in req_keys:
                id = db.help_offered.insert(admin_status = 'Submitted',
                                            admin_history=new_history, 
                                            **db.help_offered._filter_fields(form.vars))
                msg = CENTER(B('Volunteer offer created and submitted for approval.'), _style='color: green')
            else:
                pass
            
            # Email the link
            template_dict = {'name': auth.user.first_name, 
                             'url': URL('marketplace', 'volunteer_details', args=[id], scheme=True, host=True),
                             'submission_type': 'volunteer offer'}
            
            safe_mailer(to=auth.user.email,
                       subject='SAFE: volunteer offer submitted',
                       template =  'generic_submitted.html',
                       template_dict = template_dict)
            
            session.flash = msg
            redirect(URL('marketplace','volunteer_details', args=[id]))
            
        elif form.errors:
            response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
        else:
            pass
        
        # package in controller
        if not readonly:
            form.custom.widget.statement_of_interests['_rows'] = 4
            form.custom.widget.available_from['_class'] = "form-control input-sm"
            form.custom.widget.available_to['_class'] = "form-control input-sm"
        
        if record is None:
            status = ""
            # vis = ""
        else:
            status =    DIV(approval_icons[record.admin_status], XML('&nbsp'),
                           'Status: ', XML('&nbsp'), record.admin_status, 
                            _class='col-sm-3',
                            _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            # if record.hidden:
            #     vis = DIV('Hidden', _class='col-sm-1 col-sm-offset-1',
            #               _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            # else:
            #     vis = DIV('Visible', _class='col-sm-1 col-sm-offset-1',
            #               _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            
                      
        panel_header = DIV(H5('Project help request', _class='col-sm-9'), status, # vis,
                           _class='row', _style='margin:0px 10px')
        
        form = FORM(DIV(DIV(panel_header, _class="panel-heading"),
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
                        datepicker_script(html_id = 'vol_datepicker',
                                          autoclose = 'true',
                                          startDate ='"+0d"',
                                          endDate ='"+365d"'))
    else: 
        # security doesn't allow people editing other users volunteer offers
        session.flash = CENTER(B('You do not have permission to edit this volunteer offer.'), _style='color: red')
        redirect(URL('marketplace','volunteers', args=request_id))
    
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
            poster = record.user_id
            
            template_dict = {'name': poster.first_name, 
                             'url': URL('marketplace', 'volunteer_details', args=[request_id], scheme=True, host=True),
                             'public_url': URL('marketplace', 'view_volunteer', args=[request_id], scheme=True, host=True),
                             'admin': auth.user.first_name + ' ' + auth.user.last_name,
                             'submission_type': 'volunteer offer'}
            
            # pick an decision
            if admin.vars.decision == 'Approved':
                
                safe_mailer(to=poster.email,
                           subject='SAFE: volunteer offer approved',
                           template =  'generic_approved.html',
                           template_dict = template_dict)
                
                msg = CENTER(B('Volunteer offer approval emailed to poster at {}.'.format(poster.email)), _style='color: green')
            
            elif admin.vars.decision == 'Resubmit':

                safe_mailer(to=poster.email,
                           subject='SAFE: volunteer offer requires resubmission',
                           template =  'generic_resubmit.html',
                           template_dict = template_dict)
                
                msg = CENTER(B('Volunteer offer resubmission emailed to poster at {}.'.format(poster.email)), _style='color: green')
            
            else:
                pass
            
            redirect(URL('marketplace','administer_volunteers'))
            session.flash = msg
            
        elif admin.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
    else:
        admin = DIV()
    
    # pass components to the view
    return dict(form=form,  admin_history=admin_history, admin=admin)


@auth.requires_login()
def validate_volunteer(form):
    
    # validation handles any checking and also any amendments to the form variable  - adding user and date 
    # - much of this is now redundant because of the use of the range datepicker
    #   but people could always hijack the form
    
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


@auth.requires_membership('admin')
def administer_volunteers():
    
    """
    This controller handles:
     - presenting admin users with a list of submitted volunteer offers
     - forwarding to volunteer details page, which provides admin interface
    """
    
    
    links = [link_button("marketplace","volunteer_details", 'id')]
    
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
                     (db.help_request.end_date > datetime.date.today()) & \
                     (db.help_request.project_id == db.project_id.id) & \
                     (db.project_id.project_details_id == db.project_details.id)
    
    # links to custom view page
    links = [link_button("marketplace","view_help_request", 'help_request.id')]
    
    # create a link using the project name
    def link_formatter(value, row):
        if row.help_request.available:
            return A(value, _href=URL('projects','project_view',
                                      args=row.project_details.project_id),
                     _style='text-decoration:line-through') + ' (Vacancy no longer available)'
        else:
            return A(value, _href=URL('projects','project_view',
                                      args=row.project_details.project_id))

    db.project_details.title.represent = lambda value, row: link_formatter(value, row)
    
    # update how paid and unpaid are displayed
    paid = {True: I(_class='glyphicon glyphicon-ok-circle',
                    _style="color:green;font-size: 1.3em;"),
            False: I(_class='glyphicon glyphicon-remove-circle',
                     _style="color:red;font-size: 1.3em;")}
    db.help_request.paid_position.represent = lambda value, row: paid[row.help_request.paid_position]
    
    # hide the ID fields which are used in row information in links
    db.help_request.id.readable = False
    db.help_request.available.readable = False
    db.project_details.project_id.readable = False
    
    form = SQLFORM.grid(query=approved_posts, csv=False, 
                        fields=[db.help_request.id,
                                db.project_details.title,
                                db.project_details.project_id,
                                db.help_request.start_date,
                                db.help_request.end_date,
                                db.help_request.vacancy_type,
                                db.help_request.paid_position,
                                db.help_request.available
                                ], 
                        headers = {'project_details.title': 'Project Title'},
                        maxtextlength=250,
                        links=links,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False,
                        formargs={'showid':False})
    
    return dict(form=form)

def view_help_request():
    
    """
    Custom request detail view
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.help_request(record_id)
    
    if record is None or record.admin_status != 'Approved':
            session.flash = CENTER(B('Not an approved vacancy record'), _style='color: red')
            redirect(URL('marketplace', 'help_requests'))
    else:
        
        # get a row with all the joined details needed
        query =  db((db.help_request.id == record_id) &
                    (db.help_request.project_id == db.project_id.id) &
                    (db.project_details.project_id == db.project_id.id))
        
        row = query.select().first()
        
        # package up the information
        if auth.is_logged_in():
            email = DIV(LABEL('Email:', _class="control-label col-sm-2" ),
                        DIV(A(record.user_id.email, _href="mailto:" + record.user_id.email), _class="col-sm-10"),
                        _class='row', _style='margin:10px 10px')
        else:
            email = DIV()
        
        if record.available:
            hdr = 'This vacancy is no longer available'
        else:
            hdr = 'Vacancy Advert'
        
        req = DIV(DIV(H5(hdr), _class="panel-heading"),
                  DIV(LABEL('Project title:', _class="control-label col-sm-2" ),
                      DIV(A(row.project_details.title, 
                            _href=URL("projects","project_view", args=[row.project_details.id])),
                          _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Research areas:', _class="control-label col-sm-2" ),
                      DIV(', '.join(row.project_details.research_areas),  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Dates:', _class="control-label col-sm-2" ),
                       DIV(row.help_request.start_date, ' to ', row.help_request.end_date,
                           _class='col-sm-10'),
                       _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Work description:', _class="control-label col-sm-2" ),
                      DIV(XML(row.help_request.work_description.replace('\n', '<br />')),  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Vacancy type:', _class="control-label col-sm-2" ),
                      DIV(XML(row.help_request.vacancy_type),  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),                      
                  DIV(LABEL('Paid position?', _class="control-label col-sm-2" ),
                      DIV(CAT('This ', B('is' if row.help_request.paid_position else 'is not') , ' a paid position'),
                          _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Website for details', _class="control-label col-sm-2" ),
                      DIV(row.help_request.url,  _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV('Contact details', _class='panel-footer'),
                  DIV(LABEL('Project contact:', _class="control-label col-sm-2" ),
                      DIV(A(record.user_id.last_name + ", " + record.user_id.first_name,
                            _href = URL('people', 'user_details', args=(record.user_id))), 
                          _class='col-sm-4'),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Institution:', _class="control-label col-sm-2" ),
                      DIV(record.user_id.institution, _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  email,
                  _class="panel panel-primary")
    
    return dict(req=req)


@auth.requires_login()
def help_request_details():
    
    """
    This controller shows a SQLFORM to submit or update a request for help
    on a project. Only projects for which the logged in user is a 
    coordinator are available.
    
    The controller then passes the response through validation before 
    sending a confirmation email out.
    """
    
    # do we have a request for an existing help request post?
    request_id = request.args(0)
    
    if request_id is not None:
        record = db.help_request(request_id)
    else:
        record = None
        
    if request_id is not None and record is None:
        # avoid unknown blogs
        session.flash = B(CENTER('Invalid vacancy advert id'), _style='color:red;')
        redirect(URL('marketplace','help_requests'))
        
    elif record is None or record.user_id == auth.user.id or auth.has_membership('admin'):
        
        if record is None:
            buttons =  [TAG.BUTTON('Submit', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='create')]
            readonly = False
        else:
            readonly = True if record.admin_status == 'Submitted' else False
            fill_label = "Mark as available" if record.available else "Mark as unavailable"
            buttons =  [TAG.BUTTON(fill_label, _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='available'), 
                        XML('&nbsp;')*5,
                        TAG.BUTTON('Update and resubmit', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='update')]
        
        # Restrict the project choices
        # - find the acceptable project ID numbers
        if auth.has_membership('admin'):
            # admins can advertise on any project
            query = db(db.project_details.project_id > 0)
        else:
            # otherwise coordinators can advertise on their own projects
            query = db((db.project_members.user_id == auth.user.id) &
                       (db.project_members.is_coordinator == 'T') & 
                       (db.project_members.project_id == db.project_id.id) &
                       (db.project_details.project_id == db.project_id.id) &
                       (db.project_details.admin_status == 'Approved'))
    
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
                                    'work_description',
                                    'vacancy_type',
                                    'paid_position',
                                    'url'],
                            readonly = readonly,
                            record = record,
                            buttons = buttons,
                            showid=False)
        
            if form.validate(onvalidation=validate_help_request):
            
                req_keys = list(request.vars.keys())
                if 'available' in req_keys:
                    # provide a simple toggle option for the availability
                    hist_str = '[{}] {} {}\\n -- Vacancy marked as {}\\n'
                    new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                  auth.user.first_name,
                                                  auth.user.last_name,
                                                  "available" if record.available else "unavailable")
                    id = record.update_record(available = not record.available,
                                              admin_history = new_history + record.admin_history)
                    id = id.id
                    msg = CENTER(B('Vacancy availability updated.'), _style='color: green')
                else:
                    
                    # get and add a comment to the history
                    hist_str = '[{}] {} {}\\n -- {}\\n'
                    new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                               auth.user.first_name,
                                                               auth.user.last_name,
                                                               'Vacancy advert created' if request_id is None else "Vacancy advert updated")
            
                    if 'update' in req_keys:
                        id = record.update_record(admin_status = 'Submitted',
                                                  admin_history = new_history + record.admin_history,
                                                  **db.help_request._filter_fields(form.vars))
                        id = id.id
                        msg = CENTER(B('Vacancy advert updated and resubmitted for approval.'), _style='color: green')
                    elif 'create' in req_keys:
                        id = db.help_request.insert(admin_status = 'Submitted',
                                                    admin_history=new_history, 
                                                    **db.help_request._filter_fields(form.vars))
                        msg = CENTER(B('Vacancy advert created and submitted for approval.'), _style='color: green')
                    else:
                        pass
            
                    # Email the link
                    template_dict = {'name': auth.user.first_name, 
                                     'url': URL('marketplace', 'help_request_details', args=[id], scheme=True, host=True),
                                     'submission_type': 'project help request'}
            
                    safe_mailer(to=auth.user.email,
                               subject='SAFE: Vacancy advert submitted',
                               template =  'generic_submitted.html',
                               template_dict = template_dict)
            
                session.flash = msg
                redirect(URL('marketplace','help_request_details', args=[id]))
            
            elif form.errors:
                response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
            else:
                pass
        
            # package form into a panel
            if record is None:
                status = ""
                # vis = ""
            else:
                status =    DIV(approval_icons[record.admin_status], XML('&nbsp'),
                               'Status: ', XML('&nbsp'), record.admin_status, 
                                _class='col-sm-3',
                                _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
                # if record.hidden:
                #     vis = DIV('Hidden', _class='col-sm-1 col-sm-offset-1',
                #               _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
                # else:
                #     vis = DIV('Visible', _class='col-sm-1 col-sm-offset-1',
                #               _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
        
            panel_header = DIV(H5('Project vacancy advert', _class='col-sm-9'), status, # vis,
                               _class='row', _style='margin:0px 10px')
        
            # package in controller
            if not readonly:
                form.custom.widget.work_description['_rows'] = 4
                form.custom.widget.start_date['_class'] = "form-control input-sm"
                form.custom.widget.end_date['_class'] = "form-control input-sm"
            
            # set up availability header
            if record is not None:
                if record.available:
                    avail = DIV(LABEL('Availability:', _class="control-label col-sm-2" ),
                                DIV("Vacancy is currently available" ,  _class="col-sm-10"),
                                _class='row', _style='margin:10px 10px')
                else:
                    avail = DIV(LABEL('Availability:', _class="control-label col-sm-2" ),
                                DIV("Vacancy is  marked as unavailable" ,  _class="col-sm-10"),
                                _class='row', _style='margin:10px 10px')
            else:
                # blank DIV for new headers
                avail = DIV()
            
            # locally update the description representation to allow formatting
            db.help_request.work_description.represent = lambda text, row: PRE(text)
            
            form = FORM(DIV(DIV(panel_header, _class="panel-heading"),
                            DIV(form.custom.begin,
                                avail,
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
                                HR(),
                                DIV(P('Choose a vacancy type. If the post is paid, check the box and where '
                                      'possible provide a link for any further details and the application procedure.'),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(LABEL('Vacancy type:', _class="control-label col-sm-2" ),
                                    DIV(form.custom.widget.vacancy_type, _class='col-sm-7'),
                                    LABEL(form.custom.widget.paid_position, 'Paid Position', 
                                          _class="control-label col-sm-3"),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(LABEL('Website for details', _class="control-label col-sm-2" ),
                                    DIV(form.custom.widget.url,  _class="col-sm-10"),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(DIV(form.custom.submit,  _class="col-sm-10 col-sm-offset-2"),
                                    _class='row', _style='margin:10px 10px'),
                                form.custom.end,
                               _class='panel_body'),
                            _class="panel panel-primary"),
                            datepicker_script(html_id = 'help_datepicker',
                                              autoclose = 'true',
                                              startDate ='"+0d"',
                                              endDate ='""'))
    
    else: 
        # security doesn't allow people editing other users blogs
        session.flash = CENTER(B('You do not have permission to edit this vacancy advert.'), _style='color: red')
        redirect(URL('marketplace','help_requests', args=request_id))
    
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
            poster = record.user_id
            
            template_dict = {'name': poster.first_name, 
                             'url': URL('marketplace', 'help_request_details', args=[request_id], scheme=True, host=True),
                             'public_url': URL('marketplace', 'view_help_request', args=[request_id], scheme=True, host=True),
                             'admin': auth.user.first_name + ' ' + auth.user.last_name,
                             'submission_type': 'project help request'}
            
            # pick an decision
            if admin.vars.decision == 'Approved':
                
                safe_mailer(to=poster.email,
                           subject='SAFE: vacancy advert approved',
                           template =  'generic_approved.html',
                           template_dict = template_dict)
                
                msg = CENTER(B('Vacancy advert approval emailed to poster at {}.'.format(poster.email)), _style='color: green')
            
            elif admin.vars.decision == 'Resubmit':

                safe_mailer(to=poster.email,
                           subject='SAFE: Vacancy advert requires resubmission',
                           template =  'generic_resubmit.html',
                           template_dict = template_dict)
                
                msg = CENTER(B('Vacancy advert resubmission emailed to poster at {}.'.format(poster.email)), _style='color: green')
            
            else:
                pass
            
            redirect(URL('marketplace','administer_help_requests'))
            session.flash = msg
            
        elif admin.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
    else:
        admin = DIV()
    
    # pass components to the view
    return dict(form=form,  admin_history=admin_history, admin=admin)


def validate_help_request(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.user_id = auth.user.id
    form.vars.submission_date =  datetime.date.today().isoformat()
    
    # check that available_to is after available_from
    if form.vars.start_date >= form.vars.end_date:
        form.errors.available_to = 'The availability end date is earlier than the start date'
    
    if form.vars.start_date < datetime.date.today():
        form.errors.start_date = 'Your start date is in the past.'

@auth.requires_membership('admin')
def administer_help_requests():
    
    """
    This controller handles:
     - presenting admin users with a list of submiteed requests for help
     - forwarding to help request details page, which provides admin interface
    """
    
    links = [link_button("marketplace","view_help_request", 'id')]
    
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
