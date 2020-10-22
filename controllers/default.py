# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

from collections import Counter
import random
import datetime
import inspect
from gluon.contrib import simplejson
from gluon.serializers import json, loads_json
from safe_web_global_functions import thumbnail
from safe_web_datasets import (dataset_taxon_search, dataset_author_search, dataset_date_search, 
                               dataset_text_search, dataset_field_search, dataset_locations_search, 
                               dataset_spatial_search, dataset_spatial_bbox_search, dataset_query_to_json,
                               get_index_hashes, get_index)

## -----------------------------------------------------------------------------
## Default page controllers
## -----------------------------------------------------------------------------

def index():
    """
    example action using the internationalization operator T and flash
    rendered by views/default/index.html or views/generic.html
    """
    
    # OH GOD THIS CODE IS A DISGRACE, IN MY DEFENCE IT WAS PROBABLY THE FIRST PAGE
    # I WROTE IN WEB2PY, BUT THAT DOESN'T EXCUSE THE LACK OF COMMENTS.
    
    n_outputs = db(db.outputs).count()
    n_researchers = db(db.auth_user).count()
    n_dataset_versions = db(db.published_datasets).count()
    # Using SQL directly to return only th value needed
    n_dataset_concepts =  db.executesql('select count(distinct zenodo_concept_id) '
                                            'from published_datasets;')[0][0]
    
    
    proj_query = db(db.project_id.project_details_id == db.project_details.id)
    n_proj = proj_query.count()
    research_areas = proj_query.select(db.project_details.research_areas)    
    ra_list = [r.research_areas for r in research_areas]
    ra_list = [item for sublist in ra_list for item in sublist]
    ra_table = Counter(ra_list)
    
    ra_string = [k + ' (' + str(v) + ')' for k, v in ra_table.iteritems()]
    
    # BUILD a carousel of recent stuff - 4 each of news, blog, project, outputs
    n_items = 4
    news = db(db.news_posts.hidden == 'F').select(orderby=~db.news_posts.date_posted, limitby=(0,n_items))
    blog = db((db.blog_posts.hidden == 'F') &
              (db.blog_posts.admin_status == 'Approved')).select(orderby=~db.blog_posts.date_posted, limitby=(0,n_items))
    proj = db((db.project_id.project_details_id == db.project_details.id) &
              (db.project_details.admin_status == 'Approved')).select(db.project_details.ALL, orderby=~db.project_details.start_date, limitby=(0,n_items))
    outp = db(db.outputs.admin_status == 'Approved').select(orderby=~db.outputs.submission_date, limitby=(0,n_items))
    
    # MERGE - need to extract an id number, a title and an image  and build a link for each
    to_show = [proj, news, blog, outp]
    
    titles = [r.title for sublist in to_show for r in sublist]
    
    easy_ids = [r.id for sublist in to_show[1:] for r in sublist]
    proj_ids = [r.project_id for r in proj]
    ids = proj_ids + easy_ids
    
    cont = ['projects','news','blogs', 'outputs']
    cont = [i for i in cont for _ in xrange(n_items)]
    func = ['project_view','news_post', 'blog_post', 'view_output']
    func = [i for i in func for _ in xrange(n_items)]
    kind = ['Project: ','News: ','Blog: ', 'Output: ']
    kind = [i for i in kind for _ in xrange(n_items)]
    
    link_url = [URL(c,r, args=i) for c,r,i in zip(cont, func, ids)]
    
    thumb_file = [r.thumbnail_figure for sublist in to_show for r in sublist]
    
    # ind = range(4 * n_items)
    #
    # ind_args = [{'_data-target': "#newsCarousel", '_data-slide-to': str(i)} for i in ind]
    # ind_args[0]['_class'] = 'active'
    # indicators = [LI(**args) for args in ind_args]
    
    slides_args = [{'_class':'item'}] * 4 * n_items
    slides_args[0] = {'_class':'item active'}
    
    items = [DIV(DIV(thumbnail(th, 'missing_news.png'), _class='col-sm-3'),
                 DIV(A(H4(kn,ti), _href=ln), _class='col-sm-9'),
                 _style='margin: auto;width:85%;overflow:hidden', **args)
             for th, kn, ti, ln, args in zip(thumb_file, kind, titles, link_url, slides_args)]
    
    random.shuffle(items)
    
    news_carousel = DIV(#OL(indicators, _class="carousel-indicators"),
                        DIV(items, _class="carousel-inner", _role="listbox"),
                        A(SPAN(_class="glyphicon glyphicon-chevron-left"),
                          SPAN('Previous', _class='sr-only'),
                            **{'_class':"left carousel-control", '_href':"#newsCarousel",
                               '_role':"button", '_data-slide':"prev",
                               '_style':"background-image: none;background:grey;width:8%"}),
                        A(SPAN(_class="glyphicon glyphicon-chevron-right"),
                          SPAN('Next', _class='sr-only'),
                            **{'_class':"right carousel-control", '_href':"#newsCarousel",
                               '_role':"button", '_data-slide':"next",
                               '_style':"background-image: none;background:grey;width:8%"}),
                        **{'_id': "newsCarousel", 
                           '_class':"carousel slide", 
                           '_style':"overflow:hidden",
                           '_data-ride':"carousel"})
   
    return dict(n_proj=n_proj, n_outputs=n_outputs, n_researchers=n_researchers, 
                n_dataset_concepts=n_dataset_concepts, n_dataset_versions=n_dataset_versions,
                ra_string = ra_string, news_carousel=news_carousel)


