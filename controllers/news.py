import datetime
from fs.osfs import OSFS

## -----------------------------------------------------------------------------
## NEWS
## - public controllers to view news list and details
## - restricted controller to post new news items
## -----------------------------------------------------------------------------


def news():
    
    links = [dict(header = '', body = lambda row: IMG(_src = URL('default', 'download', args = row.thumbnail_figure) if row.thumbnail_figure is not None else 
                                                             URL('static', 'images/default_thumbnails/missing_news.png'),
                                                        _height = 100)),
             dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                       SPAN('View', _class="buttontext button"),
                                       _class="button btn btn-default", 
                                       _href=URL("news","news_post", args=[row.id], user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;'))]
    
    db.news_posts.thumbnail_figure.readable=False
    
    form = SQLFORM.grid(query=db.news_posts.hidden == False, 
                        fields=[db.news_posts.thumbnail_figure,
                                db.news_posts.title,
                                db.news_posts.date_posted],
                        orderby= ~ db.news_posts.date_posted,
                        maxtextlength=150,
                        links=links,
                        links_placement='left',
                        editable=False,
                        create=False,
                        deletable=False,
                        details=False,
                        csv=False)
    
    return dict(form=form)


def news_post():
    
    """
    hijacks the view from the news list grid and creates a nice display
    """
    
    # retrieve the news post id from the page arguments passed by the button
    # and then get the row and send it to the view
    news_id = request.args(0)
    news_post = db.news_posts(news_id)
    
    if news_post is None or news_post.hidden:
        session.flash = CENTER(B('Invalid news post number.'), _style='color: red')
        redirect(URL('news','news'))
    
    return dict(news_post = news_post)
    

## ADMIN

@auth.requires_membership('admin')
def manage_news():
    
    """
    Controller to allow admin to create, edit and delete news posts
    """
    
    missing_img = URL('static', 'images/default_thumbnails/missing_news.png')
    
    links = [dict(header = '', 
                  body = lambda row: IMG(_src = URL('default', 'download', 
                                          args = row.thumbnail_figure) if row.thumbnail_figure is not None else missing_img,
                                         _height = 100)),
            dict(header = '', 
                 body = lambda row: A(SPAN('',_class="glyphicon glyphicon-zoom-in"),
                                      SPAN('Edit'), _class="button btn btn-default", 
                                      _href=URL("news","news_details", args=[row.id], user_signature=True),
                                      _style='padding: 3px 5px 3px 5px;')),
            dict(header = '', 
                 body = lambda row: A(hide_glyph if row.hidden else visib_glyph,
                                      _class="button btn btn-default", 
                                      _href=URL("news","news_hide", args=[row.id], user_signature=True),
                                      _style=hide_style if row.hidden else visib_style))] 
    
    # need these three fields in the fields list to allow the links
    # to be created but don't want to actually show them in the grid
    db.news_posts.thumbnail_figure.readable=False
    db.news_posts.hidden.readable=False
    
    form = SQLFORM.grid(db.news_posts, csv=False, 
                        fields=[db.news_posts.thumbnail_figure,
                                db.news_posts.title,
                                db.news_posts.date_posted,
                                db.news_posts.hidden],
                        orderby=~db.news_posts.date_posted,
                        maxtextlength=100,
                        create=False,
                        deletable=False,
                        editable=False, 
                        details=False, # just reveals a bunch of crappy html.
                        # searchable=False,
                        formargs={'showid': False,
                                  'fields': ['thumbnail_figure', 'title','content'],
                                  'links': None},
                        editargs={'deletable':False},
                        links=links,
                        links_placement='left')
    
    # insert a new button into the form, where the create new record button would be
    # that redirects to a create new topic form (which populates topic and first post in the topic)
    new_button = A("New news post", _class='btn btn-default',
                   _href=URL("news","news_details"), 
                   _style='padding: 5px 10px 5px 10px;')
    form.element('.web2py_console').insert(1, new_button)
    
    return dict(form=form)




@auth.requires_membership('admin')
def news_details():
    
    """
    This allows admins to create or edit news posts.
    """
    
    # do we have a request for an existing post?
    news_id = request.args(0)
    
    if news_id is not None:
        record = db.news_posts(news_id)
    else:
        record = None
        
    if news_id is not None and record is None:
        # avoid unknown news posts
        session.flash = B(CENTER('Invalid news post id'), _style='color:red;')
        redirect(URL('news','manage_news'))
        
    elif record is None or auth.has_membership('admin'):
        
        if record is None:
            buttons =  [TAG.BUTTON('Create', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='create')]
        else:
            buttons =  [TAG.BUTTON('Update', _type="submit", _class="button btn btn-default",
                                   _style='padding: 5px 15px 5px 15px;', _name='update')]
        
        # provide a form to create or edit
        form = SQLFORM(db.news_posts,
                       record=record,
                       buttons=buttons,
                       fields=['thumbnail_figure','title','content'], 
                       showid=False)
        
        if form.process(onvalidation=validate_news_post).accepted:
            
            req_keys = request.vars.keys()
            
            # get and add a comment to the history
            hist_str = '[{}] {} {}\\n -- {}\\n'
            new_history = hist_str.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                                       auth.user.first_name,
                                                       auth.user.last_name,
                                                       'News post created' if news_id is None else "News post edited")
            
            if 'update' in req_keys:
                record = db.news_posts(news_id)
                record.update_record(admin_history = new_history + record.admin_history)
                msg = CENTER(B('News post updated.'), _style='color: green')
            elif 'create' in req_keys:
                record = db.news_posts(form.vars.id)
                record.update_record(admin_history = new_history)
                msg = CENTER(B('News post created.'), _style='color: green')
            else:
                pass
            
            session.flash = msg
            redirect(URL('news','news_details', args=form.vars.id))
            
        elif form.errors:
            response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
        else:
            pass
        
        # package form into a panel
        if record is None:
            vis = ""
        else:
            if record.hidden:
                vis = DIV('Hidden', _class='col-sm-1 col-sm-offset-4',
                          _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            else:
                vis = DIV('Visible', _class='col-sm-1 col-sm-offset-4',
                          _style='padding: 5px 15px 5px 15px;background-color:lightgrey;color:black;')
            
                      
        panel_header = DIV(H5('News post', _class='col-sm-7'), vis,
                           _class='row', _style='margin:0px 0px')
        
        form = FORM(form.custom.begin,
                    DIV(DIV(panel_header, _class="panel-heading"),
                        DIV(LABEL('Thumbnail Figure:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.thumbnail_figure, _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('Title:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.title, _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(LABEL('News post Content:', _class="control-label col-sm-2" ),
                            DIV(form.custom.widget.content,  _class="col-sm-10"),
                            _class='row', _style='margin:10px 10px'),
                        DIV(form.custom.submit, _class='panel-footer'),
                        _class="panel panel-primary"),
                        form.custom.end)
    else: 
        # security doesn't allow non admins to edit
        session.flash = CENTER(B('You do not have permission to edit news posts.'), _style='color: red')
        redirect(URL('news','news', args=news_id))
    
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
    
    # pass components to the view
    return dict(form=form,  admin_history=admin_history)


def validate_news_post(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.poster_id = auth.user_id
    form.vars.date_posted =  datetime.date.today().isoformat()



@auth.requires_membership('admin')
def news_hide():
    
    news_id = request.args(0)
    record = db.news_posts(news_id)
    if record.hidden:
        record.hidden = False
        new_history = '[{}] {} {}\\n ** News post un-hidden\\n'
    else:
        record.hidden = True
        new_history = '[{}] {} {}\\n ** News post hidden\\n'
    
    record.admin_history = new_history.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                                              auth.user.first_name,
                                              auth.user.last_name) + record.admin_history
    
    record.update_record()
    
    redirect(URL('news', 'manage_news'))
