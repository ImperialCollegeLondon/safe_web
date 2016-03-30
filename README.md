# SAFE website #

This is the bitbucket repository for the code underlying the SAFE website. The web application is written using the [web2py](http://web2py.com/) framework and is intended to work with the same database backend as the SAFE Earthcape database.

It is currently not fully running on any externally available IP address, although a version is running on pythonanywhere: [https://davidorme.pythonanywhere.com/SAFE_web/default/index](https://davidorme.pythonanywhere.com/SAFE_web/default/index)

## Deployment recipe ##

To be done



## web2py notes ##

### Plugins ###

It only uses [web2py_ckeditor4](https://github.com/timrichardson/web2py_ckeditor4/releases) to add a WYSIWYG interface for blogs and news.

### On SQLFORM.grid usage ###

SQLFORM.grid  provides a nice searchable view of a table contents. The function has a built in details view with a nice link button, and you can personalise that view
   
    def species():
      if request.args(0) == 'view':
         response.view = 'species/species_profile.html'

This is basically changing the behaviour for the `view` argument of the SQLFORM.grid controllers, so the resulting  URL is an extension of the grid controller name using arguments. For example:

    /controller/function/view/species_profile/id
   
Which is neat but means that you can't (not to my current knowledge) provide a direct link to the view page.

So.... instead, I've used SQLFORM.grid links to provide custom buttons to a separate controller for the view, passing the row.id to retrieve the row record and hence a standalone custom view.

### Languages ###

We potentially have Malay and English content, so need to separate the content of pages from the page. At the moment, this isn't 
 - Need to provide translation of menu headers
 - Provide switch on header to select language content
 - needs models/markmin.py
 
* Menu setup
 - Defined in models/menu.py
 
 * User approval - admin needs to OK new registrations
 
* Accessing external database
 - Need to set up ODBC and pyodbc for MSSQL, can use FreeTDS


- SAFE google account
    
    Mysafeproject@gmail.com
    safe5abah
    
 - Google group 
    - owned by Rob
    
Mail Chimp/Twitter/HootSuite

    - redesign 
    info@safeproject.net
    safe2011!
    
Server:
    host the wiki too.
    mail server: safeproject.net accounts

proposers group for projects - people who are emailed about new proposals.
bloggers group for adding new blog posts (using markmin?)

CRON JOB
automated email on project expiry to check it is closed and email members about database.
