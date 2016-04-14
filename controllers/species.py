import datetime

## -----------------------------------------------------------------------------
## SPECIES PROFILES
## create a links object that associates a row with the image link set for it
## TODO - ugly forcing of aspect ratio, but most pretty much 3:4
## TODO - some of the linked images for existing profiles are All rights reserved. Need to replace.
## -----------------------------------------------------------------------------

def species():
    
    """
    Controller to show a SQLFORM.grid view of species profiles and
    expose links to a standalone species profile controller
    """
        
    links = [dict(header = '', body = lambda row: A(IMG(_src = row.image_link, 
             _height = 100, _width=120), 
             _href=row.image_href, _title=row.image_title)),
             dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                       SPAN('View', _class="buttontext button"),
                                       _class="button btn btn-default", 
                                       _href=URL("species","species_profile", args=[row.id], user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;'))] 
    
    # need these three fields in the fields list to allow the links
    # to be created but don't want to actually show them in the grid
    db.species_profile.image_link.readable=False
    db.species_profile.image_href.readable=False
    db.species_profile.image_title.readable=False
    
    # change the representation of the binomial field to use italics
    # - creates a mini function (lambda) that acts on a row object to
    #   alter the value passed to the grid
    db.species_profile.binomial.represent = lambda binomial, row: I(binomial)
    
    form = SQLFORM.grid(db.species_profile, csv=False, 
                        fields=[db.species_profile.common_name, 
                                db.species_profile.binomial, 
                                db.species_profile.iucn_status, 
                                db.species_profile.image_link,
                                db.species_profile.image_href,
                                db.species_profile.image_title
                                ],
                        maxtextlength=250,
                        create=False,
                        deletable=False,
                        editable=False,
                        details=False,
                        formargs={'showid':False},
                        links=links,
                        links_placement='left')
    
    return dict(form=form)


def species_profile():
    
    # retrieve the species id from the page arguments passed by the button
    # and then get the row and send it to the view
    species_id = request.args(0)
    species = db(db.species_profile.id == species_id).select()[0]
    
    return dict(species = species)


@auth.requires_membership('species_profiler')
def manage_species():
    
    db.species_profile.updated_by.readable = False
    db.species_profile.updated_by.writable = False
    db.species_profile.updated_on.readable = False
    db.species_profile.updated_on.writable = False

    
    form = SQLFORM.grid(db.species_profile, 
                        fields = [db.species_profile.binomial, db.species_profile.common_name],
                        formargs = {'showid': False},
                        deletable = False,
                        details = False,
                        onvalidation = validate_species)
    
    # if form.process().accepted:
    #     session.flash = CENTER(B('Species added.'), _style='color: green')
    #     redirect(URL('species','species'))
    # else:
    #     response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
    
    return dict(form = form)


def validate_species(form):
    
    # record who last edited the profile and when
    form.vars.updated_by = auth.user.id
    form.vars.updated_on = datetime.date.today().isoformat()
