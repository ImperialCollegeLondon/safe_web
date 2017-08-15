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
        (T('Home'), True, URL('default', 'index'), []),
        (T('Concept'), True, URL('info', 'concept'), []),
        (T('The Project design'), True, URL('info', 'design'), []),
        (T('Research areas'), True, URL('info', 'research_areas'), []),
        (T('Contacts'), True, URL('people', 'contacts'), []),
        (T('Researchers'), True, URL('people', 'users'), []),
        (T('Funding and support'), True, URL('info', 'funders'), [])
    ]),
    (T('From the field'), True, None, [
        (T('Research Projects'), True, URL('projects', 'projects'), []),
        (T('News'), True, URL('news', 'news'), []),
        (T('Blog'), True, URL('blogs', 'blogs'), []),
        (T('Species profiles'), True, URL('species', 'species'), []),
        (T('Outputs'), True, URL('outputs', 'outputs'), []),
        (T('Datasets'), True, URL('datasets', 'view_datasets'), []),
        (T('SAFE Newsletter'), True, URL('info', 'newsletter'), []),
    ]),
    (T('Working at SAFE'), True, None, [
        (T('Overview'), True, URL('info', 'steps_to_follow'), []),
        (T('Register as a new user'), True, URL('user', 'register'), []),
        (T('Research Requirements'), True, URL('info', 'requirements'), []),
        (T('Data policy'), True, URL('info', 'data_policy'), []),
        (T('Research proposals'), True, URL('info', 'submitting_proposals'), []),
        (T('Logistics and costs'), True, URL('info', 'logistics'), []),
        (T('Health and Safety'), True, URL('info', 'health_and_safety'), []),
        (T('Biosecurity'), True, URL('info', 'biosecurity'), []),
        (T('Gazetteer'), True, URL('info', 'gazetteer'), []),
        # (T('SAFE Calendars'), True, URL('info', 'calendars'), []),
        (A('FAQs and SAFE wiki', _href='https://www.safeproject.net/dokuwiki/start', _target='_blank'), False, None, []),
        (T('Bed availability at SAFE'), True, URL('research_visits', 'safe_bed_availability'), []),
        (T('SAFE Mailing list'), True, URL('info', 'mailing_list'), []),
        LI(_class="divider"),
        (T('Volunteers available'), True, URL('marketplace', 'volunteers'), []),
        (T('Vacancies'), True, URL('marketplace', 'help_requests'), []),
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
                (T('View research visits'), True, URL('research_visits', 'research_visits'), []),
                (T('Discussion board'), True, URL('discussion', 'discussion_board'), []),
                LI(_class="divider"),
                (T('Propose a project'), True, URL('projects', 'project_details'), []),
                (T('Submit a new output'), True, URL('outputs', 'output_details'), []),
                (T('Propose a research visit'), True, URL('research_visits', 'research_visit_details'), []),
                (T('Volunteer at SAFE'), True, URL('marketplace', 'volunteer_details'), []),
                (T('Submit a dataset'), True, URL('datasets', 'submit_dataset'), []),
                (T('Advertise Vacancy'), True, URL('marketplace', 'help_request_details'), []),
                (T('Create a blog post'), True,URL('blogs', 'blog_details'),[]),
                LI(_class="divider"),
                (T('Request to join web group'), True, URL('groups', 'group_request'), []),
               ])]


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
          'prj': db.project_details.admin_status,
          'out': db.outputs.admin_status,
          'vol': db.help_offered.admin_status,
          'blg': db.blog_posts.admin_status,
          'hlp': db.help_request.admin_status,
          'usr': db.auth_user.registration_key
         }

n= {}
badge_class = {}
for key, field in n_dict.iteritems():
    # auth_user uses 'pending' as part of built in mechanisms, others are status values
    n[key] = db(field.belongs(['Pending', 'pending', 'Submitted', 'In Review'])).count()
    badge_class[key] = 'label badge-danger' if n[key] == 0 else 'label label-danger'

# datasets don't quite work the same - need to tell admin about passed datasets that have
# not been submitted or where submit failed
n['dat'] = db((db.datasets.dataset_check_outcome == 'PASS') &
              ((db.datasets.zenodo_submission_status == None) or 
               (db.datasets.zenodo_submission_status != 'Published'))).count()
badge_class['dat'] = 'label badge-danger' if n['dat'] == 0 else 'label label-danger'

if (auth.user_id != None) and (auth.has_membership(role = 'admin')):
    response.menu += [('Admin',  False,  None, [
                        (T('Manage users'), True, URL('people', 'manage_users'), []),
                        (T('Manage contacts'), True, URL('people', 'manage_contacts'), []),
                        (T('Manage news'), True, URL('news', 'manage_news'), []),
                        (T('Manage blogs'), True, URL('blogs', 'manage_blogs'), []),
                        (T('Health and safety info'), True, URL('health_safety', 'admin_view_health_and_safety'), []),
                        (T('Public holidays'), True, URL('info', 'public_holidays'), []),
                        (T('Create research visit'), True, URL('research_visits', 'create_late_research_visit'), []),
                        LI(_class="divider"),
                        (B('Approvals'), False, None, None),
                        (CAT(SPAN(n['usr'], _class=badge_class['usr']),
                             T('  New users')), True, URL('people', 'administer_new_users'), []),
                        (CAT(SPAN(n['grp'], _class=badge_class['grp']),
                             T('  New group requests')), True, URL('groups', 'administer_group_requests'), []),
                        (CAT(SPAN(n['prj'], _class=badge_class['prj']),
                             T('  Project proposals')), True, URL('projects', 'administer_projects'), []),
                        (CAT(SPAN(n['out'], _class=badge_class['out']),
                             T('  New outputs')), True, URL('outputs', 'administer_outputs'), []),
                        (CAT(SPAN(n['dat'], _class=badge_class['dat']),
                             T('  New datasets')), True, URL('datasets', 'administer_datasets'), []),
                        (CAT(SPAN(n['vis'], _class=badge_class['vis']),
                             T('  Research visits')), True,
                             URL('research_visits', 'administer_research_visits'), []),
                        (CAT(SPAN(n['blg'], _class=badge_class['blg']),
                             T('  Blog posts')), True, URL('blogs', 'administer_blogs'), []),
                        (CAT(SPAN(n['vol'], _class=badge_class['vol']),
                             T('  Volunteers')), True, URL('marketplace', 'administer_volunteers'), []),
                        (CAT(SPAN(n['hlp'], _class=badge_class['hlp']),
                             T('  Help requests')), True, URL('marketplace', 'administer_help_requests'), []),
                        LI(_class="divider"),
                        (T('Impersonate another user'), True, URL('user', 'impersonate')),
                        (T('Email failures'), True, URL('scheduler', 'email_failures')),
                        (T('Check scheduler tasks'), True, URL('scheduler', 'check_task_queue')),
                        (T('Database admin'), True, URL('appadmin', 'index'))
                      ])]

if "auth" in locals(): auth.wikimenu()
