import datetime
from gluon.storage import Storage
import openpyxl

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



## -----------------------------------------------------------------------------
## New research visit console testing
## -----------------------------------------------------------------------------


@auth.requires_login()
def research_visit_details():
    
    """
    Complex controller to book visits to give a single page to hold:
    - Two step - booking forms are only available once the main RV
      details have been completed and submitted
    - visitors and H&S
    - booking beds at SAFE and Maliau
    - booking RA time
    - booking transfers
    
    It relies on some client side javascript to:
    - check before deleting visitors
    - update SAFE availability
    - provide check all buttons for selecting sets of checkboxes
    """
    
    # look for an existing record, otherwise a fresh start with an empty record
    rv_id = request.args(0)
    if rv_id is not None:
        record = db.research_visit(rv_id)
    else:
        record = None
    
    if rv_id is not None and record is None:
        # If the visit is given as an ID, does it really exist?
        session.flash = B(CENTER('Invalid research visit id'), _style='color:red;')
        redirect(URL('research_visits','research_visits'))
    else:
        # set up for new or existing project
        if rv_id is not None:
            
            # is the user is a coordinator of the project associated with this record
            # or the proposer of a look see visit
            if record.look_see_visit:
                editing_users = record.proposer_id
            else:
                coord_query = db((db.project_members.project_id == record.project_id) &
                                 (db.project_members.is_coordinator == 'True')).select()
                editing_users = [r.user_id for r in coord_query]
            
            readonly = False if  auth.user.id in editing_users else True
            
            # prevent users from changing the project for a visit or making it look see
            db.research_visit.project_id.writable = False
            db.research_visit.look_see_visit.writable = False
            
            button_text = 'Update research visit proposal'
        else:
            # otherwise is the user a coordinator for any project that could create a new record?
            # join the tables here to get at the title 
            coord_query = db((db.project_members.project_id == db.project.id) &
                             (db.project_members.is_coordinator == 'True'))
            readonly = False
            button_text = 'Create research visit proposal'
            
            # restrict new records to projects that the user coordinates
            # - use distinct to remove multiple coordinators
            db.research_visit.project_id.requires = IS_NULL_OR(IS_IN_DB(coord_query, 
                                                             db.project.id, 
                                                             '%(title)s',
                                                             distinct=True))
    
    # provide a form to edit/create details of visit
    # provide the research visit form
    visit = SQLFORM(db.research_visit, 
                    record = rv_id,
                    readonly = readonly,
                    fields = ['look_see_visit','project_id','title','arrival_date',
                              'departure_date','purpose','licence_details'],
                    labels = {'title':'Reference name for visit'},
                    submit_button = button_text,
                    showid = False)
        
    # process the visitor form if it is submitted
    if visit.process(onvalidation=validate_research_visit_details, formname='visit').accepted:
        
        session.flash = 'Research visit proposal registered'
        redirect(URL('research_visits','test2', args=visit.vars.id))
    else:
        
        pass
    
    if rv_id is not None:
        
        ## Create the visit editing console - a form containing
        ## A) A panel of visitors and editing controls
        ## B) A panel to set dates 
        ## C) A UI to book at SAFE
        ## E) A UI to select RA requirements
        ## F) An action selector to submit combinations
        
        # A ) VISITOR PANEL
        # A1) A table of current visitors
        query = db(db.research_visit_member.research_visit_id == rv_id)
        rows = query.select(db.auth_user.id,
                            db.auth_user.last_name,
                            db.auth_user.first_name,
                            db.auth_user.h_and_s_id,
                            db.research_visit_member.id,
                            left=db.auth_user.on( db.research_visit_member.user_id == db.auth_user.id ))
        
        # Package rows up in a table with row selectors if non read-only
        def pack_visit(r, readonly):
            
            if r.auth_user.id is None:
                nm = 'Unknown #' + str(r.research_visit_member.id)
            else:
                nm = r.auth_user.last_name + ", " + r.auth_user.first_name
            
            if readonly:
                chk = XML('&nbsp;')
            else:
                chk = INPUT(_type='checkbox', _name='records', _value=r.research_visit_member.id)
            
            hs = hs_no if r.auth_user.h_and_s_id is None else hs_ok
            
            row = TR(TD(LABEL(chk, XML('&nbsp;'), nm)), TD(hs))
            
            return row
        
        table_rows = [pack_visit(r, readonly) for r in rows]
        
        if readonly:
            headings =TR(TH(XML('&nbsp;') * 2, 'Visit members'), TH('H&S completed'))
        else:
            headings =TR(TH(LABEL(INPUT(_type='checkbox', _id='checkAll'), XML('&nbsp;'),
                            'Select all')), TH('H&S completed'))
        
        visitors = TABLE(headings, *table_rows, _class='table table-striped') 
        
        # A2) Instructions for use
        add_icons = CAT(SPAN(_class="glyphicon glyphicon-user"), XML('&nbsp;'), 
                        SPAN(_class="glyphicon glyphicon-plus-sign"))

        proj_icons = CAT(SPAN(_class="glyphicon glyphicon-user"), 
                                 SPAN(_class="glyphicon glyphicon-user"), 
                                 SPAN(_class="glyphicon glyphicon-user"), XML('&nbsp;'), 
                                 SPAN(_class="glyphicon glyphicon-plus-sign"))
        
        replace_icons = CAT(SPAN(_class="glyphicon glyphicon-user"), XML('&nbsp;'), 
                           SPAN(_class="glyphicon glyphicon-refresh"))
        
        delete_icons = CAT(SPAN(_class="glyphicon glyphicon-user"), XML('&nbsp;'), 
                           SPAN(_class="glyphicon glyphicon-remove-sign"))
        
        visitors_instructions = P('This panel allows you to select which visitors to book in for accomodation or for transfers.'
                                  ' You can also update who will be part of the research visit team, using the dropdown list and'
                                  ' the following actions') + \
                                  UL(LI(add_icons, ': add the selected visitor from the dropdown list.'), 
                                     LI(proj_icons, ': add all the members of a project.'),
                                     LI(replace_icons, ': replace the checked visitor with the visitor selected in the '
                                                       'dropdown. Any accomodation and transfer bookings will be transferred.'),
                                     LI(delete_icons, ': remove the checked visitor from the research visits. Any accomodation'
                                                      ' and transfer bookings for that visitor ', B('will be cancelled.')))
        
        # A3) Controls
        # get a set of valid users to use in a dropdown
        # - look see visits can add anyone, but projects can only add project members
        # - both can add 'Unknown' users to be updated later. Users are linked to bookings
        #   by the research visit member id field, so can be replaced across the bookings
        if record.look_see_visit:
            users = db(db.auth_user.id > 0).select()
        else:
            # restrict members that can be added to existing project members
            # who aren't already members of this visit
            valid_ids = db(db.project_members.project_id == record.project_id)._select(db.project_members.user_id)
            already_selected = db(db.research_visit_member.research_visit_id == record.id)._select(db.research_visit_member.user_id)
            query = db(db.auth_user.id.belongs(valid_ids) & ~ db.auth_user.id.belongs(already_selected))
            users = query.select(db.auth_user.ALL)
        
        options = [OPTION(u.last_name + ', ' + u.first_name, _value=u.id) for u in users]
        edit_visitor = SELECT(OPTION('Unknown', _value=0), *options, 
                              _name='user', 
                              _class="generic-widget form-control col-sm-3",
                              _style='height: 30px;width:200px;')
        
        # buttons to do a number of actions:
        add_visitor = TAG.BUTTON(add_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='add_visitor' )

        add_project = TAG.BUTTON(proj_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='add_project' )
        
        replace_visitor = TAG.BUTTON(replace_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='replace_visitor' )
        
        delete_visitor = TAG.BUTTON(delete_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='delete_visitor',
                                 _onclick='show_alert()')
        
       
        # combine into the panel
        if readonly:
            visitors = DIV(DIV(H5('Research visit members'), _class="panel-heading"),
                           visitors,
                           DIV(_class='panel-footer'),
                           _class="panel panel-primary")
        else:
            visitors = DIV(DIV(H5('Research visit members'), _class="panel-heading"),
                           DIV(visitors_instructions, _class='panel_body', _style='margin:10px 10px'),
                           visitors,
                           DIV(edit_visitor, XML('&nbsp;')*5, add_visitor, XML('&nbsp;')*5, 
                               add_project, XML('&nbsp;')*5, replace_visitor, XML('&nbsp;')*5, delete_visitor,
                               _class='panel-footer'),
                           _class="panel panel-primary")
        
        # B ) From To dates
        
        # In order to synchronize date selection between the client and database, the 
        # selected dates are stored in the session info and updated when changed by a
        # javascript function
        # - store defaults if no dates have yet been picked
        if session.safe is None:
            session.safe = Storage(dict(arrival_date= None, departure_date= None, avail= None))
        
        arr_date = INPUT(_type='date',  _name='arrival_date', # _class="date form-control",
                                  _value=session.safe.arrival_date, _onchange='date_change()',
                                  _id='arr_date', _style='height: 30px;width:150px;')
        dep_date = INPUT(_type='date', _name='departure_date', # _class="date form-control",
                                  _value=session.safe.departure_date, _onchange='date_change()',
                                  _id='dep_date', _style='height: 30px;width:150px;')
        
        if readonly:
            dates = DIV()
        else:
            dates = DIV(DIV(H5('Set dates for booking accomodation and transfers '), _class="panel-heading"),
                           DIV(P('Select which dates you wish to book accomodation or transfers for.'), 
                               _class='panel_body',_style='margin:10px 10px'),
                           DIV(DIV(LABEL('From / Transfer on:', _class="control-label col-sm-3" ),
                                           DIV(arr_date, _class="col-sm-3"),
                                           LABEL('To:', _class="control-label col-sm-3" ),
                                           DIV(dep_date, _class="col-sm-3"),
                                   _class='row'),
                               _class='panel-body'),
                           _class="panel panel-primary")
        
        
        # C) SAFE Panel
        add_bed_icons = CAT(SPAN(_class="glyphicon glyphicon-bed"), XML('&nbsp;'), 
                            SPAN(_class="glyphicon glyphicon-plus-sign"))
        
        release_bed_icons = CAT(SPAN(_class="glyphicon glyphicon-bed"), XML('&nbsp;'),
                                SPAN(_class="glyphicon glyphicon-refresh"))
        
        cancel_bed_icons = CAT(SPAN(_class="glyphicon glyphicon-bed"),  XML('&nbsp;'),
                               SPAN(_class="glyphicon glyphicon-remove"))
        
        if session.safe.avail is None:
            avail = P('Note that accomodation at SAFE for visitors is limited to ', n_beds_available, 
                      ' bed spaces. Select dates above to check current availability.')
        else:
            avail = P('Note that accomodation at SAFE for visitors is limited to ', n_beds_available, 
                      ' bed spaces. ', B(session.safe.avail, ' beds are available', _style='color:green;'),
                      ' for the currently selected dates.')
        
        safe_instructions = P('This panel allows you to book accomodation at SAFE. The first two options allow '
                               'you to add and release bed bookings for selected visitors and for selected dates. '
                               'Overlapping bookings for a visitor will be automatically merged and releasing beds '
                               'in the middle of a booking will automatically split the existing booking.') + \
                            UL(LI(add_bed_icons, ': Select dates and visitors to add to existing bookings.'),
                               LI(release_bed_icons, ': Select dates and visitors to release existing bookings.'),
                               LI(cancel_bed_icons, ': Select booking rows to delete.')) + avail
                            
                             
        ## SAFE visits table
        safe_select = db((db.bed_reservations.research_visit_id == rv_id) & 
                         (db.bed_reservations.site == 'safe')).select()
        
        def pack_accom(r, readonly, chx_name):
            
            if r.user_id is None:
                nm = 'Unknown #' + str(r.research_visit_member_id)
            else:
                nm = r.user_id.last_name + ", " + r.user_id.first_name
            
            if readonly:
                chk = XML('&nbsp;')
            else:
                chk = INPUT(_type='checkbox', _name=chx_name, _value=r.id)
            
            row = TR(TD(LABEL(chk, XML('&nbsp;'), nm)), 
                     TD(r.arrival_date), 
                     TD(r.departure_date), 
                     TD(approval_icons[r.admin_status]))
            
            return row
        
        
        safe_hdr = TR(TH('Visitor'), TH('Arrival date'), TH('Departure date'), TH())
        
        safe_table = TABLE(safe_hdr, 
                           *[pack_accom(r, readonly, 'safe_chx') for r in safe_select],
                           _class='table table-striped')
        
        # SAFE CONTROLS
        # buttons to do a number of actions:
        add_bed_safe_button = TAG.BUTTON(add_bed_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='add_beds_safe' )
        release_bed_safe_button = TAG.BUTTON(release_bed_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='release_beds_safe' )
        cancel_bed_safe_button = TAG.BUTTON(cancel_bed_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='cancel_beds_safe' )
        
        if readonly:
            safe = DIV(DIV(H5('Accomodation bookings at SAFE'),_class="panel-heading"),
                           safe_table,
                           DIV(_class='panel-footer'),
                           _class="panel panel-primary")
        else:
            safe = DIV(DIV(H5('Accomodation bookings at SAFE'),_class="panel-heading"),
                           DIV(safe_instructions, _class='panel_body', _style='margin:10px 10px'),
                           safe_table,
                           DIV(DIV(add_bed_safe_button, XML('&nbsp;')*5, 
                                   release_bed_safe_button, XML('&nbsp;')*5, 
                                   cancel_bed_safe_button,
                                   _class='row', _style='margin:0px 10px'),
                               _class='panel-footer'),
                           _class="panel panel-primary")
        
        # D) MALIAU Panel
        maliau_instructions = P('See instruction above for booking accomodation at SAFE.')
        
        ## MALIAU visits table
        maliau_select = db((db.bed_reservations.research_visit_id == rv_id) & 
                           (db.bed_reservations.site == 'maliau')).select()
        
        maliau_table = TABLE(safe_hdr,
                             *[pack_accom(r, readonly, 'maliau_chx') for r in maliau_select],
                             _class='table table-striped')
        
        # MALIAU CONTROLS
        # buttons to do a number of actions:
        add_bed_maliau_button = TAG.BUTTON(add_bed_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='add_beds_maliau' )
        release_bed_maliau_button = TAG.BUTTON(release_bed_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='release_beds_maliau' )
        cancel_bed_maliau_button = TAG.BUTTON(cancel_bed_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='cancel_beds_maliau' )
        if readonly:
            maliau = DIV(DIV(H5('Accomodation bookings at Maliau'),_class="panel-heading"),
                           maliau_table, DIV(_class='panel-footer'),
                           _class="panel panel-primary")
        else:
            maliau = DIV(DIV(H5('Book accomodation at Maliau'),_class="panel-heading"),
                           DIV(maliau_instructions, _class='panel_body', _style='margin:10px 10px'),
                           maliau_table,
                           DIV(DIV(add_bed_maliau_button, XML('&nbsp;')*5, 
                                   release_bed_maliau_button, XML('&nbsp;')*5, 
                                   cancel_bed_maliau_button,
                                   _class='row', _style='margin:0px 10px'),
                               _class='panel-footer'),
                           _class="panel panel-primary")
        
        # E) Transfer Panel
        
        transfer_book_icons = CAT(SPAN(_class="glyphicon glyphicon-road"), XML('&nbsp;'), 
                             SPAN(_class="glyphicon glyphicon-plus-sign"))
        
        transfer_cancel_icons = CAT(SPAN(_class="glyphicon glyphicon-road"), XML('&nbsp;'), 
                             SPAN(_class="glyphicon glyphicon-remove-sign"))
        
        transfer_instructions = P('Select a date above (use the From option) and the visitors you want to book a transfer for, '
                                  'then select which transfer you want to book. You will need to discuss the '
                                  'timing of the transfer separately with staff.')
        
        ## transfers table
        transfer_select = db(db.transfers.research_visit_id == rv_id).select()
        
        def pack_transfer(r, readonly):
            
            if r.user_id is None:
                nm = 'Unknown #' + str(r.research_visit_member_id)
            else:
                nm = r.user_id.last_name + ", " + r.user_id.first_name
            
            if readonly:
                chk = XML('&nbsp;')
            else:
                chk = INPUT(_type='checkbox', _name='transfer_chx', _value=r.id)
            
            row = TR(TD(LABEL(chk, XML('&nbsp;'), nm)), 
                     TD(r.transfer), 
                     TD(r.transfer_date), 
                     TD(approval_icons[r.admin_status]))
            
            return row
        
        transfer_hdr = TR(TH('Visitor'), TH('Transfer'), TH('Transfer date'), TH())
        transfer_table = TABLE(transfer_hdr,
                               *[pack_transfer(r, readonly) for r in transfer_select],
                               _class='table table-striped')
        
        # TRANSFER CONTROLS
        # - simple dropdown
        which_transfer = SELECT(transfer_set,
                                _name='transfer', 
                                _class="generic-widget form-control col-sm-3",
                                _style='height: 30px;width:200px;')
        
        book_transfer = TAG.BUTTON(transfer_book_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='book_transfer' )
        
        cancel_transfer = TAG.BUTTON(transfer_cancel_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='cancel_transfer' )
        
        if readonly:
            transfers = DIV(DIV(H5('Site transfer bookings'),_class="panel-heading"),
                           transfer_table,
                           DIV(_class='panel-footer'),
                           _class="panel panel-primary")
            
        else:
            transfers = DIV(DIV(H5('Site transfer bookings'),_class="panel-heading"),
                           DIV(transfer_instructions, _class='panel_body', _style='margin:10px 10px'),
                           transfer_table,
                           DIV(DIV(which_transfer, XML('&nbsp;')*5, 
                                   book_transfer, XML('&nbsp;')*5, 
                                   cancel_transfer,
                                   _class='row', _style='margin:0px 10px'),
                               _class='panel-footer'),
                           _class="panel panel-primary")
        
        # F) RA booking
        
        res_assist_book_icons = CAT(SPAN(_class="glyphicon glyphicon-leaf"), XML('&nbsp;'), 
                             SPAN(_class="glyphicon glyphicon-plus-sign"))
        
        res_assist_cancel_icons = CAT(SPAN(_class="glyphicon glyphicon-leaf"), XML('&nbsp;'), 
                             SPAN(_class="glyphicon glyphicon-remove-sign"))
        
        res_assist_instructions = P('Select a start date and finish date above and then use the options '
                                   'below to provide details of the research assistant help needed. Your booking '
                                   'will include work on the finish date so, for a single day booking, set '
                                   'the finish date to be the same as the start date.')
        
        ## res_assists table
        res_assist_select = db(db.research_assistant_bookings.research_visit_id == rv_id).select()
        
        def pack_ra(r, readonly):
            
            if readonly:
                chk = XML('&nbsp;')
            else:
                chk = INPUT(_type='checkbox', _name='ra_chx', _value=r.id)
            
            row = TR(TD(LABEL(chk, XML('&nbsp;'), r.site_time)), 
                     TD(r.start_date),
                     TD(r.finish_date),
                     TD(hs_ok if r.ropework else hs_no),
                     TD(hs_ok if r.nightwork else hs_no))
            
            return row
        
        if len(res_assist_select) == 0:
            res_assist_table = DIV('No research assistant bookings', 
                                  _class='panel panel_body', _style='margin:0px 10px')
        else:
            res_assist_hdr = TR(TH('Details'), TH('Start date'), TH('Finish date'), 
                               TH('Rope access'), TH('Night work'))
            res_assist_table = TABLE(res_assist_hdr,
                                   *[pack_ra(r, readonly) for r in res_assist_select],
                                   _class='table table-striped')

        # res_assist CONTROLS
        # - simple dropdown for time frame
        ra_details = SELECT('All day at SAFE', 'Morning only at SAFE', 'Afternoon only at SAFE',
                            'All day at Maliau', 'Morning only at Maliau', 'Afternoon only at Maliau',
                            _name='ra_site_time', 
                            _class="generic-widget form-control col-sm-3",
                            _style='height: 30px;width:200px;')
        ra_night = LABEL(INPUT(_type='checkbox', _name='ra_night'), 'Night work needed')
        ra_rope  = LABEL(INPUT(_type='checkbox', _name='ra_rope'), 'Rope access needed')
        
        book_res_assist = TAG.BUTTON(res_assist_book_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='book_res_assist' )
        
        cancel_res_assist = TAG.BUTTON(res_assist_cancel_icons,
                                 _style='padding: 5px 15px',
                                 _type='submit', _name='cancel_res_assist' )
        
        if readonly:
            res_assists = DIV(DIV(H5('Research assistant bookings'),_class="panel-heading"),
                             res_assist_table,
                             DIV(_class='panel-footer'),
                             _class="panel panel-primary")
        else:
            res_assists = DIV(DIV(H5('Research assistant bookings'),_class="panel-heading"),
                           DIV(res_assist_instructions, _class='panel_body', _style='margin:10px 10px'),
                           res_assist_table,
                           DIV(DIV(ra_details, XML('&nbsp;')*5, 
                                   ra_rope, XML('&nbsp;')*5, 
                                   ra_night, XML('&nbsp;')*5, 
                                   book_res_assist, XML('&nbsp;')*5, 
                                   cancel_res_assist,
                                   _class='row', _style='margin:0px 10px'),
                               _class='panel-footer'),
                           _class="panel panel-primary")

        
        # combine the panels into a single form
        console = FORM(visitors + dates + safe + maliau + transfers + res_assists,
                       _id='console')
        
        # console validation
        if console.process(onvalidation = validate_research_visit_details_console).accepted:
            
            # The action gets sorted out by the validator and stored in the form
            
            # --------------------------------
            # FOUR ACTIONS THAT AMEND THE VISITORS
            # --------------------------------
            
            if console.action == 'add_visitor':
                
                if console.vars.user == '0':
                     new_visitor = None
                else:
                    new_visitor = int(console.vars.user)
                db.research_visit_member.insert(research_visit_id = rv_id,
                                                user_id = new_visitor)
            
            elif console.action == 'add_project':
                
                # get the project members and current visit members
                proj_members = db(db.project_members.id == console.vars.records[0]).update(user_id = new_visitor)
                
                # update any reservations
                db(db.bed_reservations.research_visit_member_id == console.vars.records[0]).update(user_id = new_visitor)
            
            elif console.action == 'delete_visitor':
                # the DB cascade removes any downstream reservations
                # so all we need to do is drop the visit record
                db(db.research_visit_member.id == console.vars.records[0]).delete()
                
                # that can release rooms and affect availability
                __check_availability()
            
            elif console.action == 'replace_visitor':
                
                if console.vars.user == '0':
                     new_visitor = None
                else:
                    new_visitor = int(console.vars.user)
                
                db(db.research_visit_member.id == console.vars.records[0]).update(user_id = new_visitor)
                
                # update any reservations
                db(db.bed_reservations.research_visit_member_id == console.vars.records[0]).update(user_id = new_visitor)
            
            # --------------------------------
            # SIX ACTIONS THAT BOOK ACCOMODATION
            # --------------------------------
            
            elif console.action == 'add_beds_safe':
                
                __book_release_beds(records = console.vars.records,
                                    site = 'safe',
                                    mode = 'book')
                __check_availability()
                
            elif console.action == 'release_beds_safe':
                
                __book_release_beds(records = console.vars.records,
                                    site = 'safe',
                                    mode = 'release')
                __check_availability()
            
            elif console.action == 'cancel_beds_safe':
                
                for r in console.vars.safe_chx:
                    db(db.bed_reservations.id == r).delete()
                
                __check_availability()
            
            elif console.action == 'add_beds_maliau':
                
                __book_release_beds(records = console.vars.records,
                                    site = 'maliau',
                                    mode = 'book')
                
            elif console.action == 'release_beds_maliau':
                
                __book_release_beds(records = console.vars.records,
                                    site = 'maliau',
                                    mode = 'release')
            
            elif console.action == 'cancel_beds_maliau':
                
                for r in console.vars.maliau_chx:
                    db(db.bed_reservations.id == r).delete()
            
            # --------------------------------
            # TWO ACTIONS THAT BOOK TRANSFERS
            # --------------------------------
            
            elif console.action == 'book_transfer':
                
                for r in console.vars.records:
                    db.transfers.insert(transfer = console.vars.transfer,
                                        research_visit_id = rv_id,
                                        research_visit_member_id = r,
                                        transfer_date = console.vars.arrival_date)
            
            elif console.action == 'cancel_transfer':
                
                for r in console.vars.transfer_chx:
                    db(db.transfers.id == r).delete()
            
            # --------------------------------
            # TWO ACTIONS THAT BOOK RAs
            # --------------------------------
            
            elif console.action == 'book_res_assist':
                
                print console.vars.ra_rope
                print console.vars.ra_night
                
                print console.vars.ra_rope is not None
                print console.vars.ra_rope == 'on'
                print ((console.vars.ra_rope is not None) and (console.vars.ra_rope == 'on'))
                
                ropework = ((console.vars.ra_rope is not None) and (console.vars.ra_rope == 'on'))
                nightwork = ((console.vars.ra_night is not None) and (console.vars.ra_night == 'on'))
                
                db.research_assistant_bookings.insert(research_visit_id = rv_id,
                                    start_date = console.vars.arrival_date,
                                    finish_date = console.vars.departure_date,
                                    site_time = console.vars.ra_site_time,
                                    ropework = ropework,
                                    nightwork = nightwork)
            
            elif console.action == 'cancel_res_assist':
                
                for r in console.vars.ra_chx:
                    db(db.research_assistant_bookings.id == r).delete()
                    
            # reload the page to update changes
            redirect(URL('test2', args=rv_id))
        
        elif console.errors:
        
            session.flash = console.errors
            
    else:
        
        console = None
     
    return dict(visit_record = record, visit=visit, console=console)


