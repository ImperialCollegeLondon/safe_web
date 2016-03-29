# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## Customize your APP title, subtitle and menus here
#########################################################################

# response.logo = A(B('web',SPAN(2),'py'),XML('&trade;&nbsp;'),
#                   _class="navbar-brand",_href="http://www.web2py.com/",
#                   _id="web2py-logo")
response.title = request.application.replace('_',' ').title()
response.subtitle = ''

## read more at http://dev.w3.org/html5/markup/meta.name.html
response.meta.author = 'David Orme <d.orme@imperial.ac.uk>'
response.meta.description = 'Information and administration for the SAFE project'
response.meta.keywords = 'Ecology'
response.meta.generator = 'Web2py Web Framework'

## your http://google.com/analytics id
response.google_analytics_id = None

## ----------------------------------------------------------------------------
## MAIN MENU STRUCTURE
## ----------------------------------------------------------------------------

response.menu = [
    (T('About'), True, None, [
        (T('Concept'), True, URL('default', 'concept'), []),
        (T('Ecological Monitoring'), True, URL('default', 'ecological_monitoring'), []),
        (T('Contacts'), True, URL('people', 'contacts'), []),
        (T('The Project design'), True, URL('default', 'todo'), []),
        (T('Funding and support'), True, URL('default', 'funders'), [])
    ]),
    (T('From the field'), True, None, [
        (T('Research Projects'), True, URL('projects', 'projects'), []),
        (T('News'), True, URL('news', 'news'), []),
        (T('Blog'), True, URL('blog', 'blogs'), []),
        (T('Species profiles'), True, URL('species', 'species'), []),
        (T('Outputs'), True, URL('outputs', 'outputs'), []),
    ]),
    (T('Research planning information'), True, None, [
        (T('FAQs and SAFE wiki'), True, 'http://forestecology.net/dokuwiki/safe/start', []),
        (T('Research Requirements'), True, URL('default', 'todo'), []),
        (T('Health and Safety'), True, URL('default', 'todo'), []),
        (T('SAFE Calendars'), True, URL('default', 'calendars'), []),
        (T('Permits'), True, URL('default', 'todo'), []),
        (T('Costs'), True, URL('default', 'todo'), []),
        (T('Bed availability'), True, URL('bed_reservations', 'bed_availability'), []),
        LI(_class="divider"),
        (T('Volunteers available'), True, URL('marketplace', 'volunteers'), []),
        (T('Help sought at SAFE'), True, URL('marketplace', 'help_requests'), []),
    ]),
    ]

## ----------------------------------------------------------------------------
## REGISTERED USER MENU
## -- adds an extra chunk to a menu for actions that require login. 
## -- Note that this basically just obfuscates the link, so the controllers
##    for these links also need login decorators
## -- having to use indexes to extend is a bit brittle, but hey.
## ----------------------------------------------------------------------------

user_actions = [(T('Registered users'), True, None, [
                (T('User directory'), True, URL('people', 'users'), []),
                (T('View research visits'), True, URL('research_visits', 'research_visits'), []),
                (T('My SAFE'), True, URL('default', 'my_safe'), []),
                (T('My health and safety info'), True, URL('health_safety', 'health_and_safety'), []),
                LI(_class="divider"),
                (T('Propose a project'), True, URL('projects', 'new_project'), []),
                # (T('Manage project members'), True, URL('projects', 'manage_project_members'), []),
                (T('Submit a new output'), True, URL('outputs', 'new_output'), []),
                (T('Add an output to a project'), True, URL('outputs', 'add_output_to_project'), []),
                (T('Propose a research visit'), True, URL('research_visits', 'new_research_visit'), []),
                (T('Reserve bed space'), True, URL('bed_reservations', 'reserve_beds'), []),
                (T('Volunteer at SAFE'), True, URL('marketplace', 'new_volunteer'), []),
                (T('Request project help'), True, URL('marketplace', 'new_help_request'), []),
               ])]

if (auth.user_id != None):
    response.menu += user_actions

## ----------------------------------------------------------------------------
## ADMIN MENU
## -- creates a new menu accessing admin tasks and shows how many need doing
## -- Note that this basically just obfuscates the link, so the controllers
##    for these links also need admin decorators to restrict access
## ----------------------------------------------------------------------------

n_dict = {'bed': db.bed_reservations.admin_status,
          'vis': db.research_visit.admin_status,
          'proj': db.project.admin_status,
          'output': db.outputs.admin_status,
          'vol': db.help_offered.admin_status,
          'help': db.help_request.admin_status,
          'new_users': db.auth_user.registration_key
         }

for key, field in n_dict.iteritems():
    
    n = db(field.belongs(['Pending', 'pending'])).count() # auth_user uses 'pending' as part of built in mechanisms
    if n > 0:
        n_dict[key] = ' (' + str(n) + ')'
    else:
        n_dict[key] = ''

if (auth.user_id != None) and (auth.has_membership(role = 'admin')):
    response.menu += [('Admin',  False,  None, [
                        (T('Manage users'), True, URL('people', 'manage_users'), []),
                        (T('Manage contacts'), True, URL('people', 'manage_contacts'), []),
                        (T('Manage bed reservations'), True, URL('bed_reservations', 'manage_bed_reservations'), []),
                        (T('Add news'), True, URL('news', 'new_news_post'), []),
                        (T('Add species'), True, URL('species', 'new_species'), []),
                        LI(_class="divider"),
                        (B('Approvals'), False, None, None),
                        (T('> New users') + n_dict['new_users'], True, URL('people', 'administer_new_users'), []),
                        (T('> New projects') + n_dict['proj'], True, URL('projects', 'administer_new_projects'), []),
                        (T('> New outputs') + n_dict['output'], True, URL('outputs', 'administer_outputs'), []),
                        (T('> Research visits') + n_dict['vis'], True, URL('research_visits', 'administer_new_research_visits'), []),
                        (T('> Bed reservations') + n_dict['bed'], True, URL('bed_reservations', 'administer_reserve_beds'), []),
                        (T('> Volunteers') + n_dict['vol'], True, URL('marketplace', 'administer_volunteers'), []),
                        (T('> Help requests' + n_dict['help']), True, URL('marketplace', 'administer_help_requests'), []),
                        LI(_class="divider"),
                        (T('Database admin'), True, URL('appadmin', 'index'))
                      ])]

if "auth" in locals(): auth.wikimenu() 
