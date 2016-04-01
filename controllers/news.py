import datetime
from fs.osfs import OSFS

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
    

## ADMIN

@auth.requires_membership('admin')
def manage_news():
    
    """
    Controller to allow admin to create, edit and delete news posts
    """
    
    links = [dict(header = '', body = lambda row: A(IMG(_src = URL('default', 
                  'download', args = row.thumbnail_figure), _height = 100)))]
                  
    # need these three fields in the fields list to allow the links
    # to be created but don't want to actually show them in the grid
    db.news_posts.thumbnail_figure.readable=False
    
    form = SQLFORM.grid(db.news_posts, csv=False, 
                        fields=[db.news_posts.thumbnail_figure,
                                db.news_posts.title,
                                db.news_posts.date_posted,
                                ],
                        maxtextlength=100,
                        create=True,
                        deletable=True,
                        editable=True, 
                        details=False, # just reveals a bunch of crappy html.
                        # searchable=False,
                        formargs={'showid':False,
                                  'fields': ['thumbnail_figure', 'title','content']},
                        editargs={'deletable':False},
                        links=links,
                        links_placement='left',
                        onvalidation = onvalidate_news_post,
                        oncreate = oncreate_news_post,
                        onupdate = onupdate_news_post
                        )
    
    return dict(form=form)


@auth.requires_membership('admin')
def oncreate_news_post(form):
    
    
    session.flash = CENTER(B('News post submitted.'), _style='color: green')


def onvalidate_news_post(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.poster_id = auth.user_id
    form.vars.date_posted =  datetime.date.today().isoformat()


@auth.requires_membership('admin')
def onupdate_news_post(form):
    
    session.flash = CENTER(B('News post edited.'), _style='color: green')