def __check_availability():
    
    """
    Updates the availability information stored in session
    - called from check availability and post booking SAFE
    """
    
    if ((session.safe.arrival_date is not None) &
       (session.safe.arrival_date is not None)):
          # check how many reservations overlap the whole period
          existing_res = db((db.bed_reservations.departure_date > session.safe.arrival_date) &
                            (db.bed_reservations.arrival_date < session.safe.departure_date))
      
          # store the availability
          session.safe.avail = n_beds_available - existing_res.count()

def validate_research_visit_details(form):
    
    # populate the proposer_id if this is a new entry (form has no record)
    if form.record is None:
        form.vars.proposer_id = auth.user.id
        form.vars.proposal_date = datetime.datetime.utcnow().isoformat()
        form.vars.admin_history =  '[{} {}, {}] {}\\n'.format(auth.user.first_name,
                    auth.user.last_name, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                    'Research visit proposal created.')
    
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


def __book_release_beds(records, site, mode):
    
    
    # book a bed for each checked record
    for rid in records:
        
        # get the user id from this row in the research_visit_member table
        rid = int(rid)
        row = db.research_visit_member(rid)
        
        # look for existing bookings at this site that intersect this one
        existing = db((db.bed_reservations.research_visit_member_id == rid) &
                      (db.bed_reservations.departure_date >= session.safe.arrival_date) &
                      (db.bed_reservations.arrival_date <= session.safe.departure_date) &
                      (db.bed_reservations.site == site))
        
        if mode == 'book':
            
            if existing.count() == 0:
                # if nothing overlapping already exists, create a new entry
                db.bed_reservations.insert(site = site,
                                           research_visit_id = row.research_visit_id,
                                           research_visit_member_id = rid,
                                           arrival_date = session.safe.arrival_date,
                                           departure_date = session.safe.departure_date,
                                           user_id = row.user_id)
            else:
                # otherwise find everthing that overlaps and get the date ranges
                existing = existing.select()
                arr_dates = [r.arrival_date for r in existing]
                arr_dates.append(datetime.datetime.strptime(session.safe.arrival_date, '%Y-%m-%d').date())
                dep_dates = [r.departure_date for r in existing]
                dep_dates.append(datetime.datetime.strptime(session.safe.departure_date, '%Y-%m-%d').date())
            
                # delete the existing overlapping records
                for e in existing:
                    db(db.bed_reservations.id == e.id).delete()
                
                # add the new spanning record
                db.bed_reservations.insert(site = site,
                                           research_visit_id = row.research_visit_id,
                                           research_visit_member_id = rid,
                                           arrival_date = min(arr_dates),
                                           departure_date = max(dep_dates),
                                           user_id = row.user_id)
        elif mode == 'release':
            
            if existing.count() > 0:
                # can only remove if there are bookings that overlap
                # TODO - add flash if there are no actions?
                existing = existing.select()
                for e in existing:
                    
                    arr_in_ex = e.arrival_date < session.safe.arrival_datetime < e.departure_date 
                    dep_in_ex = e.arrival_date < session.safe.departure_datetime < e.departure_date 
                    spans = ((session.safe.arrival_datetime < e.arrival_date) & 
                             (e.departure_date < session.safe.departure_datetime))
                    
                    # look at each one in turn to see whether to delete/truncate
                    if (arr_in_ex and not dep_in_ex):
                             # 1) truncating the end of the visit
                             db(db.bed_reservations.id == e.id).update(departure_date = session.safe.arrival_date)
                    elif (not arr_in_ex and dep_in_ex):
                             # 2) truncating the start of the visit
                             db(db.bed_reservations.id == e.id).update(departure_date = session.safe.departure_date)
                    elif (spans):
                             # 3) visit completely covered so delete
                             db(db.bed_reservations.id == e.id).delete()
                    elif (arr_in_ex and dep_in_ex):
                             # 4) visit split by deletion period, so truncate and insert
                             db(db.bed_reservations.id == e.id).update(departure_date = session.safe.arrival_date)
                             db.bed_reservations.insert(site = site,
                                                        research_visit_id = row.research_visit_id,
                                                        research_visit_member_id = rid,
                                                        arrival_date = session.safe.departure_date,
                                                        departure_date = e.departure_date,
                                                        user_id = row.user_id)
                    else:
                        # non-overlapping
                        pass
                    


