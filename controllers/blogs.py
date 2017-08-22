
import datetime

## -----------------------------------------------------------------------------
## BLOG PUBLIC INTERFACE
## - public controllers to view blog list and details
## -----------------------------------------------------------------------------

def blogs():
    
    # create a link to take the user to the custom view
    links = [link_button("blogs","blog_post", 'id')]
    
    # thumbnail representation
    db.blog_posts.thumbnail_figure.represent = lambda value, row: thumbnail(value, 'missing_blog.png')
    
    form = SQLFORM.grid((db.blog_posts.hidden == False) &
                        (db.blog_posts.admin_status == 'Approved'), 
                        fields=[db.blog_posts.thumbnail_figure,
                                db.blog_posts.title,
                                db.blog_posts.date_posted],
                        orderby= ~ db.blog_posts.date_posted,
                        headers={'blog_posts.thumbnail_figure': ''},
                        maxtextlength=150,
                        links=links,
                        editable=False,
                        create=False,
                        deletable=False,
                        details=False,
                        csv=False)
    
    return dict(form=form)


def blog_post():
    
    """
    hijacks the view from the blog list grid and creates a nice display
    """
    
    # retrieve the user id from the page arguments passed by the button
    # and then get the row and send it to the view
    blog_id = request.args(0)
    blog_post = db.blog_posts(blog_id)
    
    if blog_post is None or blog_post.hidden or blog_post.admin_status != 'Approved':
        session.flash = CENTER(B('Blog post id not available.'), _style='color: red')
        redirect(URL('blogs','blogs'))
    
    return dict(blog_post = blog_post)

## -----------------------------------------------------------------------------
## BLOG CREATION INTERFACE
## - controller to allow bloggers to create new posts and edit existing ones
## -----------------------------------------------------------------------------

