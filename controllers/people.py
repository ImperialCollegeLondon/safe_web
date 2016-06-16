import datetime

## -----------------------------------------------------------------------------
## INTERFACES TO VIEW AND MANAGE USERS AND PROJECT CONTACTS
## -- note more complex interfaces through appadmin
## -- also provides a mechanism to validate new users
## -----------------------------------------------------------------------------

@auth.requires_login()
def users():
    
    """
    This controller handles:
     - presenting users with a list of current users and access to details
    """
    
    # links to custom view page
    links = [dict(header = '', 
                 body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                      SPAN('View', _class="buttontext button"),
                                      _class="button btn btn-default", 
                                      _href=URL("people","user_details", 
                                      args=[row.id], user_signature=True),
                                      _style='padding: 3px 5px 3px 5px;'))]
    
    form = SQLFORM.grid(query = db.auth_user, csv=False,
                        fields=[db.auth_user.last_name,
                                db.auth_user.first_name, 
                                db.auth_user.email,
                               ], 
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False,
                        links=links, 
                    )
    
    return dict(form=form)


def user_details():
    
    """
    Custom user view - displays the user details
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.auth_user(record_id)
    
    
    groups = record.auth_membership.select()
    if len(groups) > 0:
    
        group_names = [g.group_id.role for g in groups]
        group_names = ", ".join(set(group_names))
        groups = DIV(LABEL('Web groups:', _class="control-label col-sm-2" ),
                            DIV(group_names, _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px')
    else:
        groups = DIV()
    
    if record is not None:
        
        # optional fields
        if record.alternative_email is None or record.alternative_email == "":
            alt_email = DIV()
        else:
            alt_email = DIV(LABEL('Alternative email:', _class="control-label col-sm-2" ),
                            DIV(A(record.alternative_email, 
                                  _href="mailto:" + record.alternative_email), 
                                _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px')
        
        if record.phone is None or record.phone == "":
            phone = DIV()
        else:
            phone = DIV(LABEL('Phone:', _class="control-label col-sm-2" ),
                        DIV(record.phone, _class="col-sm-10"),
                        _class='row', _style='margin:10px 10px')
        
        if record.mobile_phone is None or record.mobile_phone == "":
            mobile_phone = DIV()
        else:
            mobile_phone = DIV(LABEL('Mobile:', _class="control-label col-sm-2" ),
                               DIV(record.mobile_phone, _class="col-sm-4"),
                               _class='row', _style='margin:10px 10px')
        
        if record.institution_phone is None or record.institution_phone == "":
            inst_phone = DIV()
        else:
            inst_phone = DIV(LABEL('Institution Phone:', _class="control-label col-sm-2" ),
                             DIV(record.institution_phone, _class="col-sm-4"),
                             _class='row', _style='margin:10px 10px')

        if record.supervisor_id is None or record.supervisor_id == "":
            supervisor = DIV()
        else:
            supervisor = DIV(LABEL('Supervisor:', _class="control-label col-sm-2" ),
                             DIV(A(" ".join((record.supervisor_id.title, 
                                           record.supervisor_id.first_name, 
                                           record.supervisor_id.last_name)),
                                   _href=URL('people', 'user_details', args=record.supervisor_id)),
                                 _class="col-sm-10"),
                             _class='row', _style='margin:10px 10px')
        
        usr = DIV(DIV(H5(" ".join(('' if record.title is None else record.title, record.first_name, record.last_name))), 
                  _class="panel-heading"),
                  # DIV(LABEL('User:', _class="control-label col-sm-2" ),
                  #     DIV(record.last_name + ", " + record.first_name, _class="col-sm-10"),
                  #     _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Academic Status:', _class="control-label col-sm-2" ),
                      DIV(record.academic_status, _class="col-sm-4"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Institution:', _class="control-label col-sm-2" ),
                      DIV(record.institution, _class="col-sm-4"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Institution Address:', _class="control-label col-sm-2" ),
                      DIV(record.institution_address, _class="col-sm-10"),
                      _class='row', _style='margin:10px 10px'),
                  DIV(LABEL('Email:', _class="control-label col-sm-2" ),
                      DIV(A(record.email, _href="mailto:" + record.email), _class="col-sm-4"),
                      _class='row', _style='margin:10px 10px'),
                  alt_email, phone, mobile_phone, inst_phone,
                  supervisor, groups, 
                  DIV("Download contact details ", A('here', _href=URL('vcard', args=record_id)),
                      _class="panel-footer"),
                  _class="panel panel-primary")
    else:
        session.flash = CENTER(B('Invalid volunteer record number.'), _style='color: red')
        redirect(URL('people', 'users'))
    
    # pass components to the view
    return dict(usr=usr)


def vcard():
    
    # is a specific visit requested?
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.auth_user(record_id)
    
    if record is not None:
        
        # and now poke a VCF object out to the browser

        # # replace None with '' in record
        # content_keys = ['last_name', 'first_name', 'title','institution','institution_address',
        #                 'email', 'alternative_email', 'phone', 'mobile_phone','institution_phone',
        #                 'academic_status']
        # rec_dict = dict([(k, record[k]) for k in content_keys])
        
        # get the components of the vCard - we don't try and map address to fields
        # and just put it in as the Label property
        n = "N:{last_name};{first_name};;{title};\n"
        org = "" if record['institution'] is None else "ORG:{institution}\n"
        p1  = "" if record['phone'] is None else "TEL;type=MAIN;type=VOICE;type=pref:{phone}\n"
        p2  = "" if record['mobile_phone'] is None else "TEL;type=CELL;type=VOICE:{mobile_phone}\n"
        p3  = "" if record['institution_phone'] is None else "TEL;type=WORK;type=VOICE:{institution_phone}\n"
        em  = "EMAIL;type=WORK;type=pref:{email}\n"
        em2 = "" if record['alternative_email'] is None else "EMAIL;type=WORK:{alternative_email}\n"
        
        if record['institution_address'] is not None:
            adr = record['institution_address']
            adr = '\\n'.join(adr.split(','))
            adr = 'ADR;LABEL="'+ adr + '":;;;;;;\n'
        else:
            adr = ''
        
        
        content = "BEGIN:VCARD\nVERSION:3.0\n" + n + org + p1 + p2 + p3 + em + em2 + adr + "END:VCARD\n"
        content =content.format(**record)
        attachment = 'attachment;filename={first_name} {last_name}.vcf'
        attachment = attachment.format(**record)
        raise HTTP(200, content,
                   **{'Content-Type':'text/vcard',
                      'Content-Disposition':attachment + ';'})





@auth.requires_membership('admin')
def manage_users():
    
    """
    This controller handles:
     - presenting admin users with a list of current users
     - allowing admin users to view and edit user details
     - but not delete as this breaks downstream references to projects
    """

    form = SQLFORM.grid(query = db.auth_user, csv=True,
                        fields=[db.auth_user.last_name,
                                db.auth_user.first_name, 
                                db.auth_user.email,
                                #db.auth_user.id.represent
                               ],
                        maxtextlength=250,
                        deletable=False,
                        editable=True,
                        create=False,
                        details=True,
                        formargs={'showid': False}, 
                    )
    
    return dict(form=form)


@auth.requires_membership('admin')
def administer_new_users():
    
    """
    This controller handles:
     - presenting admin users with a list of pending users
     - simple button mechanisms to approve or reject a new user 
    """
    
    links = [dict(header = '', body = lambda row: A('Approve',_class='button btn btn-default'
                  ,_href=URL("people","approve_new_user", args=[row.id]))),
            dict(header = '', body = lambda row: A('Reject',_class='button btn btn-default'
                  ,_href=URL("people","reject_new_user", args=[row.id]))),
            ]


    
    form = SQLFORM.grid(query = (db.auth_user.registration_key == 'pending'),
                        fields=[db.auth_user.last_name,
                                db.auth_user.first_name, 
                                db.auth_user.email,
                                #db.auth_user.id.represent
                               ],
                        csv=False,
                        links=links,
                        links_placement='left',
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=True,
                        formargs={'showid': False}, 
                    )
    
    return dict(form=form)

@auth.requires_membership('admin')
def approve_new_user():
    
    """
    Rejects a new user from the approve new members form
    """
    
    # TODO - add emailer to user?
    # retrieve the user id from the page arguments passed by the button
    user_id = request.args(0)
    
    # update the registration key for that user ID to remove 'pending'
    db(db.auth_user.id == user_id).update(registration_key='')
    
    session.flash = CENTER(B('User approved.'), _style='color: green')
    
    redirect(URL('people','administer_new_users'))
    
    return


@auth.requires_membership('admin')
def reject_new_user():
    
    """
    Rejects a new user from the approve new members form
    """
    
    
    # TODO - add emailer to user
    # TODO - add justification?
    # retrieve the user id from the page arguments passed by the button
    user_id = request.args(0)
    
    # remove that row from the auth_user database
    db(db.auth_user.id == user_id).delete()
    
    session.flash = CENTER(B('User rejected.'), _style='color: green')
    
    redirect(URL('people','administer_new_users'))
    
    return


## -----------------------------------------------------------------------------
## CONTACTS DATABASE 
## -- moved out of static content to facilitate admin updating
## -- provide an anonymously accessible view of contacts
## -- provide a management interface
## -----------------------------------------------------------------------------

def contacts():
    
    """
    Controller to show contacts and expose links to details.
    """
    
    # using the 'group' argument to switch between different sets of contacts
    # default to management but switch using some URLs on the view
    if request.vars.group is None:
        contact_type = 'Management Team'
    else:
        contact_type=request.vars.group
    
    # create a link to show the pictures
    links = [dict(header = '', body = lambda row: IMG(_src = URL('default', 'download', args = row.picture) if row.picture is not None else
                                                             URL('static', 'images/default_thumbnails/missing_person.png'),
                                                      _height = 100))]
    
    # set a default image for the picture
    db.safe_contacts.picture.default = os.path.join(request.folder, 'static', 'images/default_thumbnails/missing_person.png')
    
    
    # need picture in the fields list to allow the links to be created 
    # but don't want to actually show them in the grid
    db.safe_contacts.picture.readable=False
    
    members = SQLFORM.grid(query=(db.safe_contacts.contact_type == contact_type), csv=False, 
                        fields=[db.safe_contacts.display_name, 
                                #db.safe_contacts.contact_type, 
                                db.safe_contacts.role,
                                db.safe_contacts.picture
                                ],
                        maxtextlength=100,
                        create=False,
                        deletable=False,
                        editable=False,
                        searchable=False,
                        formargs={'showid':False},
                        links=links,
                        links_placement='left')
    
    # suppress the counter for the table
    members.element('.web2py_counter', replace=None)
    
    return dict(members=members)


@auth.requires_membership('admin')
def manage_contacts():
    
    """
    Controller to allow admin to edit contacts
    """
    
    links = [dict(header = '', body = lambda row: A(IMG(_src = URL('default', 
                  'download', args = row.picture), _height = 100)))]
    # need these three fields in the fields list to allow the links
    # to be created but don't want to actually show them in the grid
    db.safe_contacts.picture.readable=False
    
    form = SQLFORM.grid(db.safe_contacts, csv=False, 
                        fields=[db.safe_contacts.display_name, 
                                db.safe_contacts.contact_type, 
                                db.safe_contacts.role,
                                db.safe_contacts.picture
                                ],
                        maxtextlength=100,
                        create=True,
                        deletable=True,
                        editable=True,
                        details=False,
                        # searchable=False,
                        formargs={'showid':False},
                        links=links,
                        links_placement='left')
    
    return dict(form=form)