def validate_research_visit_details_console(form):
    
    # the request captures the datechange hidden field and 
    # the name of any submit button pressed
    request_keys = request.vars.keys()
    
    # list of submit buttons (and onme hidden action)
    submit_ids = set(["add_visitor", "add_project", "replace_visitor", "delete_visitor", 
                      "add_beds_safe", "release_beds_safe", "cancel_beds_safe", "add_beds_maliau",
                      "release_beds_maliau", "cancel_beds_maliau", "book_transfer", 
                      "cancel_transfer", "book_res_assist", "cancel_res_assist", 'datechange'])
    
    action = list(submit_ids.intersection(request_keys))
    
    # check for oddities and pass the action back across to the processing actions
    if(len(action) <> 1):
        form.errors = 'Error with action identification.'
    else:
        action = action[0]
        form.action = action
        
    print action
    
    # a function to sanitize the row selection indicators as they can be:
    # - missing (none selected) 
    # - a single string (one selected)
    # - a list of strings (2+ selected)
    # so convert to a consistent list and make strings into numbers
    def row_selectors(rec):
        
        if rec is None:
            rec = [] 
        elif type(rec) is str:
            rec = [int(rec)] 
        else:
            rec = [int(x) for x in rec]
        
        return(rec)
    
    form.vars.records = row_selectors(form.vars.records)
    form.vars.safe_chx = row_selectors(form.vars.safe_chx)
    form.vars.maliau_chx = row_selectors(form.vars.maliau_chx)
    form.vars.transfer_chx = row_selectors(form.vars.transfer_chx)
    form.vars.ra_chx = row_selectors(form.vars.ra_chx)
    
    print form.vars.transfer_chx
    
    # catching and checking dates
    # - onchange event for dates triggers a submit with a hidden datechange field
    #   that we can intercept
    if action == 'datechange':
        
        # store the dates as datetime objects
        arrival_datetime = datetime.datetime.strptime(form.vars.arrival_date, '%Y-%m-%d').date()
        departure_datetime = datetime.datetime.strptime(form.vars.departure_date, '%Y-%m-%d').date()
        
        # check the from date is more than a fortnight away
        deadline = datetime.date.today() + datetime.timedelta(days=14)
        if arrival_datetime < deadline:
            form.errors.arrival_date = '14 days notice required for all bookings. Must be later than {}.'.format(deadline.isoformat())
        
        # check the departure date is after the arrival date
        if arrival_datetime >= departure_datetime:
            form.errors.departure_date = 'The departure date must be later than the arrival date'
    
        # store the dates in session and update SAFE availability
        session.safe.arrival_datetime = arrival_datetime
        session.safe.departure_datetime = departure_datetime
        session.safe.arrival_date = form.vars.arrival_date
        session.safe.departure_date = form.vars.departure_date
        __check_availability()
    
    elif action == 'add_visitor':
        
        # currently no error checking required
        pass
    
    elif action == 'add_project':
        
        # check this is a project related 
        pass
        
    elif action == 'replace_visitor':
        
        if len(form.vars.records) <> 1:
            form.errors.replace_visitor = 'You must select a single visitor row to replace'
    
    elif action == 'delete_visitor':
        
        if len(form.vars.records) <> 1:
            form.errors.delete_visitor = 'You can only delete a single visitor at a time'
    
    elif action in ['add_beds_safe', 'add_beds_maliau']:
    
        if session.safe is None:
            form.errors.action = 'You must set dates before booking beds.'
    
        if len(form.vars.records) == 0:
            form.errors.action = 'You must select visitors to book for.'
    
    elif action in ['release_beds_safe', 'release_beds_maliau']:
    
        if session.safe is None:
            form.errors.action = 'You must set dates to release beds.'
    
        if len(form.vars.records) == 0:
            form.errors.action = 'You must select which visitors to release beds for.'
            
    elif action == 'cancel_beds_safe':
    
        if len(form.vars.safe_chx) == 0:
            form.errors.action = 'You must select the rows for SAFE bookings you want to cancel.'
    
    elif action == 'cancel_beds_maliau':
    
        if len(form.vars.maliau_chx) == 0:
            form.errors.action = 'You must select the rows for Maliau bookings you want to cancel.'
    
    elif action == 'book_transfer':
    
        if session.safe is None:
            form.errors.action = 'You must set dates to book transfers.'
    
        if len(form.vars.records) == 0:
            form.errors.action = 'You must select visitors to transfer'
    
    elif action == 'cancel_transfer':
    
        if len(form.vars.transfer_chx) == 0:
            form.errors.action = 'You must select the rows for the transfers you want to cancel'
    
    elif action == 'book_res_assist':
    
        if session.safe is None:
            form.errors.action = 'You must set dates to book research assistants.'
    
    elif action == 'cancel_res_assist':
    
        if len(form.vars.ra_chx) == 0:
            form.errors.action = 'You must select the rows for the research assistant bookings you want to cancel'




