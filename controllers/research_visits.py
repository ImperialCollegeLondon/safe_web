import datetime
from gluon.storage import Storage
import openpyxl
import itertools

## -----------------------------------------------------------------------------
## RESEARCH VISITS
## -- provide a general grid view of visits for users and routes to a detail view 
##   that allows research visits to be proposed and various bookings to be made
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
            
            button_text = 'Update'
        else:
            # otherwise is the user a coordinator for any project that could create a new record?
            # join the tables here to get at the title 
            coord_query = db((db.project_members.project_id == db.project.id) &
                             (db.project_members.is_coordinator == 'True'))
            readonly = False
            button_text = 'Create'
            
            # restrict new records to projects that the user coordinates
            # - use distinct to remove multiple coordinators
            db.research_visit.project_id.requires = IS_NULL_OR(IS_IN_DB(coord_query, 
                                                             db.project.id, 
                                                             '%(title)s',
                                                             distinct=True))
    
    # provide a form to edit/create details of visit
    visit = SQLFORM(db.research_visit, 
                    record = rv_id,
                    readonly = readonly,
                    fields = ['look_see_visit','project_id','title','arrival_date',
                              'departure_date','purpose','licence_details'],
                    labels = {'title':'Reference name for visit'},
                    submit_button = button_text,
                    showid = False)
    
    # repack the fields into a new format.
    #visit.custom.widget.arrival_date['_class'] = "col-sm-3"
    #visit.custom.widget.arrival_date['_type'] = "date"
    #visit.custom.widget.departure_date['_class'] = "col-sm-3"
    #visit.custom.widget.departure_date['_type'] = "date"
    
    # get a link for download once a record is created
    if rv_id  is None:
        download_link = DIV()
        hdr_block =DIV(LABEL('Project title:', _class="control-label col-sm-2" ),
                       DIV(visit.custom.widget.project_id, _class="col-sm-7"),
                       DIV(LABEL(visit.custom.widget.look_see_visit, 'Look See visit'), _class="col-sm-3"),
                       _class='row', _style='margin:10px 10px')
    else:
        download_link = CAT('Click on this link to download a spreadsheet of the details and estimated costs: ',
                          A('Download spreadsheet', _href=URL('research_visits', 'export_research_visits', args=rv_id)))
        if record.look_see_visit:
            proj_row = 'This is a look see visit'
        else:
            proj_row = visit.custom.widget.project_id
        
        hdr_block =DIV(LABEL('Project title:', _class="control-label col-sm-2" ),
                       DIV(proj_row, _class="col-sm-9"),
                       _class='row', _style='margin:10px 10px')
    
    
    visit = FORM(DIV(DIV(H5('Research visit details'), _class="panel-heading"),
                     DIV(visit.custom.begin,
                         hdr_block,
                         DIV(LABEL('Visit title:', _class="control-label col-sm-2" ),
                             DIV(visit.custom.widget.title,  _class="col-sm-10"),
                             _class='row', _style='margin:10px 10px'),
                         DIV(LABEL('Start date:', _class="control-label col-sm-2" ),
                             DIV(visit.custom.widget.arrival_date, _class="col-sm-3"),
                             LABEL('End date:', _class="control-label col-sm-2" ),
                             DIV(visit.custom.widget.departure_date, _class="col-sm-3"),
                               _class='row', _style='margin:10px 10px'),
                         DIV(LABEL('Purpose:', _class="control-label col-sm-2" ),
                             DIV(visit.custom.widget.purpose,  _class="col-sm-10"),
                             _class='row', _style='margin:10px 10px'),
                         DIV(DIV(visit.custom.submit,  _class="col-sm-2 col-sm-offset-2"),
                             _class='row', _style='margin:10px 10px'),
                         visit.custom.end,
                        _class='panel_body'),
                    DIV(download_link, _class='panel-footer'),
                    _class="panel panel-primary"))


    # process the visitor form if it is submitted
    if visit.process(onvalidation=validate_research_visit_details, formname='visit').accepted:
        
        session.flash = 'Research visit proposal registered'
        redirect(URL('research_visits','research_visit_details', args=visit.vars.id))
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
                hs = hs_no if r.auth_user.h_and_s_id is None else hs_ok
            else:
                chk = INPUT(_type='checkbox', _name='records', _value=r.research_visit_member.id)
                if r.auth_user.h_and_s_id is None:
                    hs = hs_no
                else: 
                    hs = CAT(hs_ok, XML('&nbsp;')*5, 
                             A('view', _href=URL('health_safety','health_and_safety', args=r.auth_user.id)))
            
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
                                TAG.DL(TAG.DT(add_icons, XML('&nbsp;')*3,'Add visitor'), 
                                       TAG.DD('Choose a user from the dropdown list and click this button. ',
                                              'You cannot add the same user twice. If you are planning a visit and some '
                                              'members are still to be recruited or are not yet registered with the site '
                                              'then select "Unknown". You will need to replace these with registered visitors ',
                                              'before coming to the field. Unknown visitors are differentiated using an ID number.',
                                              _style='padding-left: 30px;'),
                                       TAG.DT(proj_icons, XML('&nbsp;')*3,'Add project members'), 
                                       TAG.DD('Clicking on this button will update the research visit list to include all ',
                                              'current project members',
                                              _style='padding-left: 30px;'),
                                       TAG.DT(replace_icons, XML('&nbsp;')*3,'Replace visitor'), 
                                       TAG.DD('If the team for a visit changes, or you can now provide details for an unknown ',
                                               'member, then select a user from the dropdown list and click on this button ',
                                               'to replace the user and update any bookings for that user.',
                                              _style='padding-left: 30px;'),
                                       TAG.DT(replace_icons, XML('&nbsp;')*3,'Remove visitor'), 
                                       TAG.DD('Check a box next to an existing visitor and click this button to remove that '
                                              'visitor', B('and all associated bookings'), 'from the research visit',
                                              _style='padding-left: 30px;'))
        
        # A3) Controls
        # get a set of valid users to use in a dropdown
        # - look see visits can add anyone, but projects can only add project members
        # - both can add 'Unknown' users to be updated later. Users are linked to bookings
        #   by the research visit member id field, so can be replaced across the bookings
        if record.look_see_visit:
            users = db(db.auth_user.id > 0).select()
        else:
            # select the rows from auth_users for project members
            # don't remove people who are already members - might be needed for replacement
            users = db((db.project_members.project_id == record.project_id) & 
                       (db.project_members.user_id == db.auth_user.id)).select(db.auth_user.ALL)
        
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
            dates = DIV(DIV(H5('Set booking dates'), _class="panel-heading"),
                           DIV(P('Select the dates on which you wish to book accomodation, research assistant support or transfers. ',
                                 'Remember that all bookings need at least 14 days notice and must be within your research visit dates: ',
                                  record.arrival_date, ' to ', record.departure_date), 
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
            avail = ""
        else:
            avail = CAT(session.safe.avail, ' beds are available for the currently selected dates.')
        
        safe_instructions = P('This panel allows you to book accomodation at SAFE. Accomodation is limited to ',
                              n_beds_available, ' bed spaces: when dates have been selected, the availability will be ', 
                              'shown above. Food is provided as part of the booking.') + \
                            TAG.DL(TAG.DT(add_bed_icons, XML('&nbsp;')*3,'Booking beds at SAFE'), 
                                   TAG.DD('Select visitors from the '
                                          'members panel above, set dates and press the ', add_bed_icons, 
                                          'button to reserve accomodation. If your selected dates create overlapping '
                                          'reservations for the same visitor, they will be automatically merged, so nobody ends '
                                          'with two beds.', 
                                          _style='padding-left: 30px;'),
                                   TAG.DT(cancel_bed_icons, XML('&nbsp;')*3,'Cancelling bed bookings'), 
                                   TAG.DD('If you no longer need a bed booking '
                                          'then please cancel it so we can offer it to other researchers. You may '
                                          'be charged for unused bookings. Check the rows for bookings you want to'
                                          'remove below and press the ', cancel_bed_icons, ' button to cancel them.',
                                          _style='padding-left: 30px;'),
                                   TAG.DT(release_bed_icons, XML('&nbsp;')*3,'"Releasing" bed bookings'), 
                                   TAG.DD('This is a way to edit bookings. Select '
                                          'visitors above and set a date range and click the ', release_bed_icons, 
                                          ' button and all bookings for those visitors will be updated to release your bookings on those dates. '
                                          'This allows you to remove time at the start and end of existing bookings, or to split '
                                          ' them in two, without having to cancel them and start over.',
                                          _style='padding-left: 30px;'))
        
        ## SAFE visits table
        
        safe_select = db(db.bed_reservations_safe.research_visit_id == rv_id).select()
        
        def pack_safe(r, readonly):
            
            if r.user_id is None:
                nm = 'Unknown #' + str(r.research_visit_member_id)
            else:
                nm = r.user_id.last_name + ", " + r.user_id.first_name
            
            if readonly:
                chk = XML('&nbsp;')
            else:
                chk = INPUT(_type='checkbox', _name='safe_chx', _value=r.id)
            
            row = TR(TD(LABEL(chk, XML('&nbsp;'), nm)), 
                     TD(r.arrival_date), 
                     TD(r.departure_date))
            
            return row
        
        safe_hdr = TR(TH('Visitor'), TH('Arrival date'), TH('Departure date'))
        
        safe_table = TABLE(safe_hdr, 
                           *[pack_safe(r, readonly) for r in safe_select],
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
            safe = DIV(DIV(H5('Accomodation bookings at SAFE') + avail,_class="panel-heading"),
                           DIV(safe_instructions, _class='panel_body', _style='margin:10px 10px'),
                           safe_table,
                           DIV(DIV(add_bed_safe_button, XML('&nbsp;')*5, 
                                   release_bed_safe_button, XML('&nbsp;')*5, 
                                   cancel_bed_safe_button,
                                   _class='row', _style='margin:0px 10px'),
                               _class='panel-footer'),
                           _class="panel panel-primary")
        
        # D) MALIAU Panel
        maliau_instructions = P('See the instructions above in the panel for booking accomodation at SAFE. ',
                                'For Maliau, you also need to choose what kind of accomodation you want and ',
                                'which meals you want provided.') + \
                              P('We are happy to book accomodation at Maliau on your behalf but note that it ', 
                                'does take longer to confirm and approve your research visit.')
        
        ## MALIAU visits table
        maliau_select = db(db.bed_reservations_maliau.research_visit_id == rv_id).select()
        
        def pack_maliau(r, readonly):
            
            if r.user_id is None:
                nm = 'Unknown #' + str(r.research_visit_member_id)
            else:
                nm = r.user_id.last_name + ", " + r.user_id.first_name
            
            if readonly:
                chk = XML('&nbsp;')
            else:
                chk = INPUT(_type='checkbox', _name='maliau_chx', _value=r.id)
            
            
            row = TR(TD(LABEL(chk, XML('&nbsp;'), nm)), 
                     TD(r.arrival_date), 
                     TD(r.departure_date),
                     TD(r.type),
                     TD(['B' if r.breakfast else ''] + ['L' if r.lunch else ''] + ['D' if r.dinner else '']))
                     
            return row
        
        maliau_hdr = TR(TH('Visitor'), TH('Arrival date'), TH('Departure date'), TH('Type'), TH('Food'))
        
        maliau_table = TABLE(maliau_hdr,
                             *[pack_maliau(r, readonly) for r in maliau_select],
                             _class='table table-striped')
        
        # MALIAU CONTROLS
        # details
        maliau_annex = LABEL(INPUT(_type='radio', _name='maliau_type', _value='Annex', value='Annex'), 'Annex')
        maliau_hostel = LABEL(INPUT(_type='radio', _name='maliau_type', _value='Hostel', value='Annex'), 'Hostel')
        maliau_breakfast = LABEL(INPUT(_type='checkbox', _name='maliau_breakfast'), 'Breakfast')
        maliau_lunch = LABEL(INPUT(_type='checkbox', _name='maliau_lunch'), 'Lunch')
        maliau_dinner = LABEL(INPUT(_type='checkbox', _name='maliau_dinner'), 'Dinner')
        
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
                           DIV(DIV(B('Accomodation type:'),  XML('&nbsp;')*5, maliau_annex,  XML('&nbsp;')*5, 
                                                         maliau_hostel,  XML('&nbsp;')*15, 
                                   B('Food:'),  XML('&nbsp;')*5, maliau_breakfast,  XML('&nbsp;')*5, maliau_lunch, 
                                             XML('&nbsp;')*5, maliau_dinner,
                                   _class='row', _style='margin:0px 10px'),
                               DIV(add_bed_maliau_button, XML('&nbsp;')*5, 
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
                     TD(r.transfer_date))
            
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
        
        # combine the panels into a single form, along with a hidden field containing
        # the research visit id to allow the validation to cross check.
        
        
        console = FORM(visitors + dates + safe + maliau + transfers + res_assists + 
                       INPUT(_name='id', _id='id', _value=rv_id, _type='hidden'),
                       _id='console')
        
        # console validation
        if console.process(onvalidation = validate_research_visit_details_console, formname='console').accepted:
            
            # row info for history
            history_hdr = '[{} {}, {}]'.format(auth.user.first_name,
                    auth.user.last_name, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'))
            
            print console.vars
            
            # add user and project share the same code, so create a local function
            def add_user(uid):
                
                new_id = db.research_visit_member.insert(research_visit_id = rv_id,
                                                         user_id = uid)
                # update the history
                if uid is None:
                    name = 'Unknown #' + str(new_id)
                else:
                    user = db.auth_user(uid)
                    name = user.last_name + ", " + user.first_name
                    
                new_history = '{} New visitor added: {}\\n'.format(history_hdr, name)
                
                return(new_history)
            
            # --------------------------------
            # The action to take gets identified by the validator and stored in the form
            # FOUR ACTIONS THAT AMEND THE VISITORS
            # --------------------------------
            
            if console.action == 'add_visitor':
                
                record.admin_history += add_user(console.vars.user)
            
            elif console.action == 'add_project':
                
                for uid in console.vars.user:
                    record.admin_history += add_user(uid)
            
            elif console.action == 'delete_visitor':
                
                # the DB cascade removes any downstream reservations
                # so all we need to do is drop the visit record
                rvm_record = db.research_visit_member(console.vars.records[0])
                
                if rvm_record.user_id is None:
                    name = 'Unknown #' + str(rvm_record.id)
                else:
                    name = rvm_record.user_id.last_name + ", " + rvm_record.user_id.first_name
                
                # delete and recheck SAFE availability
                rvm_record.delete_record()
                __check_availability()
                
                # update the history
                record.admin_history += '{} Visitor removed: {}\\n'.format(history_hdr, name)
            
            elif console.action == 'replace_visitor':
                
                # get the current visitor and new user names
                rvm_record = db.research_visit_member(console.vars.records[0])
                if rvm_record.user_id is None:
                    old_name = 'Unknown #' + str(rv_record.id)
                else:
                    user = db.auth_user(rvm_record.user_id)
                    old_name = user.last_name + ", " + user.first_name
                
                if console.vars.user == 0:
                     console.vars.user = None
                     new_name = 'Unknown #' + str(rv_record.id)
                else:
                     user = db.auth_user(console.vars.user)
                     new_name = user.last_name + ", " + user.first_name
                
                rvm_record.update_record(user_id = console.vars.user)
                
                # TODO - could potentially merge reservation records here
                
                # update any reservations (sets of possible multiple rows.)
                db(db.bed_reservations.research_visit_member_id == console.vars.records[0]).update(user_id = console.vars.user)
                db(db.transfers.research_visit_member_id == console.vars.records[0]).update(user_id = console.vars.user)
                
                # update the history
                record.admin_history += '{} Visitor replaced: {} >> {}\\n'.format(history_hdr, old_name, new_name)
            
            # --------------------------------
            # SIX ACTIONS THAT BOOK ACCOMODATION
            # --------------------------------
            # - could merge these but then might need bed type and food required at Maliau
            
            elif console.action == 'add_beds_safe':
                
                # loop over research_visit_member_ids, creating a dict of fields to insert
                # via the __book_beds function
                for rid in console.vars.records:
                    
                    rvm_record = db.research_visit_member(rid)
                    flds = dict(departure_date = session.safe.departure_datetime,
                                arrival_date = session.safe.arrival_datetime,
                                research_visit_id = rv_id,
                                research_visit_member_id = rid,
                                user_id = rvm_record.user_id)
                                
                    __book_beds(site_table='bed_reservations_safe', flds =flds)
                    
                    if rvm_record.user_id is None:
                        name = 'Unknown #' + str(rvm_record.id)
                    else:
                        name = rvm_record.user_id.last_name + ", " + rvm_record.user_id.first_name
                    
                    record.admin_history += ('{} SAFE bed booked for {} from {} to {} \\n').format(history_hdr,
                                             name, session.safe.arrival_date, session.safe.departure_date)
                
                __check_availability()
                
            elif console.action == 'release_beds_safe':
                
                # loop over research_visit_member_ids, creating a dict of fields to insert
                # via the __book_beds function
                for rid in console.vars.records:
                    
                    rvm_record = db.research_visit_member(rid)
                    flds = dict(departure_date = session.safe.departure_datetime,
                                arrival_date = session.safe.arrival_datetime,
                                research_visit_member_id = rid)
                                
                    __release_beds(site_table='bed_reservations_safe', flds =flds)
                    
                    if rvm_record.user_id is None:
                        name = 'Unknown #' + str(rvm_record.id)
                    else:
                        name = rvm_record.user_id.last_name + ", " + rvm_record.user_id.first_name
                                
                    record.admin_history += ('{} SAFE beds released for {} between {} to {} \\n').format(history_hdr,
                                             name, session.safe.arrival_date, session.safe.departure_date)
                
                __check_availability()
            
            elif console.action == 'cancel_beds_safe':
                
                # loop over the row numbers checked on the SAFE panel, which
                # are record IDs on the bed_reservations_safe table.
                for r in console.vars.safe_chx:
                    
                    res_record = db.bed_reservations_safe(r)
                    
                    if res_record.user_id is None:
                        name = 'Unknown #' + str(res_record.research_visit_member_id)
                    else:
                        name = res_record.user_id.last_name + ", " + res_record.user_id.first_name
                    
                    record.admin_history += ('{} SAFE bed cancelled for {} between {} - {} \\n').format(history_hdr,
                                             name, res_record.arrival_date, res_record.departure_date)
                    
                    res_record.delete_record()
                
                # and update availablility
                __check_availability()
            
            elif console.action == 'add_beds_maliau':
                
                # loop over research_visit_member_ids, creating a dict of fields to insert
                # via the __book_beds function
                for rid in console.vars.records:
                    
                    rvm_record = db.research_visit_member(rid)
                    flds = dict(departure_date = session.safe.departure_datetime,
                                arrival_date = session.safe.arrival_datetime,
                                research_visit_id = rv_id,
                                research_visit_member_id = rid,
                                user_id = rvm_record.user_id,
                                type = console.vars.maliau_type,
                                breakfast = console.vars.maliau_breakfast,
                                lunch = console.vars.maliau_lunch,
                                dinner = console.vars.maliau_dinner)
                                
                    __book_beds(site_table='bed_reservations_maliau', flds =flds)
                    
                    if rvm_record.user_id is None:
                        name = 'Unknown #' + str(rvm_record.id)
                    else:
                        name = rvm_record.user_id.last_name + ", " + rvm_record.user_id.first_name
                    
                    record.admin_history += ('{} Maliau bed booked for {} from {} to {} \\n').format(history_hdr,
                                             name, session.safe.arrival_date, session.safe.departure_date)
            
            elif console.action == 'release_beds_maliau':
                
                # loop over research_visit_member_ids, creating a dict of fields to insert
                # via the __book_beds function
                for rid in console.vars.records:
                    
                    rvm_record = db.research_visit_member(rid)
                    flds = dict(departure_date = session.safe.departure_datetime,
                                arrival_date = session.safe.arrival_datetime,
                                research_visit_member_id = rid)
                                
                    __release_beds(site_table='bed_reservations_maliau', flds =flds)
                    
                    if rvm_record.user_id is None:
                        name = 'Unknown #' + str(rvm_record.id)
                    else:
                        name = rvm_record.user_id.last_name + ", " + rvm_record.user_id.first_name
                    
                    record.admin_history += ('{} Maliau beds released for {}, {} between {} to {} \\n').format(history_hdr,
                                             name, session.safe.arrival_date, session.safe.departure_date)
            
            
            elif console.action == 'cancel_beds_maliau':
                
                # loop over the row numbers checked on the SAFE panel, which
                # are record IDs on the bed_reservations_safe table.
                for r in console.vars.maliau_chx:
                    
                    res_record = db.bed_reservations_maliau(r)
                    
                    if res_record.user_id is None:
                        name = 'Unknown #' + str(res_record.research_visit_member_id)
                    else:
                        name = res_record.user_id.last_name + ", " + res_record.user_id.first_name
                    
                    record.admin_history += ('{} Maliau bed cancelled for {} between {} - {} \\n').format(history_hdr,
                                             name, res_record.arrival_date, 
                                             res_record.departure_date)
                    res_record.delete_record()
            
            # --------------------------------
            # TWO ACTIONS THAT BOOK TRANSFERS
            # --------------------------------
            
            elif console.action == 'book_transfer':
                
                # loop over selected rows from user panel and book transfers
                for r in console.vars.records:
                    
                    rvm_record = db.research_visit_member(r)
                    db.transfers.insert(transfer = console.vars.transfer,
                                        research_visit_id = rv_id,
                                        research_visit_member_id = r,
                                        user_id = rvm_record.user_id,
                                        transfer_date = console.vars.arrival_date)
                    
                    if rvm_record.user_id is None:
                        name = 'Unknown #' + str(rvm_record.id)
                    else:
                        name = rvm_record.user_id.last_name + ", " + rvm_record.user_id.first_name
                    
                    record.admin_history += ('{} Transfer booked for {} from {} on {}\\n').format(history_hdr,
                                             name, console.vars.transfer, console.vars.arrival_date)
                
            
            elif console.action == 'cancel_transfer':
                
                # loop over checked rows in the transfer panel deleting those records
                for r in console.vars.transfer_chx:
                    
                    trns_record = db.transfers(r)
                    
                    if trns_record.user_id is None:
                        name = 'Unknown #' + str(trns_record.research_visit_member_id)
                    else:
                        name = trns_record.user_id.last_name + ", " + trns_record.user_id.first_name
                    
                    trns_record.delete_record()
                    
                    record.admin_history += ('{} Transfer cancelled for {} from {} on {}\\n').format(history_hdr,
                                             name, trns_record.transfer, trns_record.transfer_date)
            
            # --------------------------------
            # TWO ACTIONS THAT BOOK RAs
            # --------------------------------
            
            elif console.action == 'book_res_assist':
                
                ropework = ((console.vars.ra_rope is not None) and (console.vars.ra_rope == 'on'))
                nightwork = ((console.vars.ra_night is not None) and (console.vars.ra_night == 'on'))
                
                db.research_assistant_bookings.insert(research_visit_id = rv_id,
                                    start_date = console.vars.arrival_date,
                                    finish_date = console.vars.departure_date,
                                    site_time = console.vars.ra_site_time,
                                    ropework = ropework,
                                    nightwork = nightwork)
                                    
                record.admin_history += ('{} RA booked {} from {} to {}\\n').format(history_hdr,
                                         console.vars.ra_site_time, console.vars.arrival_date,
                                         console.vars.departure_date)
            
            elif console.action == 'cancel_res_assist':
                
                for r in console.vars.ra_chx:
                    
                    rec = db.research_assistant_bookings(r)
                    
                    record.admin_history += ('{} RA cancelled {} from {} to {}\\n').format(history_hdr,
                                             rec.site_time, rec.start_date,rec.finish_date)
                    
                    rec.delete_record()
            
            else:
                # datechange causes a processing event that doesn't do anything
                pass
            
            # update the RV record to catch history changes
            record.update_record()
            
            # reload the page to update changes
            redirect(URL('research_visit_details', args=rv_id))
        
        elif console.errors:
            print console.errors
            pass

        # return the visit history , which optionally includes the admin console
        if record.admin_history is not None:
            history = XML(record.admin_history.replace('\\n', '<br />'), sanitize=True, permitted_tags=['br/'])
        else:
            history = ""
        
        history = DIV(DIV(H5('Research visit history'), _class="panel-heading"),
                      DIV(history, _class='panel_body', _style='margin:10px 10px;height:100px;overflow-y:scroll'),
                      DIV(_class='panel-footer'),
                      _class="panel panel-primary")
    else:
        
        console = DIV()
        history = DIV()
        
    
    # If the visit record has been created and an admin is viewing, expose the 
    # decision panel
    if rv_id is not None and auth.has_membership('admin') :
        
        admin_form = SQLFORM(db.research_visit, record=rv_id, 
                             fields = ['admin_status', 'admin_notes'],
                             showid = False)
        
        admin_panel = DIV(DIV(H5('Admin Decision'),_class="panel-heading"),
                         DIV('Provide brief notes supporting your decision:',
                             admin_form,
                             _class='panel-body', _style='margin:0px 10px'),
                         _class="panel panel-primary")
    
    else:
        admin_panel = DIV()
    
    if rv_id is not None and auth.has_membership('admin') and admin_form.process(formname='admin_form').accepted:
        
        new_history = '[{} {}, {}] ** Admin decision {}: {}\\n'.format(auth.user.first_name,
                                           auth.user.last_name, 
                                           datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                           admin_form.vars.admin_status,
                                           admin_form.vars.admin_notes)
        
        record.admin_history += new_history
        record.admin_status = admin_form.vars.admin_status
        record.update_record()
        
        # reload the page to update changes
        redirect(URL('research_visit_details', args=rv_id))
    
    
    return dict(visit_record = record, visit=visit, console=console, 
                history=history, admin_panel=admin_panel)


def validate_research_visit_details(form):
    
    """
    This controller checks the form that creates the initial RV entry
    """
    
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



def validate_research_visit_details_console(form):
    
    """
    This function checks the wide range of actions available
    from the panels for a created RV - all the panels form one
    big form that share some controls (dates and users) so
    there are multiple submit buttons that use the information
    in the console form in different ways
    """
    
    # the request captures the datechange hidden field and 
    # the name of any submit button pressed
    request_keys = request.vars.keys()
    
    # retrieve the record for the related visit
    rv = db.research_visit(form.vars.id)
    
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
    
    # catching and checking dates
    # - onchange event for dates triggers a submit with a hidden datechange field
    #   that we can intercept
    if action == 'datechange':
        
        # store the dates as datetime objects
        arrival_datetime = datetime.datetime.strptime(form.vars.arrival_date, '%Y-%m-%d').date()
        departure_datetime = datetime.datetime.strptime(form.vars.departure_date, '%Y-%m-%d').date()
        
        deadline = datetime.date.today() + datetime.timedelta(days=14)

        # check arrival date and departure date separately to allow defaults on each independently
        if arrival_datetime < deadline:
            # check the from date is more than a fortnight away
            form.errors.arrival_date = '14 days notice required for all bookings. Must be later than {}.'.format(deadline.isoformat())
        elif arrival_datetime < rv.arrival_date:
            # check we are inside the visit window.
            form.errors.arrival_date = 'This date is before the research visit arrival date ({}).'.format(rv.arrival_date.isoformat())
        else:
            # all good, so store the arrival date in session
            session.safe.arrival_datetime = arrival_datetime
            session.safe.arrival_date = form.vars.arrival_date
        
        if departure_datetime > rv.departure_date:
            form.errors.departure_date = 'This date is after the research visit departure date ({}).'.format(rv.departure_date.isoformat())
        
        elif arrival_datetime >= departure_datetime:
            # check the departure date is after the arrival date
            form.errors.departure_date = 'The departure date must be later than the arrival date'
        else:
            # all good, so store the departure date in session
            session.safe.departure_datetime = departure_datetime
            session.safe.departure_date = form.vars.departure_date
        
        if session.safe.departure_date is not None and session.safe.arrival_date is not None:
            __check_availability()
            
    elif action == 'add_visitor':
        
        # get the format correct 
        if form.vars.user == '0':
            form.vars.user = None
        else:
            form.vars.user = int(form.vars.user)
        
        # check to see they aren't already a member
        visit_members = db(db.research_visit_member.research_visit_id == form.vars.id).select(db.research_visit_member.user_id)
        m = [r.user_id for r in visit_members]
        
        # strip None from m to allow multiple unknown users
        m = [x for x in m if x is not None]
        
        if form.vars.user in m:
            form.errors.user = "User already a member of this research visit."
        
    elif action == 'add_project':
        
        # check this is a project visit (don't add everyone in the world!)
        if rv.look_see_visit:
            form.errors.user = "Cannot add project members for look see visits."
            
        # get the project members and current visit members
        project_members = db(db.project_members.project_id == rv.project_id).select(db.project_members.user_id)
        visit_members = db(db.research_visit_member.research_visit_id == rv.id).select(db.research_visit_member.user_id)
        
        p = [r.user_id for r in project_members]
        r = [r.user_id for r in visit_members]
        new = set(p).difference(r)
        
        if len(new) > 0:
            form.vars.user = new
        else:
            form.errors.user = "No new project members to add."
        
    elif action == 'replace_visitor':
        
        if len(form.vars.records) <> 1:
            form.errors.user = 'You must select a single visitor row to replace'
        
        form.vars.user = int(form.vars.user)
    
    elif action == 'delete_visitor':
        
        if len(form.vars.records) <> 1:
            form.errors.user = 'You can only delete a single visitor at a time'
    
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

## -----------------------------------------------------------------------------
## HELPER FUNCTIONS - prtotected from being called as a webpage using __name()
## -----------------------------------------------------------------------------

def __check_availability():
    
    """
    Updates the availability information stored in session
    - called from check availability and post booking SAFE
    """
    
    if ((session.safe.arrival_date is not None) &
       (session.safe.arrival_date is not None)):
          # check how many reservations overlap the whole period
          existing_res = db((db.bed_reservations_safe.departure_date > session.safe.arrival_date) &
                            (db.bed_reservations_safe.arrival_date < session.safe.departure_date))
      
          # store the availability
          session.safe.avail = n_beds_available - existing_res.count()


def __book_beds(site_table, flds):
    
    """
    Function to look for existing records in a table and book 
    - expecting to be passed a dictionary of fields to insert 
      via **args and that those will contain some key checking
      fields: research_visit_member_id, arrival_date, departure_date
    """
    
    # look for existing bookings at this site that intersect this one
    existing = db((db[site_table].research_visit_member_id == flds['research_visit_member_id']) &
                  (db[site_table].departure_date >= flds['arrival_date']) &
                  (db[site_table].arrival_date <= flds['departure_date']))
    
    if existing.count() > 0:
        
        # otherwise find the existing selections that overlap and get the date ranges
        existing = existing.select()
        
        arr_dates = [r.arrival_date for r in existing]
        dep_dates = [r.departure_date for r in existing]
        arr_dates.append(flds['arrival_date'])
        dep_dates.append(flds['departure_date'])
        flds['arrival_date'] = min(arr_dates)
        flds['departure_date'] = max(dep_dates)
        
        # delete the existing overlapping records
        for e in existing:
            e.delete_record()
        
    # add the new spanning record
    db[site_table].insert(**flds)



def __release_beds(site_table, flds):
    
    """
    Function to look for existing records in a table and book 
    - expecting to be passed a dictionary of fields to insert 
      via **args and that those will contain some key checking
      fields: research_visit_member_id, arrival_date, departure_date
    """
    
    # look for existing bookings at this site that intersect this one
    existing = db((db[site_table].research_visit_member_id == flds['research_visit_member_id']) &
                  (db[site_table].departure_date >= flds['arrival_date']) &
                  (db[site_table].arrival_date <= flds['departure_date']))
    
    if existing.count() > 0:
        
        # can only remove if there are bookings that overlap
        existing = existing.select()
        
        for e in existing:
            
            arr_in_ex = e.arrival_date < flds['arrival_date'] < e.departure_date 
            dep_in_ex = e.arrival_date < flds['departure_date'] < e.departure_date 
            spans = ((flds['arrival_date'] < e.arrival_date) & 
                     (e.departure_date < flds['departure_date']))
            
            # look at each one in turn to see whether to delete/truncate
            if (arr_in_ex and not dep_in_ex):
                     # 1) truncating the end of the visit
                     e.update_record(departure_date = session.safe.arrival_date)
            elif (not arr_in_ex and dep_in_ex):
                     # 2) truncating the start of the visit
                     e.update_record(departure_date = session.safe.departure_date)
            elif (spans):
                     # 3) visit completely covered so delete
                     e.delete_record()
            elif (arr_in_ex and dep_in_ex):
                     # 4) visit split by deletion period, so truncate and insert
                     end = e.departure_date
                     e.departure_date = flds['arrival_date']
                     db[site_table].insert(**db[site_table]._filter_fields(e)) 
                     e.arrival_date = flds['departure_date']
                     e.departure_date = end
                     db[site_table].insert(**db[site_table]._filter_fields(e)) 
                     e.delete_record()
            else:
                # non-overlapping
                pass

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
                    

def date_range(start, end):
    
    days = []
    curr = start
    while curr <= end: 
        days.append(curr)
        curr += datetime.timedelta(days=1)
    
    return(days)

def export_research_visits():
    
    """
    This creates an excel workbook compiling research visit data
    and pokes it out as an http download, so a button can call the controller
    and return the file via the browser.
    """
    
    # set up the coordinates of the data block
    curr_row = start_row = 8
    data_start_col = 4
    
    # GET THE DATA TO POPULATE EACH ACTIVITY
    # get a query for all events after today
    today =datetime.date.today()
    
    rv_query = (db.research_visit.departure_date >= today)
    safe_query = (db.bed_reservations_safe.departure_date >= today) 
    maliau_query = (db.bed_reservations_maliau.departure_date >= today)
    transfer_query = (db.transfers.transfer_date >= today)
    rassist_query = (db.research_assistant_bookings.finish_date >= today)
    
    # is a specific visit requested?
    rv_id = request.args(0)
    
    if rv_id is not None:
        record = db.research_visit(rv_id)
        if record is None:
            session.flash = CENTER(B('Export request for non existant research visit', _style='color:red'))
        else:
            rv_query = (rv_query & (db.research_visit.id == rv_id))
            safe_query = (safe_query & (db.bed_reservations_safe.research_visit_id == rv_id))
            maliau_query = (maliau_query & (db.bed_reservations_maliau.research_visit_id == rv_id))
            transfer_query = (transfer_query & (db.transfers.research_visit_id == rv_id))
            rassist_query = (rassist_query & (db.research_assistant_bookings.research_visit_id == rv_id))
    else:
        record = None
    
    # grab the data from those queries
    rv_data = db(rv_query).select(orderby=db.research_visit.arrival_date)
    safe_data = db(safe_query).select(orderby=db.bed_reservations_safe.arrival_date)
    maliau_data = db(maliau_query).select(orderby=db.bed_reservations_maliau.arrival_date)
    transfer_data = db(transfer_query).select(orderby=db.transfers.transfer_date)
    rassist_data = db(rassist_query).select(orderby=db.research_assistant_bookings.start_date)
    
    # GET A COMMON TIME SCALE FROM THE RVs (which _should_ encompass all RV activities)
    
    start_all = min([r.arrival_date for r in rv_data])
    end_all   = max([r.departure_date for r in rv_data])
    
    # use start as an epoch to give column numbers
    dates  = date_range(start_all, end_all)
    dates_column = [(x - start_all).days + data_start_col for x in dates]
    
    # get column labels and get blocks to label months
    monthyear = [d.strftime('%B %Y') for d in dates]
    monthyear_set = set(monthyear)
    monthyear_dates =  [[i for i, x in zip(dates, monthyear) if x == my] for my in monthyear_set]
    monthyear_range = [[min(x), max(x)] for x in monthyear_dates]
    weekday = [d.strftime('%a') for d in dates]
    weekday = [x[0] for x in weekday]
    day = [d.day for d in dates]
    
    # SETUP THE WORKBOOK
    wb = openpyxl.Workbook()
    
    # spreadsheet styles
    left = openpyxl.styles.Alignment(horizontal='left')
    center = openpyxl.styles.Alignment(horizontal='center')
    weekend = openpyxl.styles.PatternFill(fill_type='solid', start_color='CCCCCC')
    head = openpyxl.styles.Font(size=14, bold=True)
    subhead = openpyxl.styles.Font(bold=True)
    warn = openpyxl.styles.Font(bold=True, color='FF0000')
    cell_shade = {'Approved': openpyxl.styles.PatternFill(fill_type='solid', start_color='8CFF88'),
                  'Pending': openpyxl.styles.PatternFill(fill_type='solid', start_color='FFCB8B'),
                  'Rejected': openpyxl.styles.PatternFill(fill_type='solid', start_color='FF96C3')}
    
    # name the worksheet and add a heading
    ws = wb.active
    ws.title = 'Research visits'
    ws['A1'] = 'Research visit plans for the SAFE Project as of {}'.format(today.isoformat())
    ws['A1'].font = head
    
    print record
    # Subheading 
    if record is None:
        ws['A2'] = 'All research visits'
        ws['A2'].font = subhead
    else:
        ws['A2'] = 'Research visit #' + str(record.id) + ": " + record.project_id.title
        ws['A2'].font = subhead
    
    ws['A3'] = 'Costs are estimated and do not include site transport costs at SAFE'
    ws['A3'].font = warn
    
    # Populate the sheet with the date information
    # months in merged cells with shading on alternate months
    for start, end in monthyear_range:
        start_col = (start - start_all).days + data_start_col
        end_col = (end - start_all).days + data_start_col
        
        ws.merge_cells(start_row=5, start_column= start_col,
                       end_row=5, end_column=end_col)
        c = ws.cell(row=5, column= start_col)
        c.value = start.strftime('%B %Y')
        if (start.month % 2) == 1:
            c.fill = weekend
    
    # day of month and week day, colouring weekends and setting column width
    for i, d, w in zip(dates_column, day, weekday):
        c1 = ws.cell(row = 6, column = i)
        c1.value = d
        c1.alignment = center 
        
        c2 = ws.cell(row = 7, column = i)
        c2.value = w
        c2.alignment = center
        
        if w == 'S':
            c1.fill = weekend
            c2.fill = weekend
        
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 3
    
    # add left hand column headers
    ws['A6'] = 'ID'
    ws['B6'] = 'Type'
    ws['C6'] = 'Cost in RM'
    
    # write event function - don't use merged cells here
    # it seems tempting but text cannot overflow from merged
    # cell blocks into the adjacent blank cells, but it can from 
    # a single cell, so write content into first cell of range
    # and then just colour the rest of the date range.
    def write_event(row, start, end, id, type, content, status, cost):
        
        # range
        this_start_col = (start - start_all).days + data_start_col
        this_end_col = (end - start_all).days + data_start_col
        
        # put content at LHS of range
        print this_start_col
        c = ws.cell(row=row, column=this_start_col)
        c.value = content
        c.alignment = left # makes text overflow RHS of narrow ranges.
        
        for i in range(this_start_col, this_end_col + 1):
            c = ws.cell(row=row, column=i)
            c.fill = cell_shade[status]
        
        c = ws.cell(row=row, column=1)
        c.value = id
        c = ws.cell(row=row, column=2)
        c.value = type
        c = ws.cell(row=row, column=3)
        c.value = cost
    
    # loop over the rows in each data block
    for r in rv_data:
        
        cost = '---'
        
        dat = [curr_row, r.arrival_date, r.departure_date, r.id, 'Research Visit',
               "Project " + str(r.project_id) + ": " + r.title, r.admin_status, cost]
        
        write_event(*dat)
        curr_row += 1
    
    for r in safe_data:
        
        # check for unknown users
        if r.user_id is None:
            name = 'Unknown #' + str(r.research_visit_member_id)
        else:
            name = r.user_id.last_name + ", " + r.user_id.first_name 
        
        # lookup admin status
        admin_status = db.research_visit(r.research_visit_id).admin_status
        
        # calculate cost - food charge only
        cost = (r.departure_date - r.arrival_date).days * 25
        
        # put the list of info to be written together
        dat = [curr_row, r.arrival_date, r.departure_date, r.research_visit_id, 
               'SAFE booking', name, admin_status, cost]
        
        # write it and move down a row
        write_event(*dat)
        curr_row += 1
        
    for r in maliau_data:
        
        if r.user_id is None:
            name = 'Unknown #' + str(r.research_visit_member_id)
        else:
            name = r.user_id.last_name + ", " + r.user_id.first_name 
        
        admin_status = db.research_visit(r.research_visit_id).admin_status
        
        # calculate cost - entry, bed and food costs
        days = (r.departure_date - r.arrival_date).days
        cost = 40 + 15 # entry/admin fees
        if r.type == 'Annex':
            cost += days * 100
        else:
            cost += days * 35 # hostel is only alternative at the moment
        
        if r.breakfast is True:
            cost += 15 * days
        if r.lunch is True:
            cost += 20 * days
        if r.dinner is True:
            cost += 30 * days
        
        # content 
        food_labels = ['B' if r.breakfast else ''] + ['L' if r.lunch else ''] + ['D' if r.dinner else '']
        content = name + ' (' + r.type + ','+ ''.join(food_labels) + ')'
        dat = [curr_row, r.arrival_date, r.departure_date, r.research_visit_id,
               'Maliau booking', content, admin_status, cost]
        
        write_event(*dat)
        curr_row += 1
    
    for r in transfer_data:
        
        if r.user_id is None:
            name = 'Unknown #' + str(r.research_visit_member_id)
        else:
            name = r.user_id.last_name + ", " + r.user_id.first_name 
        
        admin_status = db.research_visit(r.research_visit_id).admin_status
        
        # costs
        if r.transfer in ['SAFE to Tawau','Tawau to SAFE']:
            cost = 250
        elif r.transfer in ['SAFE to Maliau','Maliau to SAFE']:
            cost = 350
        elif r.transfer in ['Tawau to Maliau','Maliau to Tawau']:
            cost = 400
        elif r.transfer in ['SAFE to Danum','Danum to SAFE']:
            cost = 750
            
        dat = [curr_row, r.transfer_date, r.transfer_date, r.research_visit_id, 
               'Transfer', name + ': ' + r.transfer, admin_status, cost]
        
        write_event(*dat)
        curr_row += 1
    
    for r in rassist_data:
        
        admin_status = db.research_visit(r.research_visit_id).admin_status
        
        # costs 
        if r.site_time in ['All day at SAFE', 'All day at Maliau']:
            cost = 70
        else:
            cost = 125
        
        if r.ropework:
            cost *= 1.5
        
        if r.nightwork:
            cost *= 2
        
        dat = [curr_row, r.start_date, r.finish_date, r.research_visit_id, 'RA booking',
               r.site_time, admin_status, cost]
        
        write_event(*dat)
        curr_row += 1
    
    # freeze the rows
    c = ws.cell(row=start_row, column=data_start_col)
    ws.freeze_panes = c
    # and now poke the workbook object out to the browser
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    attachment = 'attachment;filename=SAFE_Bed_reservations_{}.xlsx'.format(datetime.date.today().isoformat())
    response.headers['Content-Disposition'] = attachment
    content = openpyxl.writer.excel.save_virtual_workbook(wb)
    raise HTTP(200, str(content),
               **{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                  'Content-Disposition':attachment + ';'})


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