@auth.requires_login()
def blog_details():
    
    """
    This allows blogger to create or edit a blog post - existing posts are
    linked to from the My SAFE page for the creator. These records are not
    visible to all users, who would just read the blog post.
    """
    
    # do we have a request for an existing blog post?
    blog_id = request.args(0)
    
    if blog_id is not None:
        record = db.blog_posts(blog_id)
    else:
        record = None
        
    if blog_id is not None and record is None:
        # avoid unknown blogs
        session.flash = B(CENTER('Invalid blog id'), _style='color:red;')
        redirect(URL('blogs','blogs'))
        
    elif record is None or record.user_id == auth.user.id or auth.has_membership('admin'):
        
        if record is None:
            buttons =  [TAG.BUTTON('Submit', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='create')]
            readonly = False
        else:
            readonly = True if record.admin_status == 'Submitted' else False
            buttons =  [TAG.BUTTON('Update and resubmit', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='update')]
        
        # provide a form to create or edit
        form = SQLFORM(db.blog_posts,
                       readonly=readonly,
                       record=record,
                       buttons=buttons,
                       fields=['thumbnail_figure','authors','title','content'], 
                       showid=False)
        
        if form.validate(onvalidation=validate_blog_post):
            
            req_keys = request.vars.keys()
            
            # get and add a comment to the history
            hist_str = '[{}] {} {}\\n -- {}\\n'
            new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                       auth.user.first_name,
                                                       auth.user.last_name,
                                                       'Post created' if blog_id is None else "Post edited")
            
            if 'update' in req_keys:
                id = record.update_record(admin_history = new_history + record.admin_history,
                                          **db.blog_posts._filter_fields(form.vars))
                id = id.id
                msg = CENTER(B('Blog post updated and resubmitted for approval.'), _style='color: green')
            elif 'create' in req_keys:
                id = db.blog_posts.insert(admin_history=new_history, 
                                          **db.blog_posts._filter_fields(form.vars))
                
                msg = CENTER(B('Blog post created and submitted for approval.'), _style='color: green')
            else:
                pass
            
            # Email the link
            template_dict = {'name': auth.user.first_name, 
                             'url': URL('blogs', 'blog_details', args=[id], scheme=True, host=True),
                             'submission_type': 'blog post'}
            
            SAFEmailer(to=auth.user.email,
                       subject='SAFE: blog post submitted',
                       template =  'generic_submitted.html',
                       template_dict = template_dict)
            
            session.flash = msg
            redirect(URL('blogs','blog_details', args=[id]))
            
        elif form.errors:
            response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
        else:
            pass
        
        # package form into a panel
        if record is None:
            status = ""
            vis = ""
        else:
            status =    DIV(approval_icons[record.admin_status], XML('&nbsp'),
                           'Status: ', XML('&nbsp'), record.admin_status, 
                            _class='col-sm-3',
                            _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            if record.hidden:
                vis = DIV('Hidden', _class='col-sm-1 col-sm-offset-1',
                          _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            else:
                vis = DIV('Visible', _class='col-sm-1 col-sm-offset-1',
                          _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            
                      
        panel_header = DIV(H5('Blog post', _class='col-sm-7'), status, vis,
                           _class='row', _style='margin:0px 0px')
        
        if readonly:
            content = XML(record.content)
        else:
            content = form.custom.widget.content
        
        form = FORM(form.custom.begin,
                    DIV(DIV(panel_header, _class="panel-heading"),
                        DIV(LABEL('Thumbnail Figure:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.thumbnail_figure, _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Authors:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.authors,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Title:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.title, _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Blog Content:', _class="control-label col-sm-2" ),
                            DIV(content,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(form.custom.submit, _class='panel-footer'),
                        _class="panel panel-primary"),
                        form.custom.end)
    else: 
        # security doesn't allow people editing other users blogs
        session.flash = CENTER(B('You do not have permission to edit this blog post.'), _style='color: red')
        redirect(URL('blogs','blog_post', args=blog_id))
    
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
    
    ## ADMIN INTERFACE
    if record is not None and auth.has_membership('admin') and record.admin_status == 'Submitted':
        
        admin = admin_decision_form(['Resubmit','Approved'])
        
        if admin.process(formname='admin').accepted:
            
            # update record with decision
            admin_str = '[{}] {} {}\\n ** Decision: {}\\n ** Comments: {}\\n'
            new_history = admin_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                       auth.user.first_name,
                                                       auth.user.last_name,
                                                       admin.vars.decision,
                                                       admin.vars.comment) + record.admin_history
            
            record.update_record(admin_status = admin.vars.decision,
                                 admin_history = new_history)
            
            # pick an decision
            poster = record.user_id
            
            template_dict = {'name': poster.first_name, 
                             'url': URL('blogs', 'blog_details', args=[blog_id], scheme=True, host=True),
                             'public_url': URL('blogs', 'blog_post', args=[blog_id], scheme=True, host=True),
                             'admin': auth.user.first_name + ' ' + auth.user.last_name,
                             'submission_type': 'blog post'}
            
            # pick an decision
            if admin.vars.decision == 'Approved':
                
                SAFEmailer(to=poster.email,
                           subject='SAFE: blog post approved',
                           template =  'generic_approved.html',
                           template_dict = template_dict)
                
                msg = CENTER(B('Blog approval emailed to poster at {}.'.format(poster.email)), _style='color: green')
            
            elif admin.vars.decision == 'Resubmit':

                SAFEmailer(to=poster.email,
                           subject='SAFE: blog post requires resubmission',
                           template =  'generic_resubmit.html',
                           template_dict = template_dict)
                
                msg = CENTER(B('Blog resubmission emailed to poster at {}.'.format(poster.email)), _style='color: green')
            
            else:
                pass
            
            redirect(URL('blogs','administer_blogs'))
            session.flash = msg
            
        elif admin.errors:
            response.flash = CENTER(B('Errors in form, please check and resubmit'), _style='color: red')
        else:
            pass
    else:
        admin = DIV()
    
    # pass components to the view
    return dict(form=form,  admin_history=admin_history, admin=admin)


@auth.requires_login()
def validate_blog_post(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.user_id = auth.user_id
    form.vars.date_posted =  datetime.date.today().isoformat()
    
    # need to set approval to flag oversight on edits
    form.vars.admin_status = 'Submitted'


## -----------------------------------------------------------------------------
## BLOG APPROVAL CONTROLLERS
## - give the admin an interface to review and approve pending blogs
## -----------------------------------------------------------------------------

@auth.requires_membership('admin')
def administer_blogs():

    """
    This controller handles:
     - presenting admin users with a list of submitted blogs
     - a custom link to a page showing members and project details
    """
    
    # create a new button that passes the project id to a new controller
    links = [dict(header = '', body = lambda row: A('Details',_class='button btn btn-default'
                  ,_href=URL("blogs","blog_details", args=[row.id])))
            ]
    
    # get a query of pending requests 
    form = SQLFORM.grid(query=(db.blog_posts.admin_status == 'Submitted'), csv=False,
                        fields=[db.blog_posts.title,
                                db.blog_posts.user_id,
                                db.blog_posts.date_posted],
                         maxtextlength=250,
                         deletable=False,
                         editable=False,
                         create=False,
                         details=False,
                         links = links,
                         editargs = {'showid': False},
                         )
    
    return dict(form=form)

@auth.requires_membership('admin')
def manage_blogs():
    
    links = [link_button("blogs","blog_post", 'id')]
    
    # field representation
    db.blog_posts.thumbnail_figure.represent = lambda value, row: thumbnail(value, 'missing_blog.png')
    db.blog_posts.hidden.represent = lambda value, row: A(hide_glyph if row.hidden else visib_glyph,
                                                          _class="button btn btn-default",
                                                          _href=URL("blogs","blog_hide", args=[row.id]),
                                                          _style=hide_style if row.hidden else visib_style)
    
    form = SQLFORM.grid(db.blog_posts, 
                        fields=[db.blog_posts.thumbnail_figure,
                                db.blog_posts.title,
                                db.blog_posts.date_posted,
                                db.blog_posts.hidden],
                        headers={'blog_posts.thumbnail_figure': ''},
                        orderby= ~ db.blog_posts.date_posted,
                        maxtextlength=150,
                        links=links,
                        editable=False,
                        create=False,
                        deletable=False,
                        details=False,
                        csv=False)
    
    return dict(form=form)


@auth.requires_membership('admin')
def blog_hide():
    
    blog_id = request.args(0)
    record = db.blog_posts(blog_id)
    if record.hidden:
        record.hidden = False
        new_history = '[{}] {} {}\\n ** Blog un-hidden\\n'
    else:
        record.hidden = True
        new_history = '[{}] {} {}\\n ** Blog hidden\\n'
    
    record.admin_history = new_history.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                              auth.user.first_name,
                                              auth.user.last_name) + record.admin_history
    
    record.update_record()
    
    redirect(URL('blogs', 'manage_blogs'))
        