def export_research_visits():
    
    """
    This creates an excel workbook showing the current research visit data
    and pokes it out as an http download, so a button can call the controller
    and return the file via the browser. Formatting needs some work but Ryan
    was keen on this.
    """
    
    query = ((db.bed_reservations.admin_status == 'Approved') &
             (db.bed_reservations.departure_date > datetime.date.today().isoformat()))
    data = db(query).select(orderby=db.bed_reservations.arrival_date)
    
    if len(data) > 0:
        # open the workbook object
        wb = openpyxl.Workbook()
        # get the worksheet
        ws = wb.active
        ws.title = 'Bed reservations'
        ws['A1'] = 'Bed Reservations at SAFE as of {}'.format(datetime.date.today().isoformat())
    
        # get the arrival date of the first row (which is the earliest, due to the orderby)
        end_date = start_date = data.first().arrival_date
    
        current_row = start_row = 6
        last_col = start_col = 1
    
        fill1 = openpyxl.styles.PatternFill(patternType='solid', 
                                            fgColor=openpyxl.styles.Color('55BBBBBB'))
        fill2 = openpyxl.styles.PatternFill(patternType='solid', 
                                            fgColor=openpyxl.styles.Color('FFDDDDDD'))
    
        for i, row in enumerate(data):
            this_start_col = (row.arrival_date - start_date).days + start_col 
            this_end_col = (row.departure_date - start_date).days + start_col 
            ws.merge_cells(start_row=current_row, 
                           start_column=this_start_col,
                           end_row=current_row + row.number_of_visitors - 1 ,
                           end_column=this_end_col)
            if last_col < this_end_col:
                last_col = this_end_col
                end_date = row.departure_date
            c = ws.cell(row=current_row, column=(row.arrival_date - start_date).days + start_col)
            c.style.alignment.vertical = "top"
            c.value = row.purpose
            c.fill = fill1 if (i % 2 == 0) else fill2
            current_row  += row.number_of_visitors 
    
        # label up the dates
        dates = day_range(start_date, end_date + datetime.timedelta(days=1))
        weekday = [d.strftime('%a') for d in dates]
        month = [d.strftime('%B') for d in dates]
        day = [d.day for d in dates]
    
        for i, (d, w) in enumerate(zip(day, weekday)):
            c = ws.cell(row=start_row - 1, column=start_col + i)
            c.value = d
            c = ws.cell(row=start_row - 2, column=start_col + i)
            c.value = w
    
        current_col = start_col
        while len(month) > 0:
            m_counter = Counter(month)
            this_month = month[0]
            n_month = m_counter[this_month] 
            ws.merge_cells(start_row=start_row - 3, 
                           start_column=current_col,
                           end_row=start_row - 3,
                           end_column=current_col + n_month - 1)
            c = ws.cell(row=start_row - 3, column=current_col)
            c.value = this_month
            current_col = current_col + n_month
            month = month[n_month:]
    
        for i in range(start_col, last_col + 1):
            ws.column_dimensions[openpyxl.cell.get_column_letter(i)].width = '3'
    
        # and now poke it out to the browser
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        attachment = 'attachment;filename=SAFE_Bed_reservations_{}.xlsx'.format(datetime.date.today().isoformat())
        response.headers['Content-Disposition'] = attachment
        content = openpyxl.writer.excel.save_virtual_workbook(wb)
        raise HTTP(200, str(content),
                   **{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                      'Content-Disposition':attachment + ';'})
    else:
        session.flash = CENTER(B('No approved bed reservations found.'), _style='color: red')
        redirect(URL('bed_reservations','manage_bed_reservations'))


