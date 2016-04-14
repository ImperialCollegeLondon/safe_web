import datetime

## -----------------------------------------------------------------------------
## GROUP REQUESTS
## -- Simple system for users to apply to become members of restricted groups
## -----------------------------------------------------------------------------

@auth.requires_login()
def group_request():
    
    """
    Controller to show a SQLFORM for group requests
    """
        
    # need these three fields in the fields list to allow the links
    # to be created but don't want to actually show them in the grid
    db.group_request.user_id.readable = False 
    db.group_request.admin_id.readable = False 
    db.group_request.admin_status.readable = False 
    db.group_request.admin_decision_date.readable = False 
    
    # restrict group choice
    db.group_request.group_id.requires = IS_IN_DB(db(~ db.auth_group.role.startswith('user_')), 
                                                  db.auth_group.id, '%(role)s')
    
    form = SQLFORM(db.group_request,
                   fields=['group_id','justification'],
                   showid = False)
    
    # get a Set of rows of available groups to autocreate a table
    # omitting the autocreated user groups, which aren't used at all
    # and perhaps could be suppressed
    groups = db(~ db.auth_group.role.startswith('user_') ).select(db.auth_group.role,db.auth_group.description)
    
    if form.process(onvalidation=validate_group_request).accepted:
        # signal success and load the newly created record in a details page
        response.flash = CENTER(B('Request to join group submitted.'), _style='color: green')
    else:
        response.flash = CENTER(B('Problem with group request.'), _style='color: red')
    
    return dict(form=form, groups=groups)


def validate_group_request(form):
    
    form.vars.user_id = auth.user.id


@auth.requires_membership('admin')
def administer_group_requests():
    
    """
    This controller handles:
     - presenting admin users with a list of pending group requests
     - simple button mechanisms to approve or reject the request
    """
    
    links = [dict(header = '', body = lambda row: A('Approve',_class='button btn btn-default'
                  ,_href=URL("groups","approve_group_request", args=[row.id, row.user_id, row.group_id]))),
            dict(header = '', body = lambda row: A('Reject',_class='button btn btn-default'
                  ,_href=URL("groups","reject_group_request", args=[row.id, row.user_id, row.group_id]))),
            ]


    
    form = SQLFORM.grid(query = (db.group_request.admin_status == 'Pending'),
                        fields=[db.group_request.user_id,
                                db.group_request.group_id,
                                db.group_request.justification,
                               ],
                        csv=False,
                        links=links,
                        links_placement='right',
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False,
                        searchable=False,
                    )
    
    return dict(form=form)

@auth.requires_membership('admin')
def approve_group_request():
    
    """
    Approves a group request
    # TODO - add emailer to user?
    """
    
    # insert that pair into auth_membership
    db.auth_membership.insert(user_id = request.args(1),
                              group_id = request.args(2))
    
    # update the group_request table
    db(db.group_request.id == request.args(0)).update(admin_status='Approved',
                                                      admin_id = auth.user.id,
                                                      admin_decision_date =  datetime.date.today().isoformat())
    
    session.flash = CENTER(B('Request approved.'), _style='color: green')
    redirect(URL('groups','administer_group_requests'))
    
    return


@auth.requires_membership('admin')
def reject_group_request():
    
    """
    Approves a group request
    # TODO - add emailer to user?
    """
    
    # update the group_request table
    db(db.group_request.id == request.args(0)).update(admin_status='Rejected',
                                                      admin_id = auth.user.id,
                                                      admin_decision_date =  datetime.date.today().isoformat())
    
    session.flash = CENTER(B('Request rejected.'), _style='color: red')
    
    redirect(URL('groups','administer_group_requests'))
    
    return

