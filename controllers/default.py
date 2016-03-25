# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import datetime
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


# def wiki():
#
#     return auth.wiki()

def concept():
    
    return response.render()


def funders():
    
    return response.render()


def calendars():
    
    return response.render()


def ecological_monitoring():
    
    return response.render()


def todo():
    
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


