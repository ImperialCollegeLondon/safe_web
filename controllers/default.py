# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import datetime
import dateutil.parser
import requests
# from collections import Counter


## -----------------------------------------------------------------------------
## Used to access the Google Calendar API
## -----------------------------------------------------------------------------

from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from apiclient.discovery import build

## -----------------------------------------------------------------------------
## Static page controllers
## -----------------------------------------------------------------------------

def index():
    """
    example action using the internationalization operator T and flash
    rendered by views/default/index.html or views/generic.html
    """
    
    return dict(message=T('Welcome to web2py!'))

def todo():
    
    return response.render()

# def wiki():
#
#     return auth.wiki()


@auth.requires_login()
def my_safe():
    
    """
    This controller presents a simple set of grids showing projects, outputs
    visits, reservations, blogs that a user is associated with.
    """
    table = request.vars['set']
    
    # default view
    if table is None:
        table = 'project'
    
    # provide a look up of which tables and columns to query
    membership_dict = {'project': {'tab':'project_members', 'col':'project_id',
                                   'fld': ['title'], 'name': 'projects',
                                   'cntr': 'projects', 'view': 'project_details'},
                       'outputs': {'tab':'outputs', 'col':'id',
                                   'fld': ['title'], 'name': 'outputs',
                                   'cntr': 'outputs', 'view': 'output_details'},
                       'research_visit': {'tab':'research_visit_member', 'col':'research_visit_id',
                                   'fld': ['title'], 'name': 'research visits',
                                   'cntr': 'research_visits', 'view': 'research_visit_details'},
                       'bed_reservations': {'tab':'bed_reservation_member', 'col':'bed_reservation_id',
                                   'fld': ['purpose'], 'name': 'bed reservations',
                                   'cntr': 'bed_reservations', 'view': 'bed_reservation_details'},
                       'blog_posts': {'tab':'blog_posts', 'col':'id',
                                   'fld': ['title'], 'name': 'blog posts',
                                   'cntr': 'blog', 'view': 'blog_details'}}
    
    # Is the requested set in the defined set
    if table in membership_dict.keys():
        
        m = membership_dict[table]
        
        # get the set of item ids that the user is a member of 
        # currently showing all statuses but could restrict
        valid_ids = db(db[m['tab']].user_id == auth.user.id)._select(m['col'])
        # query = ((db[table].id.belongs(valid_ids)) &
        #          (db[table].admin_status.belongs(['Approved', 'Pending'])))
        query = (db[table].id.belongs(valid_ids)) 
        
        if db(query).count() > 0:
            
            # get the grid display fields
            flds = [db[table][f] for f in m['fld']]
            flds.append(db[table]['admin_status'])
            db[table]['admin_status'].readable = False
            
            # create the links to the standalone controllers
            links = [dict(header = '', 
                          body = lambda row: A(SPAN('',_class="glyphicon glyphicon-zoom-in"),
                                      SPAN('View', _class="buttontext button"),
                                      _class="button btn btn-default", 
                                      _href=URL(m['cntr'], m['view'], args=[row.id], user_signature=True),
                                      _style='padding: 3px 5px 3px 5px;')),
                     dict(header = '', 
                          body = lambda row: approval_icons[row.admin_status])]
            
            grid = SQLFORM.grid(query, fields=flds,
                                csv=False, create=False, 
                                editable=False, deletable=False,
                                details = False, maxtextlength=200,
                                searchable=False,
                                # links_placement='left',
                                links=links)
        else:
            grid = B(CENTER('You are not a member of any {}'.format(m['name'])))
    else:
            grid = XML('Invalid table id')
    
    return dict(grid = grid )
    

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


