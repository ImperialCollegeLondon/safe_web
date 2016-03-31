# SAFE website #

This is the bitbucket repository for the code underlying the SAFE website. The web application is written using the [web2py](http://web2py.com/) framework and is intended to work with the same database backend as the SAFE Earthcape database.

It is currently not fully running on any externally available IP address, although a version is running on pythonanywhere: [https://davidorme.pythonanywhere.com/SAFE_web/default/index](https://davidorme.pythonanywhere.com/SAFE_web/default/index)

## Deployment recipe ##

The website has been deployed on an AWC EC2 instance running Ubuntu 14.04 LTS . The following steps were used (once the instance was created):

### Connecting to the EC2 instance by SSH ###

You'll get a PEM file from Amazon when you create the EC2 instance. This is a key file that allows you to connect to your server via SSH. The only trick is that you need to make the file 'read only by owner' using `chmod` :

    # EC2 instance connection
    chmod 400 AWS_SAFE_Web.pem
    ssh -i AWS_SAFE_Web.pem ubuntu@ec2-52-50-144-96.eu-west-1.compute.amazonaws.com

### Installing web2py ###

This downloads and runs a web2py script that sets sets up web2py, postgres, postfix and a bunch of other stuff and restarts Apache. This installation therefore sets up a machine that could run its own internal DB and mailserver, although AWS try to get you to use their RDS service, which isn't available for free.

    wget https://web2py.googlecode.com/hg/scripts/setup-web2py-ubuntu.sh
    chmod +x setup-web2py-ubuntu.sh
    sudo ./setup-web2py-ubuntu.sh

You then need to set the password for the admin web2py app to enable admin access via the web interface, which involves running a command from within the web2py python modules:

    cd /home/www-data/web2py
    sudo -u www-data python -c "from gluon.main import save_password; save_password(raw_input('admin password: '),443)"

After this the web2py interface should available at (e.g.)

    https://ec2-52-50-144-96.eu-west-1.compute.amazonaws.com/admin

There are some issues here with the SSL certificate, so there may be warnings about https certificates. These need to be resolved by getting a trusted certificate for the site, which I haven't done yet.
### Python package management ###

For any extra python packages, you'll then need:

    sudo apt-get install python-pip

I didn't muck around with virtualenv for packages as these ones should probably should be globally available rather than just for the user www-data. I needed:

    sudo pip install gitpython 
    sudo pip install --upgrade google-api-python-client
    sudo pip install openpyxl

### Deploying the web2py application from a bitbucket repo###

First up, install git:

    sudo apt-get install git

Now clone the repo into the web2py applications folder. You could set up SSH, which gives the advantage of not needing to provide a password every time. However it is a pain to set up the keypairs and you'd expect that there are  going to be relatively infrequent roll outs of updated versions. So go with an clone via https, requiring your bitbucket password:

    cd /home/www-data/web2py/applications
    sudo -u www-data git clone https://davidorme@bitbucket.org/davidorme/safe_web.git


## web2py notes ##

### Plugins ###

The SAFE website only uses [web2py_ckeditor4](https://github.com/timrichardson/web2py_ckeditor4/releases) to add a WYSIWYG interface for blogs and news.

### On SQLFORM.grid usage ###

SQLFORM.grid  provides a nice searchable view of a table contents. The function has a built in details view with a nice link button, and you can personalise that view
   
    def species():
      if request.args(0) == 'view':
         response.view = 'species/species_profile.html'

This is basically changing the behaviour for the `view` argument of the SQLFORM.grid controllers, so the resulting  URL is an extension of the grid controller name using arguments. For example:

    /controller/function/view/species_profile/id
   
Which is neat but means that you can't (not to my current knowledge) provide a direct link to the view page.

So.... instead, I've used SQLFORM.grid links to provide custom buttons to a separate controller for the view, passing the row.id to retrieve the row record and hence a standalone custom view.

### Email templates ###

The email templating system is reasonbly tricky to get your head around. Basically, you create a new _view_, and then use the web2py rendering engine to generate the email. You can create an html message or plain text and make use of the web2py html helpers etc.

The gotchas are:

1. The template has to be in the views directory, and provided as a path relative to that, otherwise the code will tend to spit back the contents of generic.html. So for example:

        response.render('email_templates/project_submitted.html', dict(name='Fred'))

2. Don't try naming any arguments in `response.render()`. It just makes it angry.


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
