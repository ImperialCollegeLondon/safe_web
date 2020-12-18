import datetime
from safe_web_global_functions import thumbnail, link_button, admin_decision_form, safe_mailer

## -----------------------------------------------------------------------------
## OUTPUTS
## - public controllers to view outputs and get a nicely formatted output details view
## -----------------------------------------------------------------------------

def outputs():
    
    """
    This controller shows the grid view for outputs
    """
    
    # create a link to take the user to the custom view
    links = [link_button("outputs","view_output", 'id')]
    
    # thumbnail representation
    db.outputs.thumbnail_figure.represent = lambda value, row: thumbnail(value, 'missing_output.png')
    
    # subset down to approved projects
    query = (db.outputs.admin_status == 'Approved')
    
    # we're letting the default link display for the title take us to view_output
    form = SQLFORM.grid(query = query, csv=False, 
                        fields=[db.outputs.thumbnail_figure, db.outputs.title,
                                db.outputs.submission_date, db.outputs.format],
                        orderby = ~ db.outputs.submission_date,
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        headers={'outputs.thumbnail_figure': ''},
                        details=False,
                        links=links,
                        formargs= {'fields': ['title', 'citation','format', 'file',
                                              'abstract', 'lay_summary','doi', 'url'],
                                   'showid': False})
   
    return dict(form=form)


def view_output():
    
    # retrieve the output id from the page arguments passed by the button
    # and then get the row and send it to the view
    
    output_id = request.args(0)
    output = db(db.outputs.id == output_id).select().first()
    
    # check this is a valid approved output
    if (output is None) or (output.admin_status != 'Approved'):
        session.flash = B(CENTER('Unknown output id'), _style='color:red;')
        redirect(URL('outputs','outputs'))
    
    # build the view in controller and pass over to the view as a single object
    if output.thumbnail_figure not in [None, 'NA', '']:
        pic = URL('default','download', args = output.thumbnail_figure)
    else:
        pic = URL('static', 'images/default_thumbnails/missing_output.png')
    
    if output.url not in [None, 'NA', '']:
        url = DIV(DIV(B('Output URL:'), _class='col-sm-2'), 
                  DIV(A(output.url, _href=output.url), _class='col-sm-10'),
                  _class='row')
    else:
        url = ""
    
    if output.citation not in [None, 'NA', '']:
        citation = CAT(DIV(DIV(B('Citation:'), _class='col-sm-2'), 
                           DIV(output.citation, _class='col-sm-10'),
                           _class='row'),
			local_hr)
    else:
        citation = ""
    
    if output.doi not in [None, 'NA', '']:
        doi = DIV(DIV(B('Output DOI:'), _class='col-sm-2'), 
                  DIV(A(output.doi, _href=output.doi), _class='col-sm-10'),
                  _class='row')
    else:
        doi = ""
    
    if output.file not in [None, 'NA', '']:
        # need to retrieve the file to get the original file name
        fn, stream = db.outputs.file.retrieve(output.file)
        stream.close()
        
        dfile = DIV(DIV(B('Download file:'), _class='col-sm-2'), 
                  DIV(A(fn, _href=URL('default','download', args = output.file)),  _class='col-sm-10'),
                  _class='row')
    else:
        dfile = ""

    
    # output details panel
    if output.lay_summary not in ['', None]:
        lay_summary =   CAT(local_hr,
                            DIV(LABEL('Lay Summary:', _class="control-label col-sm-2" ),
                                DIV(output.lay_summary,  _class="col-sm-10"),
                                _class='row'))
    else:
        lay_summary=''

    output_panel = CAT(DIV(DIV(H4(output.title), _class='col-sm-10'),
                        DIV(DIV(IMG(_src=pic, _width='100px'), _class= 'pull-right'), _class='col-sm-2'),
                                _class='row', _style='margin:10px 10px;'), 
                            DIV(DIV('Description', 
                                    A(SPAN('',_class="icon leftarrow icon-arrow-left glyphicon glyphicon-arrow-left"),
                                        SPAN(' Back to outputs'),
                                        _href=URL("outputs","outputs", user_signature=True),
                                        _class='pull-right', _style='color:white'),
                                    _class="panel-heading"),
                                DIV(citation, url, doi, dfile, 
                                    lay_summary, 
                                    local_hr,
                                    DIV(LABEL('Abstract:', _class="control-label col-sm-2" ),
                                        DIV(XML(output.abstract.replace('\n', '<br />'),
                                            sanitize=True, permitted_tags=['br/']),
                                            _class='col-sm-10'),
                                        _class='row'),
                                    _class='panel-body',
                                    _style='margin:10px 10px'),
                            DIV(DIV('Uploaded by: ', output.user_id.first_name, ' ', output.user_id.last_name,
                                        _style='text-align:right; color=grey; font-size:smaller'),
                                _class='panel-footer'),
                            _class="panel panel-primary"))
    
    # set up the related projects panel
    project_rows = output.project_outputs.select()
    
    if len(project_rows) > 0:
        
        # need to look up titles through the project_id and project_details tables, which is clunky
        rows = []
        for r in project_rows:
            details_id = db.project_id(r.project_id).project_details_id
            title = db.project_details(details_id).title
            rows.append(TR(TD(A(title, _href=URL('projects','project_view', args=[r.project_id])))))
            
        related_projects = TABLE(*rows, _class='table table-striped', _style='width:100%')
        
        related_projects = DIV(DIV('Related projects', _class="panel-heading"),
                                    related_projects,
                                    DIV(_class='panel-footer'),
                                _class="panel panel-primary")
    else:
        related_projects = ""
    
    return dict(output_panel = output_panel, 
                related_projects = related_projects)