def science_at_safe():
    
    return response.render()

def science_at_safe_2020():
    
    return response.render()

def covid_19():
    
    return response.render()


def todo():
    
    return response.render()

# def wiki():
#
#     return auth.wiki()

@auth.requires_login()
def my_safe():
    
    """
    This controller presents a simple set of grids showing projects, outputs
    visits, blogs, volunteer positions, work offers that a user is associated with.
    
    At the start of development, record specific URLs typically used URL args:
        controller/function/arg
    but later on variables get used:
        controller/function?var=1
    
    Arguably, the codebase should be rewritten to use one or the other. I
    think variables are clearer but that is a big job to rewrite.
    """
    
    # for most simple tables, provide a look up of which tables and columns to query
    # - the dictionary key is a tag used to populate boostrap nav tabs
    # - query selects a chunk of data containing the fields to display
    # - select details which fields to recover from the query
    # - 'none' provides a message if there aren't any rows that the user is a member of
    # - 'display' provides a field that is to be shown for each item
    # - 'cntr' and 'view' provide the controller and view for the linked URL
    # - 'url_args' provides a list of fields used to specify the URL
    # - 'url_vars' provides a list of two-tuples (variable name, value field) 
    #    to populate variables used to specify the URL
    # - 'status' provides a field to match into the status icons. 
    
    # The status entry can be set to None to suppress badges (e.g. for datasets, 
    # which are always published)
    
    membership_dict = {'projects': {'query': (db.project_members.user_id == auth.user.id) &
                                             (db.project_members.project_id == db.project_id.id) &
                                             (db.project_details.id == db.project_id.project_details_id),
                                    'select': [db.project_details.project_id, db.project_details.version, db.project_details.title, db.project_details.admin_status],
                                    'none': 'You are not a member of any projects',
                                    'cntr': 'projects', 'view': 'project_details',
                                    'display': db.project_details.title,
                                    'url_args': [db.project_details.project_id, db.project_details.version],
                                    'url_vars': [],
                                    'status': db.project_details.admin_status,
                                    'header': 'Projects'},
                       'outputs':  {'query': (db.outputs.user_id == auth.user.id),
                                    'select': [db.outputs.id, db.outputs.title, db.outputs.admin_status],
                                    'none': 'You have not uploaded any outputs',
                                    'cntr': 'outputs', 'view': 'output_details',
                                    'display': db.outputs.title,
                                    'url_args': [db.outputs.id],
                                    'url_vars': [],
                                    'status': db.outputs.admin_status,
                                    'header': 'Outputs'},
                       'blogs':    {'query': (db.blog_posts.user_id == auth.user.id),
                                    'select': [db.blog_posts.id, db.blog_posts.title, db.blog_posts.admin_status],
                                    'none': 'You have not created any blog posts',
                                    'cntr': 'blogs', 'view': 'blog_details',
                                    'display': db.blog_posts.title,
                                    'url_args': [db.blog_posts.id],
                                    'url_vars': [],
                                    'status': db.blog_posts.admin_status,
                                    'header': 'Blog posts'},
                       'visits'  : {'query': (db.research_visit_member.user_id == auth.user.id) &
                                             (db.research_visit_member.research_visit_id == db.research_visit.id),
                                    'select': [db.research_visit.id, db.research_visit.title, db.research_visit.admin_status],
                                    'none': 'You are not a member of any research visits',
                                    'cntr': 'research_visits', 'view': 'research_visit_details',
                                    'display': db.research_visit.title,
                                    'url_args': [db.research_visit.id],
                                    'url_vars': [],
                                    'status': db.research_visit.admin_status,
                                    'header': 'Research visits'},
                       'volunteer':{'query': (db.help_offered.user_id == auth.user.id),
                                    'select': [db.help_offered.id, db.help_offered.statement_of_interests, db.help_offered.admin_status],
                                    'none': 'You have not created any offers to volunteer at SAFE',
                                    'cntr': 'marketplace', 'view': 'volunteer_details',
                                    'display': db.help_offered.statement_of_interests,
                                    'url_args': [db.help_offered.id],
                                    'url_vars': [],
                                    'status': db.help_offered.admin_status,
                                    'header': 'Volunteer offers'},
                       'datasets' :{'query': (db.published_datasets.uploader_id == auth.user.id),
                                    'select': [db.published_datasets.zenodo_record_id,
                                               db.published_datasets.dataset_title],
                                    'none': 'You have not uploaded any datasets',
                                    'cntr': 'datasets', 'view': 'view_dataset',
                                    'display': db.datasets.dataset_title,
                                    'url_args': [],
                                    'url_vars': [('id', db.published_datasets.zenodo_record_id)],
                                    'status': None,
                                    'header': 'Datasets'},
                       'request':  {'query': (db.help_request.user_id == auth.user.id),
                                    'select': [db.help_request.id, db.help_request.work_description, db.help_request.admin_status],
                                    'none': 'You have not created any requests for project help at SAFE',
                                    'cntr': 'marketplace', 'view': 'help_request_details',
                                    'display': db.help_request.work_description,
                                    'url_args': [db.help_request.id],
                                    'url_vars': [],
                                    'status': db.help_request.admin_status,
                                    'header': 'Help requests'}
                      }
    
    # Loop over the dictionary, populating tables for each grid of results
    grids = {}
    
    for k, v in membership_dict.iteritems():
        
        query = v['query']
        
        # run the query and see how many rows are returned
        if db(query).count() > 0:
            
            # select the rows if there are any
            rows = db(query).select(*v['select'])
            
            # build a table row containing the display name with a URL link
            rows = [TR(TD(A(r[v['display']], 
                            _href= URL(v['cntr'], v['view'], 
                                       args=[r[x] for x in v['url_args']],
                                       vars={x[0]: r[x[1]] for x in v['url_vars']}
                                      )),
                          _style='width:90%'),
                      DIV() if v['status'] is None else TD(approval_icons[r[v['status']]]))
                   for r in rows]
            
            # package into a table
            grids[k] = TABLE(*rows, _class='table table-striped', _style='width:100%')
            
        else:
            # give a simple message back if there are no rows
            grids[k] = TABLE(TR(TD()),TR(TD(B(CENTER(v['none'])))), _class='table table-striped', _style='width:100%')
    
    # build the HTML programatically - have to include some args indirectly because
    # they contain hyphens
    ul_tags = {'_class':"nav nav-tabs nav-justified", '_data-tabs':"tabs"}
    a_tags = {'_data-toggle':"tab"}
    
    headers = [v['header'] for k,v in membership_dict.iteritems()]
    keys = membership_dict.keys()
    
    # need a UL defining the tabs and a DIV containing tab contents as tab pane DIVs .
    tabs = UL([LI(A(h, _href='#'+k , **a_tags), _role='presentation', _name=k) for k, h in zip(keys, headers)], **ul_tags)
    content = DIV([DIV(grids[k], _class="tab-pane", _id=k) for k in keys], _class="tab-content")
    
    # amend the tabs and content to make one active on load
    active_tab = request.vars['tab']
    if active_tab is None or active_tab not in membership_dict:
        active_tab = 'projects'
    
    tabs.element('li[name=' + active_tab + ']')['_class'] = 'active'
    content.element('#' + active_tab)['_class'] += ' active'
    
    return dict(grids = CAT(tabs, content))


