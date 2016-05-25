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
        (T('Concept'), True, URL('info', 'concept'), []),
        (T('Ecological Monitoring'), True, URL('info', 'ecological_monitoring'), []),
        (T('Contacts'), True, URL('people', 'contacts'), []),
        (T('The Project design'), True, URL('info', 'design'), []),
        (T('Funding and support'), True, URL('info', 'funders'), [])
    ]),
    (T('From the field'), True, None, [
        (T('Research Projects'), True, URL('projects', 'projects'), []),
        (T('News'), True, URL('news', 'news'), []),
        (T('Blog'), True, URL('blog', 'blogs'), []),
        (T('Species profiles'), True, URL('species', 'species'), []),
        (T('Outputs'), True, URL('outputs', 'outputs'), []),
        (T('SAFE Newsletter'), True, URL('info', 'newsletter'), []),
        (T('SAFE Mailing list'), True, URL('info', 'mailing_list'), []),
    ]),
    (T('Working at SAFE'), True, None, [
        (T('Overview'), True, URL('info', 'steps_to_follow'), []),
        (T('Research Requirements'), True, URL('info', 'requirements'), []),
        (T('Submitting proposals'), True, URL('info', 'submitting_proposals'), []),
        (T('Biosecurity'), True, URL('info', 'biosecurity'), []),
        (T('Health and Safety'), True, URL('info', 'health_and_safety'), []),
        (T('Data policy'), True, URL('info', 'data_policy'), []),
        (T('SAFE Calendars'), True, URL('info', 'calendars'), []),
        (T('Logistics and costs'), True, URL('info', 'logistics'), []),
        (A('FAQs and SAFE wiki', _href='http://beta.safeproject.net/dokuwiki/start', _target='_blank'), False, None, []),
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
                (T('My SAFE Project'), True, URL('default', 'my_safe'), []),
                (T('My health and safety info'), True, URL('health_safety', 'health_and_safety'), []),
                (T('User directory'), True, URL('people', 'users'), []),
                (T('View research visits'), True, URL('research_visits', 'research_visits'), []),
                (T('Discussion board'), True, URL('discussion', 'discussion_board'), []),
                LI(_class="divider"),
                (T('Propose a project'), True, URL('projects', 'project_details'), []),
                (T('Submit a new output'), True, URL('outputs', 'output_details'), []),
                (T('Propose a research visit'), True, URL('research_visits', 'research_visit_details'), []),
                (T('Make reservation at SAFE'), True, URL('bed_reservations', 'reserve_beds'), []),
                (T('Volunteer at SAFE'), True, URL('marketplace', 'new_volunteer'), []),
                (T('Request project help'), True, URL('marketplace', 'new_help_request'), []),
                LI(_class="divider"),
                (T('Request to join web group'), True, URL('groups', 'group_request'), []),
               ])]


if auth.has_membership('bloggers'):
    user_actions[0][3].append((T('Create a blog post'), True,URL('blog', 'blog_details'),[]))

if auth.has_membership('species_profiler'):
    user_actions[0][3].append((T('Manage species profiles'), True,URL('species', 'manage_species'),[]))

if auth.is_logged_in():
    response.menu += user_actions

## ----------------------------------------------------------------------------
## ADMIN MENU
## -- creates a new menu accessing admin tasks and shows how many need doing
## -- Note that this basically just obfuscates the link, so the controllers
##    for these links also need admin decorators to restrict access
## ----------------------------------------------------------------------------

n_dict = {'grp': db.group_request.admin_status,
          'vis': db.research_visit.admin_status,
          'proj': db.project.admin_status,
          'output': db.outputs.admin_status,
          'vol': db.help_offered.admin_status,
          'blog': db.blog_posts.admin_status,
          'help': db.help_request.admin_status,
          'new_users': db.auth_user.registration_key
         }

for key, field in n_dict.iteritems():
    
    n = db(field.belongs(['Pending', 'pending', 'In Review'])).count() # auth_user uses 'pending' as part of built in mechanisms
    if n > 0:
        n_dict[key] = ' (' + str(n) + ')'
    else:
        n_dict[key] = ''

if (auth.user_id != None) and (auth.has_membership(role = 'admin')):
    response.menu += [('Admin',  False,  None, [
                        (T('Manage users'), True, URL('people', 'manage_users'), []),
                        (T('Manage contacts'), True, URL('people', 'manage_contacts'), []),
                        (T('Manage news'), True, URL('news', 'manage_news'), []),
                        (T('Manage blogs'), True, URL('blog', 'manage_blogs'), []),
                        LI(_class="divider"),
                        (B('Approvals'), False, None, None),
                        (T('> New users') + n_dict['new_users'], True, URL('people', 'administer_new_users'), []),
                        (T('> New group requests') + n_dict['grp'], True, URL('groups', 'administer_group_requests'), []),
                        (T('> Project proposals') + n_dict['proj'], True, URL('projects', 'administer_projects'), []),
                        (T('> New outputs') + n_dict['output'], True, URL('outputs', 'administer_outputs'), []),
                        (T('> Research visits') + n_dict['vis'], True, URL('research_visits', 'research_visits', 
                                          vars=dict(keywords = 'research_visit.admin_status = "Pending"')), []),
                        (T('> Blog posts') + n_dict['blog'], True, URL('blog', 'administer_blogs'), []),
                        (T('> Volunteers') + n_dict['vol'], True, URL('marketplace', 'administer_volunteers'), []),
                        (T('> Help requests' + n_dict['help']), True, URL('marketplace', 'administer_help_requests'), []),
                        LI(_class="divider"),
                        (T('Database admin'), True, URL('appadmin', 'index'))
                      ])]

if "auth" in locals(): auth.wikimenu() 