## -----------------------------------------------------------------------------
## OUTPUT CREATION AND EDITING
## - user controllers create new outputs, edit existing ones and pair to projects
## -----------------------------------------------------------------------------


@auth.requires_login()
def output_details():
    
    """
    This controller provides an interface to create a new output 
    (when no request arguments are passed)
    
    shows a SQLFORM to submit an upload and it also exposes a form
    for existing users to tag that upload to a project and only
    projects for which the logged in user is a member are available.
    
    The controller then passes the response through validation before 
    sending a confirmation email out.
    """
    
    # do we have a request for an existing blog post
    output_id = request.args(0)
    
    if output_id is not None:
        record = db.outputs(output_id)
        buttons = [TAG.button('Save edits',_type="submit", 
                                      _name='save', _style='padding: 5px 15px 5px 15px;'), 
                   XML('&nbsp;')*5,
                   TAG.button('Submit output',_type="submit", 
                              _name='submit', _style='padding: 5px 15px 5px 15px;')]
    else:
        record = None
        buttons = [TAG.button('Create output',_type="submit", 
                              _name='create', _style='padding: 5px 15px 5px 15px;')]
        
    if output_id is not None and record is None:
        
        # avoid unknown outputs
        session.flash = B(CENTER('Invalid output id'), _style='color:red;')
        redirect(URL('outputs','outputs'))
        
    elif output_id is not None and ((record.user_id != auth.user.id) & (not auth.has_membership('admin'))):
        # security check to stop people editing other users outputs
        session.flash = CENTER(B('You do not have permission to edit these output details, showing output view.'), _style='color: red')
        redirect(URL('outputs','view_output', args=output_id))
        
    else:
        
        # allow admins to view but not edit existing records and lock submitted versions
        if (record is not None) and ((record.user_id != auth.user.id) or (record.admin_status == 'Submitted')):
            readonly=True
        else:
            readonly=False
        
        # create the form
        form =  SQLFORM(db.outputs, record = output_id,
                        fields = ['thumbnail_figure','file','title','abstract', 'lay_summary',
                                 'format', 'citation', 'doi','url'],
                        readonly=readonly,
                        showid=False,
                        buttons = buttons)
        
        # now intercept and parse the various inputs
        if form.process(onvalidation=validate_output_details, formname='outputs').accepted:
            
            # reload the record
            output_record = db.outputs(form.vars.id)
            
            template_dict = {'name': auth.user.first_name,
                             'url': URL('outputs', 'output_details', args=[output_record.id], scheme=True, host=True)}
            
            if form.submit:
                
                # Submit button pressed: Signal success and email the proposer
                safe_mailer(to=auth.user.email,
                           subject='SAFE: project output submitted',
                           template =  'output_submitted.html',
                           template_dict = template_dict)
            
                session.flash = CENTER(B('SAFE project output submitted.'), _style='color: green')
                
                # create a comment to add to the history
                history_text = 'Output submitted'
                
                # update the status
                output_record.update_record(submission_date=datetime.date.today(),
                                            admin_status = 'Submitted')
            
            else:
                # is this brand new? If so send a link
                if record is None:
                    safe_mailer(to=auth.user.email,
                               subject='SAFE: project output draft created',
                               template =  'output_created.html',
                               template_dict = template_dict)
                    
                    session.flash = CENTER(B('SAFE project output draft created.'), _style='color: green')
                    
                    # create a comment to add to the history
                    history_text = 'Output draft created'
                    
                else:
                    history_text = 'Output draft edited'
                    session.flash = CENTER(B('SAFE project output draft created.'), _style='color: green')
                    
                    # create a comment to add to the history
                    history_text = 'Output edited'
                    
                # update the status - takes output back from approved
                output_record.update_record(admin_status = 'Draft')
                
            new_history = '[{}] {} {}\\n -- {}\\n'.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                       auth.user.first_name,
                                                       auth.user.last_name,
                                                       history_text)
            
            if output_record.admin_history is None or output_record.admin_history == '':
                output_record.update_record(admin_history = new_history)
            else:
                output_record.update_record(admin_history =  new_history + output_record.admin_history)
            
            # now send to the output_details page for the form we've just created
            redirect(URL('outputs', 'output_details', args=form.vars.id))
            
        elif form.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
        
        
        # now repackage the form as a more attractive DIV
        if record is not None:
            # - thumbnail_figure
            if (record is None) or (record.thumbnail_figure in [None, 'NA', '']):
                pic = URL('static', 'images/default_thumbnails/missing_output.png')
            else:
                pic = URL('default','download', args = record.thumbnail_figure)
        
            # - file
            if record.file not in [None, 'NA', '']:
                # need to retrieve the file to get the original file name
                fn, stream = db.outputs.file.retrieve(record.file)
                stream.close()
                dfile = A(fn, _href=URL('default','download', args = record.file))
            else:
                dfile = ""
            
            uploader =  DIV('Uploaded by: ', record.user_id.first_name, ' ', record.user_id.last_name,
                            _style='text-align:right; color=grey; font-size:smaller',
                            _class='col-sm-8')
        else:
            pic = URL('static', 'images/default_thumbnails/missing_output.png')
            dfile = ""
            uploader = DIV()
        
        # make it clear the DOI should be a link
        if not readonly:
            form.custom.widget.doi["_placeholder"] = "http://dx.doi.org/"
        
        form =  CAT(form.custom.begin, 
                    DIV(DIV(H5('Output details', ), _class="panel-heading"),
                        DIV(DIV(LABEL('Title:', _class="control-label col-sm-2" ),
                                         DIV(form.custom.widget.title,  _class="col-sm-10"),
                                         _class='row'),
                            DIV(DIV(DIV(LABEL('Upload Thumbnail:', _class="control-label col-sm-4" ),
                                        DIV(form.custom.widget.thumbnail_figure,  _class="col-sm-8"),
                                        _class='row'),
                                    DIV(LABEL('Current Thumbnail:', _class="control-label col-sm-4" ),
                                        DIV(IMG(_src=pic, _height='100px'), _class='col-sm-8'),
                                         _class='row'),
                                    _class='col-sm-6'),
                                DIV(DIV(LABEL('Upload Output File:', _class="control-label col-sm-4" ),
                                        DIV(form.custom.widget.file,  _class="col-sm-8"),
                                        _class='row'),
                                    DIV(LABEL('Current Output File:', _class="control-label col-sm-4" ),
                                        DIV(dfile, _class='col-sm-8'),
                                         _class='row'),
                                    _class='col-sm-6'),
                                _class='row'),
                            DIV(LABEL('Scientific Abstract:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.abstract,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('Lay Summary or Press Release:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.lay_summary,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('Format:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.format,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('Citation:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.citation,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('URL for DOI:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.doi,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('URL:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.url,  _class="col-sm-10"),
                                _class='row'),
                            _class='panel_body', _style='margin:10px 10px'),
                            DIV(DIV(DIV(form.custom.submit, _class='col-sm-4'),
                                    uploader,
                                    _class='row'),
                                _class='panel-footer'),
                        _class="panel panel-primary"),
                    form.custom.end)
        
        # Now handle adding projects:
        # - provide records of the projects already added and a restricted set
        #   of projects that the user can chose
        if output_id is not None:
            
            # current projects
            projects_query = db((db.project_outputs.output_id == output_id) &
                                (db.project_outputs.project_id == db.project_id.id) & 
                                (db.project_id.project_details_id == db.project_details.id))
            
            if projects_query.count() > 0:
                
                # select the rows and wrap up into a TABLE within a panel DIV
                projects_select = projects_query.select()
                projects_rows = [TR(TD(A(r.project_details.title, 
                                         _href=URL('projects', 'project_view', 
                                                   args=r.project_details.project_id))),
                                    TD()) 
                                 for r in projects_select]
            else:
                projects_rows = []
            
            # wrap everything into a form with a list of projects to select
            linkable_query  = db((db.project_id.id == db.project_details.project_id) & 
                                 (~ db.project_id.id.belongs(projects_query.select(db.project_id.id))))
            linkable = linkable_query.select(db.project_id.id, db.project_details.title,
                                             orderby=db.project_id.id)
            
            selector = SELECT(*[OPTION('({}) {}'.format(r.project_id.id,r.project_details.title),
                                       _value=r.project_id.id) for r in linkable],
                              _class="generic-widget form-control", _name='project_id')
            add_button = TAG.BUTTON(add_member_icon, _type="submit",
                                    _style='background:none; border:none;'
                                           'padding:0px 10px;font-size: 100%;')
            
            projects_rows.append(TR(selector, add_button))
            
            projects = FORM(DIV(DIV(H5('Associated projects', ), _class="panel-heading"),
                                TABLE(*projects_rows, _width='100%', _class='table table-striped'),
                                DIV(_class="panel-footer"),
                                _class='panel panel-primary'))
            
            if projects.process(formname='projects').accepted:
                
                # add the selected_project
                db.project_outputs.insert(project_id = projects.vars.project_id,
                                          output_id = output_id,
                                          user_id = auth.user.id,
                                          date_added = datetime.datetime.now())

                # look for merged projects and add to the umbrella project as well
                project_record = db.project_id[projects.vars.project_id]
                if project_record.merged_to is not None:
                    db.project_outputs.insert(project_id=project_record.merged_to,
                                              output_id=output_id,
                                              user_id=auth.user.id,
                                              date_added=datetime.datetime.now())

                session.flash = CENTER(B('Output added to new project.'), _style='color: green')
                redirect(URL('outputs', 'output_details', args=output_id))
            elif projects.errors:
                response.flash = CENTER(B('Problem adding project.'), _style='color: red')
            else:
                pass
            
        else:
            projects = DIV()
    
    # admin history display
    if record is not None and record.admin_history is not None:
        admin_history = DIV(DIV(H5('Admin History', ), _class="panel-heading"),
                            DIV(XML(record.admin_history.replace('\\n', '<br />'),
                                    sanitize=True, permitted_tags=['br/']),
                                _class = 'panel_body'),
                            DIV(_class="panel-footer"),
                            _class='panel panel-primary')
    else:
        admin_history = DIV()
    
    # header text
    if record is None:
        header = CAT(H2('New Output Submission'), 
                     P('Please use the form below to create a new draft research output for the SAFE project. ',
                       'Once you have created the draft you will then be able to ', B('link your output '),
                       'to existing projects, make further edits and submit the completed outputs to the administrators.'),
                     P('Once you submit your output it will first be screened by an administrator. You will get an ',
                       'email to confirm that you have submitted an output and then another email to confirm ',
                       'whether the output has been accepted or not.'))
    else:
        header = CAT(H2(approval_icons[record.admin_status] + XML('&nbsp;')*3 + record.title),
                    P('Please use the form to edit your draft output and ', B('link your output '),
                      'to existing projects. When you have finished, click Submit.'),
                    P('Once you submit your output it will first be screened by an administrator. You will get an ',
                      'email to confirm that you have submitted an output and then another email to confirm ',
                      'whether the output has been accepted or not.'))
    
    # Add an admin interface
    if record is not None and auth.has_membership('admin'):
        
        admin = admin_decision_form(selector_options=['Resubmit', 'Approved'])
        
        if admin.process(formname='admin').accepted:
            
            # add info to the history string
            admin_str = '[{}] {} {}\\n ** Decision: {}\\n ** Comments: {}\\n'
            new_history = admin_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                           auth.user.first_name,
                                           auth.user.last_name,
                                           admin.vars.decision,
                                           admin.vars.comment)
            
            # update the admin history
            record.update_record(admin_status=admin.vars.decision,
                                 admin_history = new_history + record.admin_history)
            
            # set a flash message
            flash_message  = CENTER(B('Decision emailed to project member at {}.'.format(record.user_id.email)), _style='color: green')
            
            # email the submitter
            admin_template_dict = {'name': record.user_id.first_name, 
                                   'url': URL('outputs', 'output_details', args=[record.id], scheme=True, host=True),
                                   'public_url': URL('outputs', 'view_output', args=[record.id], scheme=True, host=True),
                                   'admin': auth.user.first_name + ' ' + auth.user.last_name}
            
            if admin.vars.decision == 'Approved':
                
                safe_mailer(to=record.user_id.email,
                           subject='SAFE: project output approved',
                           template =  'output_approved.html',
                           template_dict = admin_template_dict)
                
                session.flash = flash_message
                
            elif admin.vars.decision == 'Resubmit':
                
                safe_mailer(to=record.user_id.email,
                           subject='SAFE: resubmit project output',
                           template =  'output_resubmit.html',
                           template_dict = admin_template_dict)
                
                session.flash = flash_message
            else:
                pass
            
            # reload
            redirect(URL('outputs', 'output_details', args=output_id))
    else:
        admin = DIV()
    
    return dict(form=form, projects=projects, admin_history=admin_history, header=header, admin=admin)


def validate_output_details(form):
    
    """
    Add uploader id and check whether the submit button has been pressed
    TODO -  could check the file isn't ridiculously big but once it is at this 
            point, in this controller, it has already been uploaded. So dim to 
            block it here.
    """
    
    # capture if the request is a submission
    if 'submit' in list(request.vars.keys()):
        form.submit = True
    else:
        form.submit = False
    
    form.vars.user_id = auth.user_id

# @auth.requires_login()
# def remove_project():
#
#     """
#     Removes a row from the project_outputs table and as such needs careful safeguarding
#     against use by non-authorised people - must be a logged in as the owner of the output
#     """
#
#     # get the row id and look up the owner of the related output
#     row_id = request.args(0)
#     record = db.project_outputs(row_id)
#     owner = db.outputs(record.output_id).user_id
#
#     if record is not None:
#         # if the user is the output owner then ok
#         if  auth.user.id == owner:
#                 session.flash =  CENTER(B('Project association removed from output.'), _style='color: green')
#                 db(db.project_outputs.id == row_id).delete()
#                 redirect(URL('outputs','output_details', args=record.output_id))
#         else:
#             session.flash =  CENTER(B('Unauthorised use of outputs/remove_project'), _style='color: red')
#             redirect(URL('outputs','outputs'))
#     else:
#         session.flash = CENTER(B('Unknown row ID in outputs/remove_project'), _style='color: red')
#         redirect(URL('outputs','outputs'))



## -----------------------------------------------------------------------------
## OUTPUTS ADMINISTRATION
## - admin controllers to approve submitted outputs.
## -----------------------------------------------------------------------------


@auth.requires_membership('admin')
def administer_outputs():

    """
    This controller handles:
     - presenting admin users with a list of pending output uploads
     - a link to the details page, which will provide an admin decision box
    """
    
    rows = db(db.outputs.admin_status == 'Submitted').select()

    if len(rows) > 0:
        table_rows = [TR(TD(A(r.title, _href=URL('outputs', 'output_details', args=r.id)))) for r in rows]
    else:
        table_rows = [TR(TD(B(CENTER('No pending outputs to administer'))))]
    
    outputs = TABLE(*table_rows, _width='100%', _class='table table-striped')
    
    return dict(outputs=outputs)
