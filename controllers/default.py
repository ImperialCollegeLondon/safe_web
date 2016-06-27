# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import datetime
import dateutil.parser
import requests
from collections import Counter
import random

## -----------------------------------------------------------------------------
## Used to access the Google Calendar API
## -----------------------------------------------------------------------------

from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from apiclient.discovery import build

## -----------------------------------------------------------------------------
## Default page controllers
## -----------------------------------------------------------------------------

def index():
    """
    example action using the internationalization operator T and flash
    rendered by views/default/index.html or views/generic.html
    """
    
    proj_query = db(db.project_id.project_details_id == db.project_details.id)
    n_proj = proj_query.count()
    research_areas = proj_query.select(db.project_details.research_areas)
    n_outputs = db(db.outputs).count()
    n_researchers = db(db.auth_user).count()
    
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
    
    thumb_url = [URL('default', 'download', args = r.thumbnail_figure) for sublist in to_show for r in sublist]
    
    # ind = range(4 * n_items)
    #
    # ind_args = [{'_data-target': "#newsCarousel", '_data-slide-to': str(i)} for i in ind]
    # ind_args[0]['_class'] = 'active'
    # indicators = [LI(**args) for args in ind_args]
    
    slides_args = [{'_class':'item'}] * 4 * n_items
    slides_args[0] = {'_class':'item active'}
    
    items = [DIV(DIV(IMG(_src=th, _height='100px'), _class='col-sm-3'),
                 DIV(A(H4(kn,ti), _href=ln), _class='col-sm-9'),
                 _style='margin: auto;width:85%;overflow:hidden', **args)
             for th, kn, ti, ln, args in zip(thumb_url, kind, titles, link_url, slides_args)]
    
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
                ra_string = ra_string, news_carousel=news_carousel)



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
    """
    
    # for most simple tables, provide a look up of which tables and columns to query
    # - the dictionary key is a tag used to populate boostrap nav tabs
    # - query selects a chunk of data containing the fields to display
    # - select details which fields to recover from the query
    # - 'none' provides a message if there aren't any rows that the user is a member of
    # - 'display' provides a field that is to be shown for each item
    # - 'cntr' and 'view' provide the controller and view for the linked URL
    # - 'url_args' provides a list of fields used to specify the URL
    # - 'status' provides a field to match into the status icons. 
    # There is currently no provision for a display grid without status icons.
    
    membership_dict = {'projects': {'query': (db.project_members.user_id == auth.user.id) &
                                             (db.project_members.project_id == db.project_id.id) &
                                             (db.project_details.id == db.project_id.project_details_id),
                                    'select': [db.project_details.project_id, db.project_details.version, db.project_details.title, db.project_details.admin_status],
                                    'none': 'You are not a member of any projects',
                                    'cntr': 'projects', 'view': 'project_details',
                                    'display': db.project_details.title,
                                    'url_args': [db.project_details.project_id, db.project_details.version],
                                    'status': db.project_details.admin_status,
                                    'header': 'Projects'},
                       'outputs':  {'query': (db.outputs.user_id == auth.user.id),
                                    'select': [db.outputs.id, db.outputs.title, db.outputs.admin_status],
                                    'none': 'You have not uploaded any outputs',
                                    'cntr': 'outputs', 'view': 'output_details',
                                    'display': db.outputs.title,
                                    'url_args': [db.outputs.id],
                                    'status': db.outputs.admin_status,
                                    'header': 'Outputs'},
                       'blogs':    {'query': (db.blog_posts.user_id == auth.user.id),
                                    'select': [db.blog_posts.id, db.blog_posts.title, db.blog_posts.admin_status],
                                    'none': 'You have not created any blog posts',
                                    'cntr': 'blog', 'view': 'blog_details',
                                    'display': db.blog_posts.title,
                                    'url_args': [db.blog_posts.id],
                                    'status': db.blog_posts.admin_status,
                                    'header': 'Blog posts'},
                       'visits'  : {'query': (db.research_visit_member.user_id == auth.user.id) &
                                             (db.research_visit_member.research_visit_id == db.research_visit.id),
                                    'select': [db.research_visit.id, db.research_visit.title, db.research_visit.admin_status],
                                    'none': 'You are not a member of any research visits',
                                    'cntr': 'research_visits', 'view': 'research_visit_details',
                                    'display': db.research_visit.title,
                                    'url_args': [db.research_visit.id],
                                    'status': db.research_visit.admin_status,
                                    'header': 'Research visits'},
                       'volunteer':{'query': (db.help_offered.user_id == auth.user.id),
                                    'select': [db.help_offered.id, db.help_offered.statement_of_interests, db.help_offered.admin_status],
                                    'none': 'You have not created any offers to volunteer at SAFE',
                                    'cntr': 'marketplace', 'view': 'volunteer_details',
                                    'display': db.help_offered.statement_of_interests,
                                    'url_args': [db.help_offered.id],
                                    'status': db.help_offered.admin_status,
                                    'header': 'Volunteer offers'},
                       'request':  {'query': (db.help_request.user_id == auth.user.id),
                                    'select': [db.help_request.id, db.help_request.work_description, db.help_request.admin_status],
                                    'none': 'You have not created any requests for project help at SAFE',
                                    'cntr': 'marketplace', 'view': 'help_request_details',
                                    'display': db.help_request.work_description,
                                    'url_args': [db.help_request.id],
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
            rows = [TR(TD(A(r[v['display']], _href= URL(v['cntr'], v['view'], args=[r[x] for x in v['url_args']])),
                          _style='width:90%'),
                      TD(approval_icons[r[v['status']]]))
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
    active = 'projects'
    tabs.element('li[name=' + active + ']')['_class'] = 'active'
    content.element('#' + active)['_class'] += ' active'
    
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

# create a global dictionary of calendar IDs
calID = {'volunteers': 'k23sbip8av2nvv196n9kupj5ss@group.calendar.google.com',
         'help_request': 'fber8126s5pdgccm3k13s90q58@group.calendar.google.com',
         'booked_visits': 'rairu8u98scfb8cgn86qdrgtic@group.calendar.google.com'}


def post_event_to_google_calendar(event, calendarId):
    
    """
    Function to post an event to a calendar and return event details.
    See:
    https://developers.google.com/api-client-library/python/auth/service-accounts
    """
    
    # we want the calendar API
    scopes = 'https://www.googleapis.com/auth/calendar'
    
    # Load the service account credentials
    # TODO -think about where to store this securely.
    cred_json = os.path.join(request.folder, 'private/google_auth/SAFE-project-website-6a272f141d5a.json')
    credentials = ServiceAccountCredentials.from_json_keyfile_name(cred_json, scopes)
    
    # authorise those credentials with Google
    http_auth = credentials.authorize(Http())
    
    # build the service handler
    service = build('calendar', 'v3', http=http_auth)
    
    # run the insert
    #try:
    event = service.events().insert(calendarId=calendarId, body=event).execute()
    # except AccessTokenRefreshError:
    #     # The AccessTokenRefreshError exception is raised if the credentials
    #     # have been revoked by the user or they have expired.
    #     print ('The credentials have been revoked or expired, please re-run'
    #            'the application to re-authorize')
    
    return event


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


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()
