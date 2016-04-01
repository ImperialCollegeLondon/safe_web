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

    form = SQLFORM.grid(query = db.auth_user, csv=False,
                        fields=[db.auth_user.last_name,
                                db.auth_user.first_name, 
                                db.auth_user.email,
                               ], 
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=True,
                        formargs={'showid': False}, 
                    )
    
    return dict(form=form)


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
