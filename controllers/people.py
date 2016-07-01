import datetime

## -----------------------------------------------------------------------------
## INTERFACES TO VIEW AND MANAGE USERS AND PROJECT CONTACTS
## -- note more complex interfaces through appadmin
## -- also provides a mechanism to validate new users
## -----------------------------------------------------------------------------

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
                                db.auth_user.institution,
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
    Custom user view - displays the user details, but only give some details
    to non-logged in visitors
    """
    
    # retrieve the record id from the page arguments passed by the button
    record_id = request.args(0)
    
    # control access to records based on status
    record = db.auth_user(record_id)
    
    
    if record_id is None or record is None:
        
        # avoid unknown outputs
        session.flash = B(CENTER('Invalid user id'), _style='color:red;')
        redirect(URL('people','users'))
    
    else:
    
        groups = record.auth_membership.select()
        if len(groups) > 0:
    
            group_names = [g.group_id.role for g in groups]
            group_names = ", ".join(set(group_names))
            groups = DIV(LABEL('Web groups:', _class="control-label col-sm-2" ),
                                DIV(group_names, _class="col-sm-10"),
                                _class='row', _style='margin:10px 10px')
        else:
            groups = DIV()
        
    
        # avoid incomplete fields and restrict what can be seen by anonymous visitors
        if auth.is_logged_in():
            flds = ['nationality', 'academic_status','supervisor_id',  'institution', 'institution_address',
                    'institution_phone', 'phone', 'mobile_phone', 'email', 'alternative_email', 
                    'website', 'orcid', 'biography', 'scientific_expertise']
            footer = DIV("Download contact details ", A('here', _href=URL('vcard', args=record_id)), _class="panel-footer")
        else:
            flds = ['nationality', 'academic_status','supervisor_id', 'institution', 'institution_address',
                    'biography', 'scientific_expertise']
            footer = ''
            
        fld_names  = {'nationality':'Nationality', 'academic_status':'Academic Status','supervisor_id':'Supervisor',
                'institution':'Academic institution', 'institution_address':'Institutional Address',
                'institution_phone':'Institutional Phone','phone':'Phone number', 'mobile_phone': 'Mobile phone', 
                'email':'Email', 'alternative_email':'Alternative Email', 'orcid':'ORCiD',
                'website': 'Website', 'scientific_expertise':'Areas of Expertise'}
        
        content = []
        
        for f in flds:
            
            if record[f] not in [None, ""]:
                
                if f in ['email', 'alternative_email']:
                    row_content = A(record[f], _href='mailto:'+record[f])
                elif f == 'supervisor_id':
                    supe = db.auth_user(record[f])
                    row_content = A(supe.first_name + " " + supe.last_name, _href = URL('people', 'user_details', args=record[f]))
                else:
                    row_content = record[f]
                
                content.append(DIV(LABEL(fld_names[f], _class="control-label col-sm-4"),
                                   DIV(row_content, _class="col-sm-8"),
                                   _class='row', _style='margin:10px 10px'))
        
        # put the user thumbnail on the left
        if record.thumbnail_picture is None:
            img = URL('static', 'images/default_thumbnails/missing_person.png')
        else:
            img = URL('default', 'download', args = record.thumbnail_picture)
        
        # look up contact roles
        if record.contacts.count() > 0:
            
            contact_info = record.contacts.select()
            for r in contact_info:
                content.append(DIV(LABEL('Role', _class="control-label col-sm-4"),
                                       DIV(r.contacts_role + ' (' + r.contacts_group + ')', _class="col-sm-8"),
                                       _class='row', _style='margin:10px 10px'))
        
        # package content
        content = DIV(DIV(IMG(_src=img, _height=100), _class='col-sm-2'), DIV(*content,_class='col-sm-10'), _class='panel-body')
        
        usr = DIV(DIV(H5(" ".join(('' if record.title is None else record.title, record.first_name, record.last_name))), 
                  _class="panel-heading"),
                  content,
                  footer,
                  _class="panel panel-primary")
        
        # pass components to the view
        return dict(usr=usr)

@auth.requires_login()
def vcard():
    
    """
    Download a vcard of a users details
    """
    
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
    
    
    # don't let the admin touch passwords and expose the contact group/role
    db.auth_user.password.readable = False
    db.auth_user.password.writable = False
    
    form = SQLFORM.grid(query = db.auth_user, csv=True,
                        fields=[db.auth_user.last_name,
                                db.auth_user.first_name, 
                                db.auth_user.email,
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
    Approves a new user from the approve new members form
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
## -----------------------------------------------------------------------------

def contacts():
    
    # what groups can be selected
    groups = ["Management Team", "Science Advisory Committee", "Malaysian Collaborators", "Field Team"]
    ids = {"Management Team":'manage', "Science Advisory Committee":'sac', "Malaysian Collaborators":'local', "Field Team":'field'}
    
    # using the 'group' argument to switch between different sets of contacts
    # default to management but switch using some URLs on the view
    if request.vars.group is None or request.vars.group not in groups:
        requested_group = 'manage'
    else:
        requested_group = ids[request.vars.group]
    
    # Loop over the options, populating tables for each grid of results
    grids = {}
    for k in groups:
        
        # select the rows
        rows = db((db.auth_user.id == db.contacts.user_id) &
                  (db.contacts.contacts_group == k)).select()
        
        # build a table row containing the display name with a URL link
        rows = [TR( TD(IMG(_src = URL('static', 'images/default_thumbnails/missing_person.png')
                                  if r.auth_user.thumbnail_picture is None else
                                  URL('default', 'download', args = r.auth_user.thumbnail_picture,),
                            _height='100px')),
                    TD(A(" ".join(['' if r.auth_user.title is None else r.auth_user.title, r.auth_user.first_name, r.auth_user.last_name]),
                        _href= URL('people', 'user_details', args=[r.auth_user.id]))),
                      TD(r.contacts.contacts_role))
                   for r in rows]
            
        # package into a table
        grids[k] = TABLE(*rows, _class='table table-striped', _style='width:100%')
    
    # build the HTML programatically - have to include some args indirectly because
    # they contain hyphens
    ul_tags = {'_class':"nav nav-tabs nav-justified", '_data-tabs':"tabs"}
    a_tags = {'_data-toggle':"tab"}
    
    # need a UL defining the tabs and a DIV containing tab contents as tab pane DIVs .
    tabs = UL([LI(A(k, _href='#' + ids[k] , **a_tags), _role='presentation', _name=ids[k]) for k in groups], **ul_tags)
    content = DIV([DIV(grids[k], _class="tab-pane", _id=ids[k]) for k in groups], _class="tab-content")
    
    # amend the tabs and content to make one active on load
    tabs.element('li[name=' + requested_group + ']')['_class'] = 'active'
    content.element('#' + requested_group)['_class'] += ' active'
    
    return dict(grids = CAT(tabs, content))


def manage_contacts():
    
    form = SQLFORM.grid(query = db.contacts,
                        csv=False,
                        maxtextlength=250,
                        deletable=True,
                        editable=True,
                        create=True,
                        details=True,
                        formargs={'showid': False}, 
                    )
    
    return dict(form=form)
    
