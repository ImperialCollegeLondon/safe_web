import datetime
from safe_web_global_functions import link_button

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
    
    
    # create a link to take the user to the custom view
    links = [link_button("species", "species_profile", 'id')]
    
    # change the representation of the binomial field to use italics
    db.species_profile.binomial.represent = lambda binomial, row: I(binomial)
    
    # and the representation of the image link (can't use the global thumbnail function here 
    # as these are external images
    def _sp_img(row):
        return A(DIV(_style=('background: url(' + row.image_link + ') 50% 50% no-repeat; '
                             'background-size: cover; width: 120px; height: 100px;')),
                 _href=row.image_href)
    
    db.species_profile.image_link.represent = lambda value, row : _sp_img(row)
    db.species_profile.image_href.readable = False
    
    form = SQLFORM.grid(db.species_profile, csv=False, 
                        fields=[db.species_profile.image_link,
                                db.species_profile.common_name, 
                                db.species_profile.binomial, 
                                db.species_profile.iucn_status, 
                                db.species_profile.image_href],
                        headers={'species_profile.image_link': ''},
                        maxtextlength=250,
                        orderby='<random>',
                        create=False,
                        deletable=False,
                        editable=False,
                        details=False,
                        formargs={'showid':False},
                        links=links)
    
    return dict(form=form)


def species_profile():
    
    # retrieve the species id from the page arguments passed by the button
    # and then get the row, format it all and and send it to the view
    species_id = request.args(0)
    species = db(db.species_profile.id == species_id).select()[0]
    
    #Define some view dictionaries
    
    rlist = dict([('Not Evaluated', 'images/species/status_ne_on.gif'),
                    ('Data Deficient', 'images/species/status_dd_on.gif'),
                    ('Least Concern', 'images/species/status_lc_on.gif'),
                    ('Near Threatened', 'images/species/status_nt_on.gif'),
                    ('Vulnerable', 'images/species/status_vu_on.gif'),
                    ('Endangered', 'images/species/status_en_on.gif'),
                    ('Critically Endangered', 'images/species/status_cr_on.gif'),
                    ('Extinct in the Wild', 'images/species/status_ew_on.gif'),
                    ('Extinct', 'images/species/status_ex_on.gif')]) 


    prilist = dict(True = 'images/species/Natural-Colour.jpg',
                     False = 'images/species/Natural-Grey.jpg')

    palmlist = dict(True = 'images/species/Plantation-Colour.jpg',
                    False = 'images/species/Plantation-Grey.jpg')

    loglist = dict(True = 'images/species/Logged-Colour.jpg',
                   False = 'images/species/Logged-Grey.jpg')

    
    # put together a set of external links
    ext =  [(species.google_scholar_link, 'images/species/Google_scholar.png'),
            (species.wikipedia_link, 'images/species/Wikipedia.png'),
            (species.eol_link, 'images/species/eol.png'),
            (species.iucn_link, 'images/species/iucn.png'),
            (species.arkive_link, 'images/species/arkive.png'),
            (species.gbif_link, 'images/species/gbif.png')]
    
    external_links = [DIV(CENTER(A(IMG(_src=URL('static', x[1]), _height='50px'), _href=x[0], _target='_blank')), _class='col-sm-2') for x in ext]
    external_links = DIV(*external_links, _class='row')
    
    # modals to show definitions
    # modals to show definitions
    def modal_wrapper(title, content, id):
        
        return DIV(DIV(DIV(DIV(H4(title, _class="modal-title"),
                                _class="modal-header"),
                            DIV(*content,
                                _class="modal-body", _style='margin:0px 20px'),
                            _class="modal-content"),
                        _class="modal-dialog modal-sm", _role="document"),
                    _class="modal fade", _id=id, _role="dialog")
    
    # -- population trend
    tlist = {'stable': {'img':'images/species/stable.png', 'dsc':'Global population is stable'},
             'increasing': {'img':'images/species/increasing.png','dsc':'Global population is increasing'},
             'decreasing': {'img':'images/species/decreasing.png', 'dsc':'Global population is decreasing'},
             'unknown': {'img':'images/species/unknown.png', 'dsc':'Global population trends unknown'}}
    
    pop_modal = [DIV(IMG(_src=URL('static', v['img']), _height='40px'), v['dsc'], _class='row') for k, v in tlist.iteritems()]
    pop_modal = modal_wrapper('Global population trends', pop_modal, 'pop_modal')
    
    # -- local abundance
    alist = {'commonly seen': {'img':'images/species/common.png', 'dsc':'Species commonly seen'},
             'often seen': {'img':'images/species/often.png', 'dsc':'Species often seen'},
             'sometimes seen': {'img':'images/species/sometimes.png', 'dsc':'Species sometimes seen'},
             'rarely seen': {'img':'images/species/rare.png', 'dsc':'Species rarely seen'}}
    
    abnd_modal = [DIV(IMG(_src=URL('static', v['img']), _height='40px'), v['dsc'], _class='row') for k, v in alist.iteritems()]
    abnd_modal = modal_wrapper('Local population abundance', abnd_modal, 'abnd_modal')
    
    
    content =   CAT(HR(),
                    DIV(DIV(CENTER(IMG(_src=species.image_link, _height='85px')), _class='col-sm-3'),
                        DIV(CENTER(H3(species.common_name)), CENTER(H4(I(species.binomial))), _class='col-sm-6'),
                        DIV(CENTER(IMG(_src=URL('static', rlist[species.iucn_status]), _height='85')), _class='col-sm-3'),
                        _class='row'),
                    HR(),
                    DIV(DIV(CENTER(H5('Global populations'),
                               IMG(_src=URL('static', tlist[species.global_population]['img']), 
                                   _height='85px', _title= tlist[species.global_population]['dsc'],
                                   **{'_data-toggle':"modal", '_data-target':"#pop_modal"})),
                               _class='col-sm-2 col-sm-offset-1'),
                           DIV(CENTER(H5('Local abundance'),
                                      IMG(_src=URL('static', alist[species.local_abundance]['img']), 
                                      _height='85px', _title= alist[species.local_abundance]['dsc'],
                                      **{'_data-toggle':"modal", '_data-target':"#abnd_modal"})),
                                      _class='col-sm-2'),
                           DIV(CENTER(H5('In plantations'),
                                      IMG(_src=URL('static', palmlist[str(species.in_plantation)]), _height='85px')),
                                      _class='col-sm-2'),
                           DIV(CENTER(H5('In logged areas'),
                                      IMG(_src=URL('static', loglist[str(species.in_logged)]), _height='85px')),
                                      _class='col-sm-2'),
                           DIV(CENTER(H5('In primary forest'),
                                      IMG(_src=URL('static', prilist[str(species.in_primary)]), _height='85px')),
                                      _class='col-sm-2'),
                           _class='row'), HR(),
                    pop_modal, abnd_modal,
                    H4('Animal facts'), XML(species.animal_facts.replace('\n', '<br /><br />'), sanitize=True, permitted_tags=['br/']), BR(),
                    H4('Where do they live?'), species.where_do_they_live, BR(),
                    H4('What habitats do they live in?'), species.habitat, BR(),
                    H4('What do they eat?'), species.what_do_they_eat, BR(),
                    H4('Who eats them?'), species.who_eats_them, BR(),
                    H4('What are they threatened by?'), species.threatened_by, BR(),
                    H4('Search for this species on:'), external_links, BR())
    
    return dict(content = content)


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
