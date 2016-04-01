## -----------------------------------------------------------------------------
## BLOG
## - public controllers to view blog list and details
## - restricted controller to post new blogs
## -----------------------------------------------------------------------------


def blogs():
    
    links = [dict(header = '', body = lambda row: A(IMG(_src = URL('default', 
                  'download', args = row.thumbnail_figure), _height = 100))),
             dict(header = '', 
                  body = lambda row: A(SPAN('',_class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"),
                                       SPAN('View', _class="buttontext button"),
                                       _class="button btn btn-default", 
                                       _href=URL("blog","blog_post", args=[row.id], user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;'))] 
    
    db.blog_posts.thumbnail_figure.readable=False
    
    form = SQLFORM.grid(db.blog_posts, 
                        fields=[db.blog_posts.thumbnail_figure,
                                db.blog_posts.title,
                                db.blog_posts.date_posted],
                        orderby= ~ db.blog_posts.date_posted,
                        maxtextlength=150,
                        links=links,
                        links_placement='left',
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
    blog_post = db(db.blog_posts.id == blog_id).select()[0]
    
    return dict(blog_post = blog_post)
    

@auth.requires_membership('bloggers')
def new_blog_post():
    
    form = SQLFORM(db.blog_posts,
                   fields=['thumbnail_figure','authors','title','content'])
    
    if form.process(onvalidation=validate_blog_post).accepted:
        response.flash = CENTER(B('Blog post submitted.'), _style='color: green')
    else:
        response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
    
    return dict(form=form)


def validate_blog_post(form):
    
    # validation handles any checking and also any 
    # amendments to the form variable  - adding user and date 
    form.vars.poster_id = auth.user_id
    form.vars.date_posted =  datetime.date.today().isoformat()


def edit_blog_post():
    
    """
    This allows a non-admin user to edit a blog post - it is currently accessed
    from the blog post itself via a link only made visible to the owner
    """
    
    # edits a requested blog post
    blog_id = request.args(0)
    
    # internal security check - could move to decorator
    blog_record = db.blog_posts(blog_id)
    if blog_record.poster_id <> auth.user.id:
        response.flash = CENTER(B('Attempt to edit blog post that you do not own.'), _style='color: red')
        redirect(URL('blog','blogs', args=blog_id))
        return
    
    form = SQLFORM(db.blog_posts, blog_id,
                   fields=['thumbnail_figure','authors','title','content'], 
                   showid=False)
    
    if form.process(onvalidation=validate_blog_post).accepted:
        session.flash = CENTER(B('Blog post edited.'), _style='color: green')
        redirect(URL('blog','blogs', args=blog_id))
    else:
        response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
    
    return dict(form=form)

@auth.requires_membership('admin')
def manage_blogs():
    
    """
    Controller to allow admin to create, edit and delete blogs
    """
    
    links = [dict(header = '', body = lambda row: A(IMG(_src = URL('default', 
                  'download', args = row.thumbnail_figure), _height = 100)))]
                  
    # need these three fields in the fields list to allow the links
    # to be created but don't want to actually show them in the grid
    db.blog_posts.thumbnail_figure.readable=False
    
    form = SQLFORM.grid(db.blog_posts, csv=False, 
                        fields=[db.blog_posts.thumbnail_figure,
                                db.blog_posts.title,
                                db.blog_posts.date_posted,
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
                        onvalidation = validate_blog_post,
                        oncreate = oncreate_blog_post,
                        onupdate = onupdate_blog_post
                        )
    
    return dict(form=form)

# these functions provide simple info back to the manage_blogs Admin view 

@auth.requires_membership('admin')
def oncreate_blog_post(form):
    
    
    session.flash = CENTER(B('Blog post created.'), _style='color: green')


@auth.requires_membership('admin')
def onupdate_blog_post(form):
    
    session.flash = CENTER(B('Blog edited.'), _style='color: green')

