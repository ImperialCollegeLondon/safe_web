import datetime

## -----------------------------------------------------------------------------
## OUTPUTS
## - public controllers to view outputs and get a nicely formatted output details view
## -----------------------------------------------------------------------------

def outputs():
    
    """
    This controller shows the grid view for outputs
    """
    
    # create a link object that associates a row with the image uploaded for it
    links = [dict(header = '', body = lambda row: IMG(_src = URL('default', 
                  'download', args = row.picture), _width = 100, _height = 100))]
    
    # we need the picture field in the fields fetched, in order to look up
    # the picture to display as a row using links, but we don't want to actually 
    # show the field itself, so:
    db.outputs.picture.readable = False
    
    # subset down to approved projects
    query = (db.outputs.admin_status == 'Approved')
    
    form = SQLFORM.grid(query = query, csv=False, 
                        fields=[db.outputs.picture, db.outputs.title, db.outputs.format],
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False,
                        links=links,
                        links_placement='left',
                        formargs= {'fields': ['title', 'citation','format', 'file',
                                              'description','doi', 'url'],
                                   'showid': False})
   
    return dict(form=form)


def view_output():
    
    # retrieve the output id from the page arguments passed by the button
    # and then get the row and send it to the view
    
    output_id = request.args(0)
    output = db(db.outputs.id == output_id).select().first()
    
    # build the view in controller and pass over to the view as a single object
    if output.picture not in [None, 'NA', '']:
        pic = URL('static', 'images/default_thumbnails/missing_output.png')
    else:
        pic = URL('default','download', args = output.picture)
    
    if output.url not in [None, 'NA', '']:
        url = DIV(DIV(B('Output URL:'), _class='col-sm-2'), 
                  DIV(A(output.url, _href=output.url), _class='col-sm-10'),
                  _class='row')
    else:
        url = ""
    
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
    output_panel = CAT(DIV(DIV(H4(output.title), _class='col-sm-10'),
                        DIV(DIV(IMG(_src=pic, _width='100px'), _class= 'pull-right'), _class='col-sm-2'),
                                _class='row', _style='margin:10px 10px;'), 
                            DIV(DIV('Description', 
                                    A(SPAN('',_class="icon leftarrow icon-arrow-left glyphicon glyphicon-arrow-left"),
                                        SPAN(' Back to outputs'),
                                        _href=URL("outputs","outputs", user_signature=True),
                                        _class='pull-right', _style='color:white'),
                                    _class="panel-heading"),
                                DIV(url, doi, dfile, 
                                    local_hr,
                                    DIV(DIV(XML(output.description.replace('\n', '<br />'),
                                            sanitize=True, permitted_tags=['br/']),
                                            _class='col-sm-12'),
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
        button = 'Save edits'
    else:
        record = None
        button = 'Submit output'
        
    if output_id is not None and record is None:
        
        # avoid unknown outputs
        session.flash = B(CENTER('Invalid output id'), _style='color:red;')
        redirect(URL('outputs','outputs'))
        
    elif output_id is not None and ((record.user_id != auth.user.id) & (not auth.has_membership('admin'))):
        print 'hello!'
        print not auth.has_membership('admin')
        # security check to stop people editing other users outputs
        session.flash = CENTER(B('You do not have permission to edit these output details, showing output view.'), _style='color: red')
        redirect(URL('outputs','view_output', args=output_id))
        
    else:
        
        # allow admins to view but not edit the record
        if record.user_id <> auth.user.id:
            readonly=True
        else:
            readonly=False
        
        # create the form
        form =  SQLFORM(db.outputs, record = output_id,
                        fields = ['picture','file','title','description',
                                 'format', 'citation', 'doi','url'],
                        readonly=readonly,
                        showid=False,
                        submit_button = button)
        
        # now intercept and parse the various inputs
        if form.process(onvalidation=validate_output_details, formname='outputs').accepted:
            
            # Signal success and email the proposer
            mail.send(to=auth.user.email,
               subject='SAFE project output created/edited',
               message='Many thanks for uploading your output')
            session.flash = CENTER(B('SAFE project output created/edited.'), _style='color: green')
            
            # add a comment to the history
            new_history = '[{} {}, {}, {}]\\n'.format(auth.user.first_name,
                           auth.user.last_name, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                           'Output created' if output_id is None else "Output edited")
            
            # reload the record
            output_record = db.outputs(form.vars.id)
            
            if output_record.admin_history is None or output_record.admin_history == '':
                output_record.update_record(admin_history = new_history)
            else:
                output_record.update_record(admin_history = output_record.admin_history + '\\n' + new_history)
            
            # now send to the output_details page for the form we've just created
            redirect(URL('outputs', 'output_details', args=form.vars.id))
            
        elif form.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
        
        
        # now repackage the form as a more attractive DIV
                
        # - picture
        if (record is None) or (record.picture in [None, 'NA', '']):
            pic = URL('static', 'images/default_thumbnails/missing_output.png')
        else:
            pic = URL('default','download', args = record.picture)
        
        # - file
        if record.file not in [None, 'NA', '']:
            # need to retrieve the file to get the original file name
            fn, stream = db.outputs.file.retrieve(record.file)
            stream.close()
            dfile = A(fn, _href=URL('default','download', args = record.file))
        else:
            dfile = ""
        
        form =  CAT(form.custom.begin, 
                    DIV(DIV(H5('Output details', ), _class="panel-heading"),
                        DIV(DIV(LABEL('Title:', _class="control-label col-sm-2" ),
                                         DIV(form.custom.widget.title,  _class="col-sm-10"),
                                         _class='row'),
                            DIV(DIV(DIV(LABEL('Upload Thumbnail:', _class="control-label col-sm-4" ),
                                        DIV(form.custom.widget.picture,  _class="col-sm-8"),
                                        _class='row'),
                                    DIV(LABEL('Current Thumbnail:', _class="control-label col-sm-4" ),
                                        DIV(IMG(_src=pic, _height='100px'), _class='col-sm-8'),
                                         _class='row'),
                                    _class='col-sm-6'),
                                DIV(DIV(LABEL('Upload File:', _class="control-label col-sm-4" ),
                                        DIV(form.custom.widget.file,  _class="col-sm-8"),
                                        _class='row'),
                                    DIV(LABEL('Current File:', _class="control-label col-sm-4" ),
                                        DIV(dfile, _class='col-sm-8'),
                                         _class='row'),
                                    _class='col-sm-6'),
                                _class='row'),
                            DIV(LABEL('Description:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.description,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('Format:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.format,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('Citation:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.citation,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('DOI:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.doi,  _class="col-sm-10"),
                                _class='row'),
                            DIV(LABEL('URL:', _class="control-label col-sm-2" ),
                                DIV(form.custom.widget.url,  _class="col-sm-10"),
                                _class='row'),
                            _class='panel_body', _style='margin:10px 10px'),
                            DIV(DIV(DIV(form.custom.submit, _class='col-sm-4'),
                                    DIV('Uploaded by: ', record.user_id.first_name, ' ', record.user_id.last_name,
                                        _style='text-align:right; color=grey; font-size:smaller',
                                        _class='col-sm-8'),
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
            linkable = linkable_query.select(db.project_id.id, db.project_details.title, orderby=db.project_details.title)
            
            selector = SELECT(*[OPTION(r.project_details.title, _value=r.project_id.id) for r in linkable],
                              _class="generic-widget form-control", _name='project_id')
            add_button = TAG.BUTTON(add_member_icon, _type="submit",
                                    _style='background:none; border:none;padding:0px 10px;font-size: 100%;')
            
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
                
                session.flash = CENTER(B('Output added to new project.'), _style='color: green')
                redirect(URL('outputs', 'output_details', args=output_id))
            elif projects.errors:
                response.flash = CENTER(B('Problem adding project.'), _style='color: red')
            else:
                pass
            
        else:
            projects = None
    
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
                     P('Please use the form below to submit a new research output to the SAFE project. ',
                       'Your submitted output will first be screened by an administrator. You will get an ',
                       'email to confirm that you have submitted an output and then another email to confirm ',
                       'whether the output has been accepted or not.'))
    else:
        header = H2(approval_icons[record.admin_status] + XML('&nbsp;')*3 + record.title)
    
    # Add an admin interface
    if auth.has_membership('admin'):
        
        selector = SELECT('Resubmit', 'Approved',  _class="generic-widget form-control", _name='decision')
        comments = TEXTAREA(_type='text', _class="form-control string", _rows=2, _name='comment')
        submit = TAG.BUTTON('Submit', _type="submit", _class="button btn btn-default",
                            _style='padding: 3px 5px 3px 5px;')
        
        admin = FORM(DIV(DIV(H5('Admin Decision', ), _class="panel-heading"),
                        DIV(DIV(DIV(LABEL('Select decision', _class='row'),
                                DIV(selector, _class='row'),
                                DIV(submit,  _class='row'),
                                _class='col-sm-2'),
                            DIV(LABEL('Comments', _class='row'),
                                DIV(comments, _class='row'),
                                _class='col-sm-10'),
                            _class='row',_style='margin:10px 10px'),
                            _class = 'panel_body', _style='margin:10px 10px'),
                        DIV(_class="panel-footer"),
                        _class='panel panel-primary'))
        
        if admin.process(formname='admin').accepted:
            
            # add info to the history string
            new_history = '[{} {}, {}, {}]\\n{}\\n'.format(auth.user.first_name,
                           auth.user.last_name, datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                           admin.vars.decision, admin.vars.comment)
            
            # update the admin history
            if record.admin_history in [None, '']:
                record.update_record(admin_status=admin.vars.decision,
                                     admin_history = new_history)
            else:
                record.update_record(admin_status=admin.vars.decision,
                                     admin_history = record.admin_history + '\\n' + new_history)
    
            # set a flash message
            flash_message  = CENTER(B('Decision emailed to project member at {}.'.format(record.user_id.email)), _style='color: green')
    
            if admin.vars.decision == 'Approved':
                mail.send(to=record.user_id.email,
                          subject='SAFE output submission',
                          message='Dear {},\n\nLucky template\n\n {}'.format(record.user_id.first_name, admin.vars.comment))
                session.flash = flash_message
            elif admin.vars.decision == 'Resubmit':
                mail.send(to=record.user_id.email,
                          subject='SAFE output submission',
                          message='Dear {},\n\nUnlucky template\n\n {}'.format(record.user_id.first_name, admin.vars.comment))
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
    Add uploader id and date and (re)set the approval status
    TODO -  could check the file isn't ridiculously big but once it is at this 
            point, in this controller, it has already been uploaded. So dim to 
            block it here.
    """
    
    form.vars.user_id = auth.user_id
    form.vars.submission_date =  datetime.date.today().isoformat()
    
    # update the record admin status to make it Pending
    form.vars.admin_status='Pending'

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
    
    rows = db(db.outputs.admin_status == 'Pending').select()

    if len(rows) > 0:
        table_rows = [TR(TD(A(r.title, _href=URL('outputs', 'output_details', args=r.id)))) for r in rows]
    else:
        table_rows = [TR(TD(B(CENTER('No pending outputs to administer'))))]
    
    outputs = TABLE(*table_rows, _width='100%', _class='table table-striped')
    
    return dict(outputs=outputs)
