import datetime
import uuid

## -----------------------------------------------------------------------------
## PROJECT CONTROLLERS
## - the project system requires the ability to revise projects both for initial 
##   approval and for any later edits. The underlying database needs permanent ID
##   numbers (and paired UUIDs for the Earthcape database), so we have the concept
##   of a permanent record of authority and a set of revisions. 
## - These controllers implement that via two tables 
##   A) A project_details table, which stores all revisions and from which project 
##      coordinators can submit a proposal.
## - B) A project_id table, which just holds the permanent ids and a link to the
##      current version of the project details table.
## - The two tables are connected by project_details.id = project_id.project_details_id. 
##   When a project is first created, a row is created in project_id to create the
##   permanent ID record.
## -----------------------------------------------------------------------------



## -----------------------------------------------------------------------------
## PUBLIC CONTROLLERS
## - presents a grid view of approved projects and a simple view of the current
##   details for that project
## -----------------------------------------------------------------------------

def projects():
    
    """
    This public controller shows the grid view for projects and allows
    users to look at project details but creating new ones is handled
    by a standalone form
    
    It uses a custom button to divert from the SQLFORM.grid view to a
    custom view page that displays project members and outputs as well
    """
    
    # For standard users (need a separate admin projects controller)
    # don't show the authorization fields and don't show a few behind 
    # the scenes fields
    db.project_details.admin_status.readable = False 
    db.project_details.proposer_id.readable = False 
    db.project_details.proposal_date.readable = False 
    db.project_details.data_sharing.readable = False 
    db.project_details.legacy_project_id.readable = False 
    
    # hide thumbnail_figure link - we need it in the fields, to use it in the links
    # but we don't want to show the field itself
    db.project_details.thumbnail_figure.readable = False
    
    # create a links list that:
    # 1) displays a thumbnail of the  project image
    # 2) creates a custom button to pass the row id to a custom view 
    
    links = [dict(header = '', body = lambda row: IMG(_src = URL('static', 'images/default_thumbnails/missing_project.png') if row.project_details.thumbnail_figure in [None,''] else 
                                                             URL('default', 'download', args = row.project_details.thumbnail_figure),
                                                        _height = 100)),
             dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                       SPAN('View', _class="buttontext button"),
                                       _class="button btn btn-default", 
                                       _href=URL("projects","project_view", args=[row.project_id.id], user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;'))]
    
    # create a grid view on the join between project_id and project_details
    query = (db.project_id.project_details_id == db.project_details.id)
    
    form = SQLFORM.grid(db.project_id.project_details_id == db.project_details.id, csv=False, 
                        fields=[db.project_details.title,
                                db.project_details.start_date, 
                                # db.project_details.end_date, 
                                db.project_details.thumbnail_figure],
                        orderby = ~ db.project_details.start_date, 
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False, 
                        details=False,
                        links=links,
                        links_placement='left',
                        formargs={'showid': False}
                        )
    
    return dict(form=form)


def project_view():
    
    """
    Custom public project view - displays the project and any members or outputs
    """
    
    # retrieve the user id from the page arguments passed by the button
    project_id = request.args(0)
    
    # control access to records based on status
    project_record = db.project_id(project_id)
    
    # get the linked project details (there is only one)
    project_details = db.project_details(project_record.project_details_id)
    
    if (project_record is None) or (project_details.admin_status != 'Approved'):
    
        session.flash = CENTER(B('Invalid project id number.'), _style='color: red')
        redirect(URL('projects','projects'))
    
    else:
        
        # return a set of panels showing the content of the records links
        
        # build the view in controller and pass over to the view as a single object
        if project_details.thumbnail_figure in [None, '']:
            pic = URL('static', 'images/default_thumbnails/missing_project.png')
        else:
            pic = URL('default','download', args = project_details.thumbnail_figure)
        
        rationale = XML(project_details.rationale.replace('\n', '<br />'), sanitize=True, permitted_tags=['br/'])
        methods = XML(project_details.methods.replace('\n', '<br />'), sanitize=True, permitted_tags=['br/'])
        
        # project details panel
        project_details =   CAT(DIV(DIV(H4(project_details.title), _class='col-sm-10'),
                                    DIV(DIV(IMG(_src=pic, _width='100px'), _class= 'pull-right'), _class='col-sm-2'),
                                    _class='row', _style='margin:10px 10px;'), 
                                DIV(DIV('Project details', 
                                        A(SPAN('',_class="icon leftarrow icon-arrow-left glyphicon glyphicon-arrow-left"),
                                            SPAN(' Back to projects'),
                                            _href=URL("projects","projects", user_signature=True),
                                            _class='pull-right', _style='color:white'),
                                        _class="panel-heading"),
                                    DIV(DIV(DIV(H4('Start date') + project_details.start_date, _class='col-sm-3', 
                                                _style='padding-right:0; padding-left:0;'),
                                            DIV(H4('End date') + project_details.end_date, _class='col-sm-3',
                                                _style='padding-right:0; padding-left:0;'),
                                            DIV(H4('Research areas') + XML(('<br>').join(project_details.research_areas)), _class='col-sm-3',
                                                _style='padding-right:0; padding-left:0;'),
                                            DIV(H4('Data use') + XML(('<br>').join(project_details.data_use)), _class='col-sm-3',
                                                _style='padding-right:0; padding-left:0;'),
                                            _class='row'),
                                        DIV(H4('Rationale') + rationale, _class='row'),
                                        DIV(H4('Methods') + methods, _class='row'),
                                    _class='panel-body', _style='margin:10px 10px'),
                                DIV(_class='panel-footer'),
                                _class="panel panel-primary"))
        
        # members panel
        members_table = TABLE(TR(TH('Researcher'), TH('Project role'), TH('Project contact')),
                              *[TR(TD(A(r.user_id.first_name + " " + r.user_id.last_name, 
                                        _href=URL('people','user_details', args=[r.user_id]))),
                                   TD(r.project_role),
                                   TD(coordinator_icon if r.is_coordinator else not_coordinator_icon)) 
                                   for r in project_record.project_members.select()],
                              _class='table table-striped', _style='width:100%')

        members = DIV(DIV('Project members', _class="panel-heading"),
                      members_table,
                      DIV(_class='panel-footer'),
                      _class="panel panel-primary")

        # outputs panel
        outputs = project_record.project_outputs.select()
        
        if len(outputs) > 0:
            outputs_table = TABLE(TR(TH('Output title'), TH('Output type')),
                                  *[TR(TD(A(r.output_id.title, 
                                            _href=URL('outputs','view_output', args=[r.output_id]))),
                                       TD(r.output_id.format))
                                       for r in outputs],
                                  _class='table table-striped', _style='width:100%')

            outputs = DIV(DIV('Project outputs', _class="panel-heading"),
                          outputs_table,
                          DIV(_class='panel-footer'),
                          _class="panel panel-primary")
        else:
            outputs = DIV()
        
        # project links
        project_link_id = db(db.project_link_pairs.project_id == project_id)._select(db.project_link_pairs.link_id)
        
        project_query = db((db.project_link_pairs.link_id.belongs(project_link_id)) &
                           (db.project_link_pairs.project_id == db.project_id.id) &
                           (db.project_id.id != project_id) &
                           (db.project_id.id == db.project_details.project_id))
        
        project_rows = project_query.select(db.project_details.project_id, 
                                            db.project_details.version, 
                                            db.project_details.title)
        
        if len(project_rows) > 0:
            
            for r in project_rows:
                project_links = DIV(DIV('Linked projects', _class="panel-heading"),
                                    TABLE(*[TR(TD(A(r.title, 
                                                    _href=URL('projects','project_view', 
                                                              args=[r.project_id]))))
                                               for r in project_rows],
                                          _class='table table-striped', _style='width:100%'),
                                    DIV(_class='panel-footer'),
                                    _class="panel panel-primary")
        else:
            
            project_links = DIV()
    
    # pass components to the view
    return dict(project_id = project_id, project_details = project_details,
                members = members, outputs=outputs, project_links = project_links)


## -----------------------------------------------------------------------------
## PROJECT DETAIL CONTROLLERS
## -- DESIGN NOTES: A project can be created by a single user, who is automatically
##                  added as a project member and coordinator. Once a new project
##                  is created via a form accept then the view is refreshed to add 
##                  a project members view.
##                  
##                  The view for this controller contains a lot of code to provide
##                  a single URL for a project that can expose either an editing
##                  interface or a detailed record for oversight
##                  
## -- TODO - extend new_project to require non-student status?
## -----------------------------------------------------------------------------

@auth.requires_login()
def project_details():

    """
    Controller to handle the management of project details. This needs to be a 
    form that users can return to to fix problems etc, so this controller accepts project_id
    as an argument to reload existing records and project_details_id to allow access to
    different versions.
    
    The controller also need access control to cover who has write access. For admin users,
    an admin panel is exposed to input decisions on submitted and in review proposal.
    
    The controller contains a lot of formatting code, to return simple units to the view
    for display, rather than having a lot of logic in {{}} in the view html.
    """
    
    # two possible arguments - the project id and the version of that project
    project_id = request.args(0)
    version_id = request.args(1)

    # look for an existing record, otherwise a fresh start with an empty record
    if project_id is not None:
        # get the row for the project id, which contains the set of all
        # project_details records through referencing and the link to the current
        # canonical one
        project_record = db.project_id(project_id)
    else:
        # brand new proposal for a new project, so no record
        project_record = None
    
    # need access control here for existing projects and provide:
    # - default readonly access to all users to allow project oversight.
    # - but give write access to project coordinator members
    
    # There are four combinations we want to handle:
    # - New project: edit mode, save new draft option
    # - Editing draft: edit mode, save draft and submit draft options 
    # - New draft: view mode, new draft option
    # - View mode: view mode, no options.
    
    # The SQL readonly option turns off all field writing, but also suppresses buttons used to
    # provide options, so gives view mode only. The other options could be achieved by
    # turning off field writable for each field, but we want pretty looking edit and view modes, 
    # so create two distinct FORM views (edit, view) and use readonly to suppress the buttons.
    
    if project_id is not None and project_record is None:
        
        # avoid unknown project id
        session.flash = B(CENTER('Invalid project id'), _style='color:red;')
        redirect(URL('projects','projects'))
        
    else:
        
        # Now set up for new projects versus existing projects 
        if project_id is not None:
            
            # A) need to handle versions of existing project details - multiple records for the same
            # project id. First get a dictionary of valid version numbers
            versions = project_record.project_details.select(orderby=db.project_details.version)
            version_num = [str(v.version) for v in versions]
            version_date = [v.proposal_date.strftime('%Y-%m-%d %H:%M') for v in versions]
            version_detail_id = [v.id for v in versions]
            version_dict = dict(zip(version_num, version_detail_id))
            
            # If there isn't a version number provided, then redirect to load the record for the
            # one linked in the projects_id table, which is the most recently approved
            if version_id is None:
                linked_version = db.project_details(project_record.project_details_id).version
                redirect(URL('projects','project_details', args=[project_id, linked_version]))
            else:
                # otherwise we load the version referenced by the version number
                if version_id not in version_num:
                    # avoid unknown version id
                    session.flash = B(CENTER('Invalid project version id'), _style='color:red;')
                    redirect(URL('projects','projects'))
                else:
                    # lookup the details row for that version
                    details = db.project_details(version_dict[version_id])
        
            # Create a bootstrap dropdown to allow users to select different versions
            # - needs a dictionary of arguments to the TAG.button, because of the hyphen
            #   in data-toggle 
            version_links = []
            version_string = []
            
            # two icons to show which version is currently being looked at - one is just
            # a glyphicon class with a minimum width to align the text that follows
            this_icon = SPAN(_class='glyphicon glyphicon-ok-sign', _style='min-width:15px')
            other_icon = SPAN(_class='glyphicon',_style='min-width:15px')
            
            for n, d in zip(version_num, version_date):
                if n == version_id:
                    this_version = CAT(this_icon, '  Version ' + n + " (" + d + ")")
                    version_string.append(this_version)
                else:
                    version_string.append(CAT(other_icon, '  Version ' + n + " (" + d + ")"))
                
                version_links.append(URL('projects','project_details', args=[project_id, n]))
            
            version_list = [LI(A(st, _href=ln)) for st, ln in zip(version_string, version_links)]
            
            version_dropdown = DIV(TAG.button(CAT(this_version , ' ', SPAN(_class="caret")),
                                              **{'_class': "btn btn-default dropdown-toggle", 
                                                 '_type': "button", 
                                                 '_id': "dropdownMenu1", 
                                                 '_data-toggle': "dropdown",
                                                 '_style': 'padding: 5px 15px 5px 15px;background-color:lightgrey;color:black'}),
                                              UL(*version_list, _class="dropdown-menu dropdown-menu-right"),
                                   _class="dropdown col-sm-3")
            
            status = DIV(approval_icons[details.admin_status], XML('&nbsp'),
                         'Status: ', XML('&nbsp'), details.admin_status, 
                         _class='col-sm-3',
                         _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            
            # B) now sort out what the mode and editability is
            
            # - get a list of coordinators that can edit this project
            project_coords = db((db.project_members.project_id == project_id) &
                                (db.project_members.is_coordinator == 'True')).select()
            project_coords = [r.user_id for r in project_coords]
            
            # Is this a version that could launch a new version?
            # - must be most recent version and could be Approved or Rejected
            if (auth.user.id in project_coords) & (int(version_id) == max([int(r) for r in version_num])) & (details.admin_status in ['Approved','Rejected']):
                launch_new_version = True
            else: 
                launch_new_version = False
            
            if auth.user.id in project_coords and details.admin_status in ['Draft', 'Resubmit']:
                # an active draft
                mode = 'edit'
                buttons = [TAG.button('Save draft',_type="submit", 
                                      _name='save_draft', _style='padding: 5px 15px 5px 15px;'), 
                           XML('&nbsp;')*5,
                           TAG.button('Save and Submit draft',_type="submit", 
                                      _name='submit_draft', _style='padding: 5px 15px 5px 15px;')]
                header_text = CAT(H2('Edit Project Draft'), 
                                   P('Please use the form below to edit your draft project proposal. You can save your changes by ',
                                     'clicking on the Save Draft button below'),
                                   P('Once you have completed your proposal, click the Save and Submit Draft button to submit your ',
                                     ' proposal. It will first be screened by an ',
                                     'administrator and then sent out to the research community at SAFE for comments. This process ',
                                     'usually takes about 14 days. You will get an email to confirm that you have submitted a project ',
                                     'and then another email to confirm whether the project has been accepted or not.'))
            elif auth.user.id in project_coords and launch_new_version:
                # able to create a new draft?
                mode = 'view'
                header_text = CAT(H2('Project details'), 
                                   P('The form below shows the most recent version of your project proposal. If you want to update ',
                                     'the project details or need to re-submit an updated version of a rejected proposal, then ',
                                     'click on the Edit New Draft button.'))

            else:
                # view only
                mode = 'view'
                header_text = CAT(H2('Project details'), 
                                   P('The form below shows the details of a project proposal submitted to SAFE. Note that proposals ',
                                     'cannot be edited once they have been submitted or are in review - you will have to wait for a', 
                                     'decision to be made before you can alter a proposal.'),
                                   P('You can add new project members to submitted project proposals both you and other project '
                                     'coordinators may add new project links.'))

        else:
            # otherwise, we're providing a blank form with only a save changes button, 
            # no pre-existing details and an empty DIV in place of the version dropdown
            # to create a new proposal
            mode = 'edit'
            buttons = [TAG.button('Save new draft',_type="submit", 
                                  _name='save_new', _style='padding: 5px 15px 5px 15px;')]
            version_dropdown = DIV(_class='col-sm-3')
            status = DIV(_class='col-sm-3')
            details = None
            version_dropdown = DIV()
            header_text = CAT(H2('New Project Submission'), 
                               P('Please use the form below to create a new draft research proposal. Once you save the new draft, '
                                 'you will be added as the main contact for the proposal and you will be able to add new project ',
                                 'members and identify linked projects.'))
        
        # NOW we setup the main form for edit mode
        panel_header = DIV(H5('Project details', _class='col-sm-6'),
                           status, version_dropdown,
                           _class='row', _style='margin:0px 0px')
        
        if mode == 'edit':
        
            form = SQLFORM(db.project_details, 
                           record = details, 
                           fields =  ['thumbnail_figure', 'title', 
                                      'research_areas', 'start_date', 'end_date', 'data_use',
                                      'rationale', 'methods', 'which_animal_taxa',
                                      'destructive_sampling','destructive_sampling_info',
                                      'ethics_approval_required','ethics_approval_details',
                                      'funding', 'data_sharing'],
                           buttons = buttons)
            
            # Process the form first to add hidden fields etc or to capture submitted values
            if form.process(onvalidation=validate_project_details, formname='details', session=session).accepted:
                
                # actions depend on whether this is a submission, a new project, an update
                if form.submit:
                    # i) update the history, change the status and redirect
                    hist_str = '[{}] {} {}\\n -- Proposal submitted\\n'
                    new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                               auth.user.first_name,
                                                               auth.user.last_name) + details.admin_history
                    
                    details.update_record(admin_status = 'Submitted',
                                          admin_history = new_history)
                    
                    # ii) email the proposer
                    SAFEmailer(to=auth.user.email,
                               subject='SAFE: project proposal submitted',
                               template =  'project_submitted.html',
                               template_dict = {'name': auth.user.first_name,
                                                'url': URL('projects', 'project_details', args=[project_id, version_id], scheme=True, host=True)})
                    
                    session.flash = CENTER(B('SAFE project proposal submitted.'), _style='color: green')
                    redirect(URL('projects', 'project_details', args=[project_id, version_id]))
                
                elif details is None:
                    # if a new project (no existing details) then:
                    # i) link to a new project_id
                    
                    new_details = db.project_details(form.vars.id)
                    project_id = db.project_id.insert(project_details_id = new_details.id)
                                                      
                    # ii) set it up as a Draft version and initialise the history
                    hist_str = '[{}] {} {}\\n -- New proposal created\\n'
                    new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                               auth.user.first_name,
                                                               auth.user.last_name)
                    
                    new_details.update_record(project_id = project_id, 
                                              version=1,
                                              admin_status='Draft',
                                              admin_history = new_history)
                    
                    # iii) add the proposer as the Main Contact for the project
                    db.project_members.insert(user_id = auth.user.id,
                                              project_id = project_id,
                                              project_role = 'Lead Researcher',
                                              is_coordinator = True)
                    
                    # iv) email the proposer
                    SAFEmailer(to=auth.user.email,
                               subject='SAFE: draft project proposal created',
                               template =  'project_draft_created.html',
                               template_dict = {'name': auth.user.first_name,
                                                'url': URL('projects', 'project_details', args=[project_id, 1], scheme=True, host=True)})
                    
                    # signal success and load the newly created record in a details page
                    session.flash = CENTER(B('SAFE project draft created.'), _style='color: green')
                    redirect(URL('projects', 'project_details', args=[project_id, 1]))
                else:
                    # i) update the history
                    hist_str = '[{}] {} {}\\n -- Proposal updated\\n'
                    new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                               auth.user.first_name,
                                                               auth.user.last_name) + details.admin_history
                    
                    details.update_record(admin_history = new_history)
                    
                    # Just edits submitted via the save draft button so send a signal success 
                    session.flash = CENTER(B('SAFE project proposal updated.'), _style='color: green')
                    redirect(URL('projects', 'project_details', args=[project_id, version_id]))
            
            elif form.errors:
                response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
            else:
                # this runs when the form is being set up, so process has added
                # the formkey and formname now
                pass
            
            # Now create the edit panel
            # - first edit some of the settings for the widgets
            form.custom.widget.ethics_approval_details['_rows'] = 4
            form.custom.widget.destructive_sampling_info['_rows'] = 2
            form.custom.widget.rationale['_rows'] = 4
            form.custom.widget.methods['_rows'] = 4
            form.custom.widget.research_areas['_size'] = 3
            form.custom.widget.start_date['_class'] = "form-control input-sm"
            form.custom.widget.end_date['_class'] = "form-control input-sm"
            
            # thumbnail_figure
            if (details is None) or (details.thumbnail_figure in [None, '']):
                pic = URL('static', 'images/default_thumbnails/missing_project.png')
            else:
                pic = URL('default','download', args = details.thumbnail_figure)
            
            # - now package the widgets
            form = CAT(form.custom.begin, 
                        DIV(DIV(panel_header,
                                _class="panel-heading"),
                            DIV(DIV(DIV(IMG(_src=pic, _height='100px'), _class='col-sm-2'),
                                    DIV(DIV(LABEL('Project title:', _class="control-label col-sm-2" ),
                                            DIV(form.custom.widget.title,  _class="col-sm-10"),
                                            _class='row'),
                                        DIV(LABEL('Picture:', _class="control-label col-sm-2" ),
                                            DIV(form.custom.widget.thumbnail_figure,  _class="col-sm-10"),
                                            _class='row'),
                                        DIV(LABEL('Dates:', _class="control-label col-sm-2" ),
                                             DIV(DIV(form.custom.widget.start_date,
                                                     SPAN('to', _class="input-group-addon input-sm"),
                                                     form.custom.widget.end_date,
                                                     _class="input-daterange input-group", _id="proj_datepicker"),
                                                 _class='col-sm-10'),
                                             _class='row'),
                                        _class='col-sm-10'),
                                    _class='row', _style='margin:10px 10px'),
                              local_hr,
                                DIV(H4('Science case'), P('These sections set out the case for the research - what is the background ',
                                    'and the hypotheses - and the research methods to be used. You', B(' must '), 'provide a detailed ',
                                    'rationale and methods for your project before it can be sent out for comment. You must also choose ',
                                    'at least one research area classification from the list provided below and select at least one ',
                                    'data use option, showing what the project data will be used for.'),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(LABEL('Rationale:', _class="control-label col-sm-2" ),
                                    DIV(form.custom.widget.rationale,  _class="col-sm-10"),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(LABEL('Methods:', _class="control-label col-sm-2" ),
                                    DIV(form.custom.widget.methods,  _class="col-sm-10"),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(DIV(LABEL('Research areas:'), _class="col-sm-2"),
                                    DIV(form.custom.widget.research_areas,  _class="col-sm-4"),
                                    DIV(LABEL('Data use:'),_class="col-sm-2"),
                                    DIV(form.custom.widget.data_use,  _class="col-sm-4"),
                                    _class='row', _style='margin:10px 10px'),
                                local_hr,
                                DIV(H4('Destructive sampling'), P('Any research that kills or removes animals from the environment ',
                                        'or causes damage to the habitat by disturbing the soil or damaging vegetation is ',
                                      B('strictly monitored '), 'at SAFE. If you plan to perform destructive sampling as ',
                                        'part of your project, then check the box below. In the text box, you  ', B(' must '),
                                        'then: (1) describe the destructive sampling, (2) explain why it is necessary, and ',
                                        '(3) describe where you plan to carry out destructive sampling.'),
                                    _class='row', _style='margin:10px 10px;'),
                                DIV(DIV(LABEL(form.custom.widget.destructive_sampling, 'Destructive sampling required', _class="control-label"),
                                        form.custom.widget.destructive_sampling_info,
                                        _class="col-sm-12"),
                                    _class='row', _style='margin:10px 10px'),
                                local_hr,
                                DIV(H4('Animal research and ethics'), P('If your project involves working with animals you will need to check if ',
                                     'ethical approval is needed and provide details  of how you are obtaining approval. You must also indicate '
                                     'all animal groups you plan to work with from the list below:'),
                                    _class='row', _style='margin:10px 10px;'),
                                DIV(DIV(LABEL(form.custom.widget.ethics_approval_required, 'Ethics Approval required', _class="control-label"),
                                        DIV(form.custom.widget.ethics_approval_details),
                                        _class="col-sm-8" ),
                                    DIV(B('Animal taxa'), form.custom.widget.which_animal_taxa ,_class="col-sm-4"),
                                    _class='row', _style='margin:10px 10px'),
                                local_hr,
                                DIV(H4('Funding and data sharing'), P('The SAFE Project requires that you deposit a copy of any primary '
                                      'field data you collect in the SAFE central database, and to provide metadata for that data.'),
                                    _class='row', _style='margin:10px 10px;'),
                                DIV(DIV(LABEL(form.custom.widget.data_sharing, 'Check this box to confirm you agree to provide',
                                              ' your data to the SAFE project', _class="control-label"),
                                        _class="col-sm-12"),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(P('It is very important for us to show our funders the extent to which their investment has been leveraged ',
                                      'to support work beyond their central donation. If you have a grant to support this work or applying for ',
                                      'one, please give details of the grant title, funder, year of award and amount below:'),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(DIV(form.custom.widget.funding, _class="col-sm-12"),
                                    _class='row', _style='margin:10px 10px'),
                                local_hr,
                                DIV(form.custom.submit, _class='panel-footer'),
                                _class='panel_body'),
                            _class="panel panel-primary"),
                        form.custom.end,
                        datepicker_script(id = 'proj_datepicker',
                                          autoclose = 'true',
                                          startDate ='"+0d"',
                                          endDate ='"+365d"'))
        
        elif mode == 'view':
            
            # We just provide a panel of information populated from details
            # but also include a form with a single submit button to allow coordinators
            # to launch new drafts
            
            # package destuctive sampling if present
            if details.destructive_sampling:
                destruct =   DIV('This project ',B('involves destructive sampling'), '. The provided description is :', 
                                 DIV(details.destructive_sampling_info, _class='well'),
                                 _class='row', _style='margin:10px 10px;')
            else:
                destruct =   DIV('This project has not declared any destructive sampling.', 
                                 _class='row', _style='margin:10px 10px;')
            
            # package ethics
            if len(details.which_animal_taxa) > 0:
                animals =   P('This project will work with the following animal taxa: ' + ','.join(details.which_animal_taxa))
            else:
                animals = ''
            
            if details.ethics_approval_required:
                ethics = DIV('Ethical approval ',B('is required for this work'), ' and the following details have ',
                             'been provided:', DIV(details.ethics_approval_details, _class='well'), animals,
                              _class='row', _style='margin:10px 10px;')
            else:
                ethics = DIV(P('Ethical approval is not required for this work'), animals,
                             _class='row', _style='margin:10px 10px;')
            
            # thumbnail_figure
            if details.thumbnail_figure in [None, '']:
                pic = URL('static', 'images/default_thumbnails/missing_project.png')
            else:
                pic = URL('default','download', args = details.thumbnail_figure)
            
            # funding
            if details.funding in [None, '']:
                funds = P('This project has not provided any funding information.')
            else:
                funds = CAT(P('This project has provided the following funding information.'), DIV(details.funding, _class='well'))
            
            # build the form to look pretty in  view mode
            form =  FORM(DIV(DIV(panel_header,
                                _class="panel-heading"),
                            DIV(DIV(DIV(IMG(_src=pic, _height='100px'), _class='col-sm-2'),
                                    DIV(DIV(LABEL('Project title:', _class="control-label col-sm-2" ),
                                            DIV(details.title,  _class="col-sm-10"),
                                            _class='row'),
                                        DIV(LABEL('Start Date:', _class="control-label col-sm-2" ),
                                            DIV(details.start_date,  _class="col-sm-10"),
                                            _class='row'),
                                        DIV(LABEL('End Date:', _class="control-label col-sm-2" ),
                                            DIV(details.end_date,  _class="col-sm-10"),
                                            _class='row'), 
                                        _class='col-sm-10'),
                                    _class='row', _style='margin:10px 10px'),
                                local_hr,
                                DIV(H4('Science case'),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(LABEL('Rationale:', _class="control-label col-sm-2" ),
                                    DIV(details.rationale,  _class="col-sm-10"),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(LABEL('Methods:', _class="control-label col-sm-2" ),
                                    DIV(details.methods,  _class="col-sm-10"),
                                    _class='row', _style='margin:10px 10px'),
                                DIV(DIV(LABEL('Research areas:'), _class="col-sm-2"),
                                    DIV(XML(('<br>').join(details.research_areas)), _class="col-sm-4"),
                                    DIV(LABEL('Data use:'),_class="col-sm-2"),
                                    DIV(XML(('<br>').join(details.data_use)),  _class="col-sm-4"),
                                    _class='row', _style='margin:10px 10px'),
                                local_hr,
                                DIV(H4('Destructive sampling'), _class='row', _style='margin:10px 10px;'),
                                destruct,
                                local_hr,
                                DIV(H4('Animal research and ethics'), _class='row', _style='margin:10px 10px;'),
                                ethics,
                                local_hr,
                                DIV(H4('Funding and data sharing'), 
                                    P('The project coordinators ',B('have confirmed '), 'that this project will provide primary field data and metadata to the SAFE project.'),
                                    _class='row', _style='margin:10px 10px;'),
                                DIV(funds, _class='row', _style='margin:10px 10px'),
                                _class='panel_body'),
                            DIV(_class='panel-footer'),
                            _class="panel panel-primary"))
            
            # if the user has permission to relaunch a new draft insert a button and make it a form
            if launch_new_version:
                buttons = TAG.button('Edit new draft', _type="submit", _name='new_draft', _style='padding: 5px 15px 5px 15px;')
                form.elements('div.panel-footer')[0].insert(0,buttons)
            
            # very simple process for the view form (which can only do anything when the button is revealed)
            # Process the form first to add hidden fields etc or to capture submitted values
            if form.process(formname='launch_new_draft', session=session).accepted:
                
                # duplicate the details record into a new record
                new_draft_id = db.project_details.insert(**db.project_details._filter_fields(details))
                # update the history
                hist_str = '[{}] {} {}\\n -- New draft version created\\n'
                new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                              auth.user.first_name,
                                              auth.user.last_name) + details.admin_history
                
                # get the new record updated with the new status and version number
                db.project_details(new_draft_id).update_record(admin_status='Draft',
                                                               version=details.version + 1,
                                                               admin_history = new_history)
                                                               
                redirect(URL('projects', 'project_details', args=[project_id, details.version + 1]))
        
        # NOW PROVIDE FORMS TO ADD MEMBERS AND LINKS:
        
        # 1) PROVIDE A VIEW OF THE PROJECT MEMBERS if the project exists
        
        if project_id is not None:
            
            # get current members
            members = db(db.project_members.project_id == project_id).select()
            members_rows = [TR(TD(coordinator_icon if r.is_coordinator else not_coordinator_icon, _style='text-align:center'),
                               TD(A(r.user_id.last_name + ', ' + r.user_id.first_name, _href = URL('people','user_details', args=r.user_id))),
                               TD(r.project_role), TD()) for r in members]
            
            if auth.user.id in project_coords:
                
                # allow members to be added by coordinators from any version (don't need to have a draft)
                # - set the project id value for the member
                db.project_members.project_id.default = project_id
                
                # - create the form ...
                members = SQLFORM(db.project_members, fields=['user_id','project_role','is_coordinator', 'project_id'])
                
                # set the processing in order to setup hidden fields
                if members.process(onvalidation=validate_new_project_member, formname='members').accepted:
                    
                    # i) lookup the new member details to get a reference to auth and update the history
                    # and link the OIDs up 
                    new_member = db.project_members(members.vars.id)
                    
                    hist_str = '[{}] {} {}\\n -- Project members added/updated: {} {}, {} {}\\n'
                    new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                  auth.user.first_name,
                                                  auth.user.last_name,
                                                  new_member.user_id.first_name,
                                                  new_member.user_id.last_name,
                                                  members.vars.project_role,
                                                  'and Coordinator' if members.vars.is_coordinator else ''
                                                  ) + details.admin_history
                    
                    details.update_record(admin_history = new_history)
                    
                    session.flash = CENTER(B('Project members updated.'), _style='color: green')
                    redirect(URL('projects', 'project_details', args=[project_id, version_id]))
                    
                elif members.errors:
                    
                    response.flash = CENTER(B('Problem with adding project member.'), _style='color: red')
                    
                else:
                    pass
                
                # - ... and repackage it as a FORM around a panel
                # a) add the customform elements into a new row at the end
                #    We need to pass the project id value to the validation, but it can't be edited
                #    so hide it and bundle it in later
                members.custom.widget.project_id.attributes['_type'] = 'hidden'
                members_rows.append(TR(TD(members.custom.widget.is_coordinator, _style='text-align:center'),
                                      TD(members.custom.widget.user_id),
                                      TD(members.custom.widget.project_role),
                                      TD(TAG.BUTTON(add_member_icon,
                                                    _style='background:none; border:none;padding:0px 10px;font-size: 100%;',
                                                    _type="submit")),
                                         _style="vertical-align:centre"))
                
                # b) wrap everything up in the form
                members = CAT(members.custom.begin,
                              DIV(DIV(H5('Project members'), _class='panel-heading'),
                                   DIV('As you are a coordinator for this project, you can add new project members. You ',
                                       'can add members again to change their role and coordinator status. You cannot remove ',
                                       'your own coordinator status!', _class = 'panel-body'),
                                   TABLE(TR(TH('Coordinator', _style='text-align:center'),TH('Name'), TH('Project Role'), TH()),
                                         *members_rows,
                                         _width='100%', _class='table table-striped'),
                                   DIV(_class='panel-footer'),
                                   _class="panel panel-primary"),
                              members.custom.widget.project_id, # hidden field to pass over the information to the validation
                              members.custom.end)
            
            else:
                members = DIV(DIV(H5('Project members'), _class='panel-heading'),
                              TABLE(TR(TH('Coordinator', _style='text-align:center'),TH('Name'), TH('Project Role'), TH()),
                                    *members_rows,
                                    _width='100%', _class='table table-striped'),
                              DIV(_class='panel-footer'),
                              _class="panel panel-primary")
        else:
            # blank placeholder
            members = DIV()
        
        # 2) PROVIDE A VIEW OF THE PROJECT LINKS if the project exists
        
        if project_id is not None:
            
            # get current links joined all the way through to project_details - big complex join!
            link_ids = db(db.project_link_pairs.project_id == project_id)._select(db.project_link_pairs.link_id)
            
            links = db((db.project_links.id.belongs(link_ids)) &
                       (db.project_links.id == db.project_link_pairs.link_id) &
                       (db.project_id.id <> project_id) &
                       (db.project_link_pairs.project_id == db.project_id.id) &
                       (db.project_id.project_details_id == db.project_details.id))
            links = links.select(db.project_links.user_id, db.project_details.title,
                                 db.project_id.id, db.project_details.version)
            
            # look up project details and wrap them up into a table of links
            link_rows = [TR(TD(A(r.project_details.title, 
                                 _href = URL('projects','project_details', 
                                             args=[r.project_id.id, r.project_details.version]))),
                            TD(A(r.project_links.user_id.last_name + ', ' + r.project_links.user_id.first_name, 
                                 _href = URL('people','user_details', 
                                             args=r.project_links.user_id)))) 
                         for r in links]
            
            # now implement a mechanism for adding new links
            # - coordinators of _any_ project can add a link between their projects and this one
            # - admins and coordinators of _this_ project can link any other projects.
            if auth.has_membership('admin') or (auth.user.id in project_coords):
                
                linkable = db(db.project_id.project_details_id == db.project_details.id)
                linkable = linkable.select(db.project_details.title,
                                           db.project_id.id)
            else:
                
                # what projects is the user a coordinator for?
                coordinating = db((db.project_id.project_details_id == db.project_details.id) & 
                                  (db.project_id.id == db.project_members.project_id) &
                                  (db.project_members.user_id == auth.user_id) &
                                  (db.project_members.project_id <> project_id) &
                                  (db.project_members.is_coordinator == 'T'))
                
                linkable =  coordinating.select(db.project_details.title,
                                                db.project_id.id)
                
            if len(linkable):
                
                # build up a form containing a table of the current links and some controls
                # to add new ones
                selector = SELECT(*[OPTION(r.project_details.title, _value=r.project_id.id) for r in linkable],
                                  _class="generic-widget form-control", _name='project_id')
                add_button = TAG.BUTTON(add_member_icon, _type="submit",
                                        _style='background:none; border:none;padding:0px 10px;font-size: 100%;')
                
                link_rows.append(TR(TD(selector), TD(add_button)))
                
                linked_projects = FORM(DIV(DIV(H5('Linked projects'), _class='panel-heading'),
                                       TABLE(TR(TH('Linked project', _width='80%'), TH('Linked by')),
                                            *link_rows,
                                            _width='100%', _class='table table-striped'),
                                       DIV(_class='panel-footer'),
                                       _class="panel panel-primary"))
                
                # form handling for the link form
                if linked_projects.process(formname='linking').accepted:
                    
                    # create the link and populate the link pairs
                    link_id = db.project_links.insert(user_id = auth.user.id,
                                                      link_date = datetime.datetime.now())
                    db.project_link_pairs.insert(link_id = link_id,
                                                 project_id = project_id)
                    db.project_link_pairs.insert(link_id = link_id,
                                                 project_id = linked_projects.vars.project_id)
                    
                    # update the history
                    link_str = '[{}] {} {}\\n -- Project linked to project id {}\\n'
                    new_history = link_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                  auth.user.first_name,
                                                  auth.user.last_name,
                                                  linked_projects.vars.project_id) + details.admin_history
                
                    details.update_record(admin_history = new_history)
                    
                    # signal success and load the newly created record in a details page
                    session.flash = CENTER(B('New project link added.'), _style='color: green')
                    redirect(URL('projects', 'project_details', args=[project_id, version_id]))
            
            else:
                # just provide a view of the existing links
                linked_projects = DIV(DIV(H5('Linked projects'), _class='panel-heading'),
                                      TABLE(TR(TH('Linked project', _width='80%'), TH('Linked by')),
                                            *link_rows,
                                            _width='100%', _class='table table-striped'),
                                      DIV(_class='panel-footer'),
                                      _class="panel panel-primary")
        else:
            # blank placeholder
            linked_projects = DIV()
        
        # admin history display
        if project_record is not None and details.admin_history is not None:
            admin_history = DIV(DIV(H5('Admin History', ), _class="panel-heading"),
                                DIV(XML(details.admin_history.replace('\\n', '<br />'),
                                        sanitize=True, permitted_tags=['br/']),
                                    _class = 'panel_body'),
                                DIV(_class="panel-footer"),
                                _class='panel panel-primary')
        else:
            admin_history = DIV()
        
        ## ADMIN INTERFACE
        if project_id is not None and auth.has_membership('admin') and details.admin_status in ['Submitted', 'In Review']:
            
            admin = admin_decision_form(selector_options=['Resubmit', 'Approved', 'In Review'])
            
            if admin.process(formname='admin').accepted:
                
                # update record with decision
                admin_str = '[{}] {} {}\\n ** Decision: {}\\n ** Comments: {}\\n'
                new_history = admin_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                               auth.user.first_name,
                                               auth.user.last_name,
                                               admin.vars.decision,
                                               admin.vars.comment) + details.admin_history
                
                details.update_record(admin_status = admin.vars.decision,
                                      admin_history = new_history)
                
                # if this is an approval then update the project_id table
                if admin.vars.decision == 'Approved':
                    id_record = db.project_id(project_id)
                    id_record.update_record(project_details_id = details.id)
                
                # Email decision
                proposer = details.proposer_id
                template_dict = {'name': proposer.first_name, 
                                 'url': URL('projects', 'project_details', args=[project_id, version_id], scheme=True, host=True),
                                 'public_url': URL('projects', 'project_view', args=[project_id], scheme=True, host=True),
                                 'overview_url': URL('info', 'steps_to_follow', scheme=True, host=True),
                                 'rv_url': URL('research_visits','research_visit_details', scheme=True, host=True),
                                 'hs_url': URL('health_safety','health_and_safety', scheme=True, host=True),
                                 'output_url': URL('outputs','output_details', scheme=True, host=True),
                                 'blog_url': URL('blogs','blog_details', scheme=True, host=True),
                                 'email_url': URL('info','mailing_list', scheme=True, host=True),
                                 'admin': auth.user.first_name + ' ' + auth.user.last_name}
                
                # pick an decision
                if admin.vars.decision == 'Approved':
                    
                    SAFEmailer(to=auth.user.email,
                               subject='SAFE: project proposal approved',
                               template =  'project_approved.html',
                               template_dict = template_dict)
                    
                elif admin.vars.decision == 'Resubmit':
                    
                    SAFEmailer(to=auth.user.email,
                               subject='SAFE: project proposal requires resubmission',
                               template =  'project_resubmit.html',
                               template_dict = template_dict)
                    
                elif admin.vars.decision == 'In Review':
                    
                    # Email the proposer
                    SAFEmailer(to=auth.user.email,
                               subject='SAFE: project proposal sent for review',
                               template =  'project_in_review.html',
                               template_dict = template_dict)
                    
                    # collect the people to email - coordinators of projects that have end dates less than a year ago
                    coords = db((db.project_details.end_date > datetime.date.today() - datetime.timedelta(days=365)) &
                                (db.project_details.project_id == db.project_members.project_id) &
                                (db.project_members.is_coordinator == 'T') &
                                (db.auth_user.id == db.project_members.user_id)).select(db.auth_user.email)
                    
                    
                    # TODO TODO TODO - make this live! Sub in to email below.
                    coords = set([r.email for r in coords])
                    coords = ['d.orme@imperial.ac.uk']
                    
                    # Email the review panel
                    SAFEmailer(to = coords,
                               subject='SAFE Project Proposal Review (' + str(project_id) + ')',
                               template =  'project_to_review.html',
                               template_dict = template_dict)
                    
                # elif admin.vars.decision == 'Rejected':
                #     mail.send(to=proposer.email,
                #               subject='SAFE project submission',
                #               message='Dear {},\n\nUnlucky template\n\n {}'.format(proposer.first_name, admin.vars.comment))
                #     redirect(URL('projects','administer_projects'))
                else:
                    pass
                
                session.flash = CENTER(B('Decision emailed to project proposer at {}.'.format(proposer.email)), _style='color: green')
                redirect(URL('projects','administer_projects'))
                
            elif form.errors:
                response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
            else:
                pass
        else:
            admin = DIV()
        
        return dict(header_text = header_text,
                    form=form,
                    members=members,
                    linked_projects = linked_projects,
                    admin_history = admin_history,
                    admin = admin)

def validate_project_details(form):
    
    # capture if the request is a submission
    if 'submit_draft' in request.vars.keys():
        form.submit = True
    else:
        form.submit = False
    
    # insert proposal time, proposer and a temporary project_id if there 
    # is no record (so a new proposal)
    if form.record is None:
        form.vars.proposer_id = auth.user_id
        form.vars.proposal_date =  datetime.datetime.now()
    
    # must agree to share data
    if form.vars.data_sharing is False or form.vars.data_sharing is None:
        form.errors.data_sharing = 'Data sharing is a mandatory part of the requirements for working at SAFE.'
    
    # must provide ethics details if needed
    if form.vars.ethics_approval_required == 'on' and \
      (form.vars.ethics_approval_details == '' or form.vars.ethics_approval_details is None):
        form.errors.ethics_approval_details = 'You must provide details of the ethics approval you will need and how you plan to obtain it.'
    
    # must provide destructive sampling details if needed
    if form.vars.destructive_sampling == 'on' and \
      (form.vars.destructive_sampling_info == '' or form.vars.destructive_sampling_info is None):
        form.errors.destructive_sampling_info = 'You must provide justification for destructive sampling in your project.'
    
    # must provide at least one research area
    if form.vars.research_areas == []:
        form.errors.research_areas = 'You must select at least one research area'
    
    # must provide at least one data use
    if form.vars.data_use == []:
        form.errors.data_use = 'You must select at least one data use option'



def validate_new_project_member(form):
    
    # Because we're using SQLFORM always in create mode (there's no existing record
    # preloaded into the widgets in the form) we need to handle 'updates' in a slightly
    # sly way. Basically, look here to see if the user is already a member of this
    # project and delete that record here. It then gets recreated with new values
    # by the rest of the form handling.
    
    
    if (int(form.vars.user_id) == auth.user.id) & (form.vars.is_coordinator is None):
        form.errors.user_id = "You cannot remove your own coordinator status!"
    
    existing_record = db((db.project_members.project_id == form.vars.project_id) & 
                         (db.project_members.user_id == form.vars.user_id)).select()
    
    for r in existing_record:
        db.project_members(r.id).delete_record()


## -----------------------------------------------------------------------------
## ADMINISTER NEW PROJECTS
## - viewing a simple list of proposals that need action, with links to the
##   project_details page, which exposes an admin interface 
## -----------------------------------------------------------------------------

@auth.requires_membership('admin')
def administer_projects():

    """
    This controller handles:
     - presenting admin users with a list of submitted new proposals
       and in review proposals
     - a custom link to the project details page (which exposes an admin controller)
    """
    
    # create an icon showing project status and a new button that
    # passes the project id to a new controller
    links = [dict(header = '', body = lambda row: approval_icons[row.admin_status]),
             dict(header = '', body = lambda row: A('Details',_class='button btn btn-default'
                  ,_href=URL("projects","project_details", args=[row.project_id, row.version]),
                  _style =  'padding: 5px 15px 5px 15px;'))
            ]
    
    # hide the text of the admin_status
    db.project_details.admin_status.readable = False
    db.project_details.project_id.readable = False
    db.project_details.version.readable = False
    
    query = (db.project_details.admin_status.belongs(['Submitted','In Review']))
    
    # get a query of pending requests 
    form = SQLFORM.grid(query = query,
                        csv=False,
                        fields=[db.project_details.proposal_date,
                                db.project_details.title,
                                #db.project.start_date,
                                #db.project.end_date
                                db.project_details.admin_status,
                                db.project_details.project_id,
                                db.project_details.version,
                                ],
                         orderby = db.project_details.proposal_date,
                         maxtextlength=250,
                         deletable=False,
                         editable=False,
                         create=False,
                         details=False,
                         links = links,
                         )
    
    return dict(form=form)