def bed_availability():

    """
    This controller:
        - creates data for a free beds view using fullcalendar javascript
        - combining this and the booking on a single page causes issues
    """

    # get the dates when beds are booked
    # and select as an iterable of rows
    bed_data = db(db.bed_data)
    rows = bed_data.select()
    
    # Pass a list of events to the view for the javascript calendar
    # - need to handle null values from db
    pend = [0 if r.pending is None else r.pending for r in rows]
    conf = [0 if r.approved is None else r.approved for r in rows]
    avail = [n_beds_available - (x+y) for x, y in zip(pend, conf)]
    # handle admin approved overbooking by trunctating
    avail = [0 if x < 0 else x for x in avail]
    date = [r.day.isoformat() for r in rows]
    
    # now zip into sets of events, with three per day
    # one for each of pending confirmed and available
    n_events = len(date)
    event_n_beds =pend + conf + avail
    event_class  = ['pending'] * n_events + ['confirmed'] * n_events + ['available'] * n_events
    event_title  = [ str(x) + ' ' + y for x,y in zip(event_n_beds, event_class)]
    event_order  = [2] * n_events + [3] * n_events + [1] * n_events
    # pass colour information
    event_backgrounds = ['#CC9900'] * n_events + ['#CC0000'] * n_events + ['#228B22'] * n_events
    
    events = zip(event_title, date * 3, event_class, event_order, event_backgrounds)
    
    return dict(events=events)


