import datetime

## -----------------------------------------------------------------------------
## NEWS
## - public controllers to view news list and details
## - restricted controller to post new news items
## -----------------------------------------------------------------------------


def news():
    
    links = [dict(header = '', body = lambda row: A(IMG(_src = URL('default', 
                  'download', args = row.thumbnail_figure), _height = 100))),
             dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                       SPAN('View', _class="buttontext button"),
                                       _class="button btn btn-default", 
                                       _href=URL("news","news_post", args=[row.id], user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;'))]
    
    db.news_posts.thumbnail_figure.readable=False
    
    form = SQLFORM.grid(db.news_posts, 
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
    news_post = db(db.news_posts.id == news_id).select()[0]
    
    return dict(news_post = news_post)
    

@auth.requires_membership('admin')
def new_news_post():
    
    # set where the controller is going to save uploads
    ckeditor.settings.uploadfs = 'uploads/news'
    
    form = SQLFORM(db.news_posts,
                   fields=['thumbnail_figure','title','content'])
    
    if form.process(onvalidation=validate_new_news_post).accepted:
        response.flash = CENTER(B('News post submitted.'), _style='color: green')
    else:
        response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
    
    return dict(form=form)


def validate_new_news_post(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.poster_id = auth.user_id
    form.vars.date_posted =  datetime.date.today().isoformat()


@auth.requires_membership('admin')
def edit_news_post():
    
    # edits a requested news post
    news_id = request.args(0)
    
    form = SQLFORM(db.news_posts, news_id,
                   fields=['thumbnail_figure','title','content'], 
                   showid=False)
    
    # Note - no validation, don't want to overwrite original poster/date
    if form.process().accepted:
        session.flash = CENTER(B('News post edited.'), _style='color: green')
        redirect(URL('news','news_post', args=news_id))
    else:
        response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
    
    return dict(form=form)

