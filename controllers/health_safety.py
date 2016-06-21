import datetime

## -----------------------------------------------------------------------------
## HEALTH AND SAFETY
## - controllers to view and edit a user's H&S form and for admin to view records
## -- TODO - how hardline do we want to be about completeness of fields
## -----------------------------------------------------------------------------

@auth.requires_login()
def health_and_safety():
    
    """
    provides access to the health and safety information:
    - for the logged in user, both edit and create use the same interface
    - for admin and project coordinators, as a view interface
    """
    
    # if no user id is provided as an argument then go to the
    # logged in user record as an edit interface
    uid = request.args(0)
    if uid is not None:
        if db.auth_user(uid) is None:
            session.flash = CENTER(B('Unknown user ID number', _style='color:red;'))
            redirect(URL('default','index'))
    else:
        uid = auth.user.id
    
    # Set up what record to get.
    # - If the logged in user ID and requested ID match, then we're 
    #   editing a possibly new record
    # - Otherwise we're viewing an existing hs record if it exists
    #   and we have a right to view it (Admin or Project Coordinator)
    user_record = db.auth_user(uid)
    
    if int(uid) == auth.user.id:
        if user_record.h_and_s_id is None:
            hs_record = None
        else:
            hs_record = db.health_and_safety(user_record.h_and_s_id)
        readonly = False
    else:
        # does this user have any right to view
        user_projects = db(db.project_members.user_id == uid)._select(db.project_members.project_id)
        project_coords = db((db.project_members.project_id.belongs(user_projects)) &
                            (db.project_members.is_coordinator == 'T')).select()
        is_coordinator_for_user = any([auth.user.id == r.user_id for r in project_coords])
        
        if not auth.has_membership('admin') and not is_coordinator_for_user:
            session.flash = CENTER(B('You do not have access rights to the H&S record for this user', _style='color:red;'))
            redirect(URL('default','index'))
        
        if user_record.h_and_s_id is None:
            session.flash = CENTER(B('No H&S record for this user', _style='color:red;'))
            redirect(URL('default','index'))
        else:
            hs_record = db.health_and_safety(user_record.h_and_s_id)
        readonly = True
    
    # lock the widget for user_id and make it use the uid as a default
    db.health_and_safety.user_id.default = uid
    db.health_and_safety.user_id.writable = False
    db.health_and_safety.date_last_edited.readable = False
    db.health_and_safety.date_last_edited.writable = False
    
    # get the form with the existing record
    form = SQLFORM(db.health_and_safety, 
                   readonly = readonly,
                   record=hs_record, 
                   showid=False,
                   labels={'user_id': 'Name'})
    
    # now intercept and parse the various inputs
    if form.process(onvalidation=validate_health_and_safety).accepted:
        # insert the h&s record id into the user table 
        #- this field is primarily to avoid a lookup to just to 
        #  populate links from visit and reservation details pages
        db(db.auth_user.id == auth.user.id).update(h_and_s_id = form.vars.id)
        
        response.flash = CENTER(B('Thanks for updating your health and safety information.'), _style='color: green')
        redirect(URL('health_safety','health_and_safety', args=uid))
    elif form.errors:
        response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
    else:
        pass
    
    
    return dict(form=form)


def validate_health_and_safety(form):
    
    """
    Pretty minimal - currently just updates the date edited
    """
    form.vars.date_last_edited = datetime.date.today().isoformat()


@auth.requires_membership('admin')
def admin_view_health_and_safety():
    
    """
    provides access to the health and safety information for admin
    """
    
    # get the form with the existing or new record
    form = SQLFORM.grid(db.health_and_safety.id == db.auth_user.h_and_s_id,
                        fields = [db.auth_user.id, db.auth_user.last_name, db.auth_user.first_name],
                        editable= False,
                        create=False,
                        deletable=False,
                        viewargs = {'showid':False}
                        )
    
    return dict(form=form)
