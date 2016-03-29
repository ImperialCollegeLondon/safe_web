import datetime

## -----------------------------------------------------------------------------
## HEALTH AND SAFETY
## - controllers to view and edit a user's H&S form and for admin to view records
## -- TODO - how hardline do we want to be about completeness of fields
## -----------------------------------------------------------------------------

@auth.requires_login()
def health_and_safety():
    
    """
    provides access to the health and safety information 
    for the logged in user, both edit and create use the same interface
    """

    # Restrict the user 
    db.health_and_safety.user_id.requires = IS_IN_DB(db(db.auth_user.id == auth.user.id),
                                                     db.auth_user.id, '%(first_name)s %(last_name)s')
    
    # lock the widget for user_id
    db.health_and_safety.user_id.writable = False
    db.health_and_safety.date_last_edited.readable = False
    db.health_and_safety.date_last_edited.writable = False
    
    # look for an existing record, otherwise initialise a blank one
    # - this is a bit of a hack. The DB backend accepts the empty strings
    #   but conveniently the SQLFORM validation doesn't, so you can't just
    #   click through with the blank form 
    rows = db(db.health_and_safety.user_id == auth.user.id).select()
    if len(rows) > 0:
        record = rows.first().id
    else:
        record = db.health_and_safety.insert(user_id = auth.user.id, 
                                             passport_number = '',
                                             emergency_contact_name = '',
                                             emergency_contact_address = '',
                                             emergency_contact_phone = '',
                                             emergency_contact_email = '',
                                             insurance_company = '',
                                             insurance_emergency_phone = '',
                                             insurance_policy_number = '')
    
    # get the form with the existing or new record
    form = SQLFORM(db.health_and_safety, record=record, 
                   showid=False, labels={'user_id': 'Name'})
    
    # now intercept and parse the various inputs
    if form.process(onvalidation=validate_health_and_safety).accepted:
        # insert the h&s record id into the user table 
        #- this field is primarily to avoid a lookup to just to 
        #  populate links from visit and reservation details pages
        db(db.auth_user.id == auth.user.id).update(h_and_s_id = form.vars.id)
        session.flash = CENTER(B('Thanks for providing your health and safety information.'), _style='color: green')
        redirect(URL('default', 'index'))
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
    
    user_id = request.args(0)
        
    # look for an existing record
    rows = db(db.health_and_safety.user_id == user_id).select()
    if len(rows) > 0:
        # get the form with the existing or new record
        form = SQLFORM(db.health_and_safety, record=user_id, 
                       showid=False, labels={'user_id': 'Name'},
                       readonly=True)
    else:
        form = None
    return dict(form=form)