def lang_switch():
    
    """
    Only exists to switch languages and reload calling page
    """
    
    session.lang = 'my' if session.lang == 'en' else 'en'
    
    return response.render()



## ----------------------------------------------------------------------------
## -- This uses a Google Service Account to connect to the Google Calendar API
##    which operates as follows:
##    1) Visit: https://console.developers.google.com/
##    2) Create a developer project for the website
##    3) Generate a set of service account credentials for the project and enable
##       the Google calendar API
##    4) Create a calendar in the google account and note its ID
##    5) Share that calendar (editing access) with the email of the service account,
##       which is currently: 
##       safe-project-website-service@safe-project-website-140316.iam.gserviceaccount.com
##    6) The account should now be able to write and delete events to the account
##    7) In order to delete events, you need the event ID, so need to store those
##
## -- TODO - think about whether this service needs to be built each time or 
##           whether the service could be created in a model file and used here
## -- TODO - fix up exception handling
## -- TODO - secure the private key JSON file. Where to keep it?
## -- TODO - handle offline problems. Don't see how this would happen in reality.
## ----------------------------------------------------------------------------
#
# # create a global dictionary of calendar IDs
# calID = {'volunteers': 'k23sbip8av2nvv196n9kupj5ss@group.calendar.google.com',
#          'help_request': 'fber8126s5pdgccm3k13s90q58@group.calendar.google.com',
#          'booked_visits': 'rairu8u98scfb8cgn86qdrgtic@group.calendar.google.com'}
#
#
# def _post_event_to_google_calendar(event, calendarId):
#
#     """
#     Function to post an event to a calendar and return event details.
#     See:
#     https://developers.google.com/api-client-library/python/auth/service-accounts
#     """
#
#     # we want the calendar API
#     scopes = 'https://www.googleapis.com/auth/calendar'
#
#     # Load the service account credentials
#     # TODO -think about where to store this securely.
#     cred_json = os.path.join(request.folder, 'private/google_auth/SAFE-project-website-6a272f141d5a.json')
#     credentials = ServiceAccountCredentials.from_json_keyfile_name(cred_json, scopes)
#
#     # authorise those credentials with Google
#     http_auth = credentials.authorize(Http())
#
#     # build the service handler
#     service = build('calendar', 'v3', http=http_auth)
#
#     # run the insert
#     #try:
#     event = service.events().insert(calendarId=calendarId, body=event).execute()
#     # except AccessTokenRefreshError:
#     #     # The AccessTokenRefreshError exception is raised if the credentials
#     #     # have been revoked by the user or they have expired.
#     #     print ('The credentials have been revoked or expired, please re-run'
#     #            'the application to re-authorize')
#
#     return event
#

## ----------------------------------------------------------------------------
## EXPOSE VARIOUS USER FUNCTIONS
## ----------------------------------------------------------------------------

def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/bulk_register
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    """
    return dict(form=auth())


@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)



# ------------------------------------------------------------------
# Dataset search API
# ------------------------------------------------------------------

def api():
    
    """
    This controller provides an API endpoint to query the various
    dataset indices to find data. I did look at the parse_as_rest
    option (falling by the wayside) and the pydal.restapi (extremely
    bleeding edge), but this approach is more tuned to the particular
    searches we want to support and is easier to include spatial 
    queries.
    """
    

    # Some API endpoints use endpoint specific query string parameters,
    # but the following two apply to most endpoints, so strip them off
    # to allow the remaining parameters to be checked against the API 
    # of individual endpoint functions.
    # - 'most_recent': a flag to get only the recent versions of datasets
    # - 'ids': a way to restrict the set of possible datasets searched.
                
    if 'most_recent' in request.vars:
        most_recent = request.vars.pop('most_recent')

        if most_recent == '':
            most_recent = True
        else:
            raise HTTP(400, 'Do not provide a value for the most_recent query flag.')
    else:
        most_recent = False
    
    if 'ids' in request.vars:
        ids = request.vars.pop('ids')
        
        if isinstance(ids, str):
            ids = [ids]
        
        try:
            ids = [int(vl) for vl in ids]
        except ValueError:
            raise HTTP(400, 'Invalid ids value')
            
    else:
        ids = None
        
    # A dictionary of endpoint names and query building functions
    # for the search endpoint
    search_func = {'taxa': dataset_taxon_search,
                   'authors': dataset_author_search,
                   'dates': dataset_date_search,
                   'text': dataset_text_search,
                   'fields': dataset_field_search,
                   'locations': dataset_locations_search,
                   'spatial': dataset_spatial_search,
                   'bbox': dataset_spatial_bbox_search
                  }
    
    # Handle the API arguments
    if not len(request.args):
        
        # return the docstrings as HTML to populate the API html description
        docs = CAT([H4(ky) + PRE(inspect.getdoc(fn)) for ky, fn in  search_func.iteritems()])
        return dict(docs=docs)
    
    elif request.args[0] == 'index_hashes':
        
        # This retrieves the current version hashs from the ram cache.
        
        # NOTE: the expiry time of None means these never expire and so functions
        # that update versions (publishing a record, reloading gazetteer) need
        # to clear this variable so that it will be reset by the next call to this
        # API.
        
        val = cache.ram('index_hashes', get_index_hashes, time_expire=None)
    
    elif request.args[0] == 'record' and len(request.args) == 2:
        # /api/record/zenodo_record_id endpoint provides a machine readable
        # version of the data contained in the dataset description
        try:
            record_id = int(request.args[1])
        except ValueError:
            raise HTTP(400, 'Non-integer record number')
        else:
            record = db(db.published_datasets.zenodo_record_id == record_id).select().first()
        
            if record is None:
                val = {'error': 404, 'message': 'Unknown record number.'}
            else:
                # Build the record metadata, including taxa and locations
                val = record.dataset_metadata
                val['publication_date'] = record.publication_date
                val['zenodo_concept_id'] = record.zenodo_concept_id
                val['zenodo_record_id'] = record.zenodo_record_id
                val['taxa'] = record.dataset_taxa.select()
                val['locations'] = record.dataset_locations.select(db.dataset_locations.name,
                                                                   db.dataset_locations.new_location,
                                                                   db.dataset_locations.wkt_wgs84)
    
    elif request.args[0] == 'access_status' and len(request.args) == 2:
    
        # Small payload API for getting dataset access details, used by change_dataset_access
        try:
            record_id = int(request.args[1])
        except ValueError:
            raise HTTP(400, 'Non-integer record number')
        else:
            record = db(db.published_datasets.zenodo_record_id == record_id).select().first()
        
            if record is None:
                raise HTTP(400, 'Unknown record number')
            else:
                val = dict(dataset_title=record.dataset_title,
                           dataset_access=record.dataset_access.capitalize(), 
                           dataset_embargo=record.dataset_embargo,
                           dataset_conditions=record.dataset_conditions)
    
    elif request.args[0] == 'files':
        
        # /api/files endpoint provides a json file containing the files associated
        # with dataset records, allowing filtering by ID and most_recent query parameters
                
        # version of the data contained in the dataset description
        qry = (db.published_datasets.id == db.dataset_files.dataset_id)
        val = dataset_query_to_json(qry, most_recent, ids, 
                                    fields = [('published_datasets', 'publication_date'), 
                                              ('published_datasets', 'zenodo_concept_id'), 
                                              ('published_datasets', 'zenodo_record_id'), 
                                              ('published_datasets', 'dataset_access'), 
                                              ('published_datasets', 'dataset_embargo'), 
                                              ('published_datasets', 'dataset_title'), 
                                              ('published_datasets', 'most_recent'), 
                                              ('dataset_files', 'checksum'),
                                              ('dataset_files', 'filename'),
                                              ('dataset_files', 'filesize')])
        
        # repackage the db output into a single dictionary per file                            
        entries = val['entries'].as_list()
        [r['published_datasets'].update(r.pop('dataset_files')) for r in entries]
        val['entries'] = [r['published_datasets'] for r in entries]

    elif request.args[0] == 'index':

        # This mirrors the files endpoint but always returns a complete list of all 
        # files available across the SAFE dataset repository along with publication
        # details and accessibility.
        
        # The output from this endpoint is used as the core index for the safedata
        # R package. The output is therefore cached in ram: i) to speed up access and
        # ii) to provide an MD5 hash of the contents to provide a version stamp. Note
        # the expiry date of None in the cache means that it never expires - publishing
        # a new dataset therefore needs to clear the ram cache to reset these version
        # stamps

        val = cache.ram('index', get_index, time_expire=None)

    elif request.args[0] == 'validator_locations':
        
        # This provides a dictionary using valid location names as keys to their bounding
        # boxes and a dictionary using aliases as keys to their canonical names. It is 
        # primarily intended for use by the safedata-validator package
        
        locations = db().select(db.gazetteer.location, 
                                db.gazetteer.bbox_xmin,
                                db.gazetteer.bbox_xmax,
                                db.gazetteer.bbox_ymin,
                                db.gazetteer.bbox_ymax)
    
        # reformat to a dictionary of bbox tuples
        locations = {r.location: (r.bbox_xmin, r.bbox_xmax, r.bbox_ymin, r.bbox_ymax) 
                     for r in locations}
    
        # Add aliases dictionary - aliases are unique so use them as key to locations, which
        # might have more than one alias
        aliases = db().select(db.gazetteer_alias.location, 
                              db.gazetteer_alias.alias)
    
        aliases = {r.alias: r.location for r in aliases}
    
        val = {'locations': locations, 'aliases': aliases}
    
    elif request.args[0] == 'gazetteer':
        
        # Get the gazetteer - the table is populated directly from the gazetteer geojson
        # stored in static, and the MD5 sum of that file is used as a version stamp, so
        # this endpoint simply redirects to that file, both for speed and to preserve the
        # JSON file structure for MD5 comparison between local and server versions.
        
        redirect(URL('static','files/gis/gazetteer.geojson'))

    elif request.args[0] == 'location_aliases':
        
        # Get the location aliases - as with the gazetteer endpoint, this is simply a 
        # redirect to the file used to populate the table. 

        redirect(URL('static','files/gis/location_aliases.csv'))
    
    elif request.args[0] == 'location_aliases':
        
        # Get the locations - for geojson, we need an id, a geometry and a dictionary
        # of properties. This query uses the with_alias() to strucure the results with
        # id and geojson outside of the 'gazetteer' table dictionary, making it really
        # simple to restucture them into a geojson Feature entry
        val = db(db.gazetteer_alias).select(db.gazetteer_alias.ALL).as_list()
        
    elif request.args[0] == 'taxa':
        
        # Get all taxa across studies - retrieve gbif codes, names and status along
        # with the number of datasets the taxon appears in
        
        taxon_fields = [db.dataset_taxa.gbif_id, db.dataset_taxa.taxon_rank,
                        db.dataset_taxa.taxon_name, db.dataset_taxa.gbif_status,
                        db.dataset_taxa.gbif_parent_id]
        
        taxon_count = [db.dataset_taxa.taxon_name.count().with_alias('n_datasets')]
        
        val = db(db.dataset_taxa).select(*taxon_fields + taxon_count,
                                         groupby=taxon_fields).as_list()
        
        # repackage the Rows to provide a flat json per taxon format.
        for txn in val:
            txn.update(txn.pop('dataset_taxa'))
            del txn['_extra']

    elif request.args[0] == 'search' and len(request.args) == 2 and request.args[1] in search_func:
            
        # validate the remaining query search parameters to the search function arguments
        func = search_func[request.args[1]]
        fn_args = inspect.getargspec(func).args
        unknown_args = set(request.vars) - set(fn_args)
        
        if unknown_args:
            raise HTTP(400, 'Unknown query parameters to endpoint'
                       ' /{}: {}'.format(request.args[0],','.join(unknown_args)))
        else:
            try:
                qry = func(**request.vars)
                # does the function return a query or an error dictionary
                if isinstance(qry, dict):
                    val = qry
                else:
                    val = dataset_query_to_json(qry, most_recent, ids)
            except TypeError as e:
                raise HTTP(400, 'Could not parse api request: {}'.format(e))
    else:
        raise HTTP(400, 'Unknown endpoint {}'.format(request.env.web2py_original_uri))
    
    return response.json(val)
