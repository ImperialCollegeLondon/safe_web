# SAFE website #

This is the bitbucket repository for the code underlying the SAFE website. The web application is written using the [web2py](http://web2py.com/) framework and is intended to work with the same database backend as the SAFE Earthcape database.

## Deployment recipe ##


### Creating the AWS virtual machine and web interface ###

The overview is:

  1. Create and Amazon EC2 instance - the free tier options provide a reasonable processing and disk space
  2. In order to make 


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
#### Python package management ####

For any extra python packages, you'll then need:

    sudo apt-get install python-pip

I didn't muck around with virtualenv for packages as these ones should probably should be globally available rather than just for the user www-data. I needed:

    sudo pip install gitpython 
    sudo pip install --upgrade google-api-python-client
    sudo pip install openpyxl

#### Deploying the web2py application from a bitbucket repo ####

First up, install git:

    sudo apt-get install git

Now clone the repo into the web2py applications folder. You could set up SSH, which gives the advantage of not needing to provide a password every time. However it is a pain to set up the keypairs and you'd expect that there are  going to be relatively infrequent roll outs of updated versions. So go with an clone via https, requiring your bitbucket password:

    cd /home/www-data/web2py/applications
    sudo -u www-data git clone https://davidorme@bitbucket.org/davidorme/safe_web.git

#### web2py Plugins ####

The SAFE website only uses [web2py_ckeditor4](https://github.com/timrichardson/web2py_ckeditor4/releases) to add a WYSIWYG interface for blogs and news.

#### On SQLFORM.grid usage ####

SQLFORM.grid  provides a nice searchable view of a table contents. The function has a built in details view with a nice link button, and you can personalise that view
   
    def species():
      if request.args(0) == 'view':
         response.view = 'species/species_profile.html'

This is basically changing the behaviour for the `view` argument of the SQLFORM.grid controllers, so the resulting  URL is an extension of the grid controller name using arguments. For example:

    /controller/function/view/species_profile/id
   
Which is neat but means that you can't (not to my current knowledge) provide a direct link to the view page.

So.... instead, I've used SQLFORM.grid links to provide custom buttons to a separate controller for the view, passing the row.id to retrieve the row record and hence a standalone custom view.

#### Email templates ####

The email templating system is reasonbly tricky to get your head around. Basically, you create a new _view_, and then use the web2py rendering engine to generate the email. You can create an html message or plain text and make use of the web2py html helpers etc.

The gotchas are:

1. The template has to be in the views directory, and provided as a path relative to that, otherwise the code will tend to spit back the contents of generic.html. So for example:

        response.render('email_templates/project_submitted.html', dict(name='Fred'))

2. Don't try naming any arguments in `response.render()`. It just makes it angry.


#### Languages ####

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

### Deploying Dokuwiki ###

First, you will need to ssh into the EC2 instance:

    ssh -i AWS_SAFE_Web.pem ubuntu@ec2-52-50-144-96.eu-west-1.compute.amazonaws.com

Then, broadly following the instructions [here](https://www.dokuwiki.org/install:ubuntu)

 First, update the system and install / update web services:

    sudo apt-get update && sudo apt-get upgrade
    sudo apt-get install apache2 libapache2-mod-php5

Now enable the Apache Rewrite module in order to get cleaner URLs
 
    sudo a2enmod rewrite

Get and extract the latest dokuwiki tarball

    cd /home/www-data
    sudo wget http://download.dokuwiki.org/src/dokuwiki/dokuwiki-stable.tgz
    sudo tar xvf dokuwiki-stable.tgz
    sudo mv dokuwiki-*/ dokuwiki # rename the root directory
    sudo rm dokuwiki-stable.tgz
 
Now make all of that belong to the `www-data` user:

    sudo chown -R www-data:www-data /home/www-data/dokuwiki

Now create the following apache2 config file to lead URLs to dokuwiki:

    sudo -U www-data vi /home/www-data/dokuwiki/apache2.conf

With the following contents:

    AliasMatch ^/dokuwiki/sites/[^/]+$      /home/www-data/dokuwiki/
    AliasMatch ^/dokuwiki/sites/[^/]+/(.*)$ /home/www-data/dokuwiki/$1
    Alias      /dokuwiki                    /home/www-data/dokuwiki/
    
    <Directory /home/www-data/dokuwiki/>
    Options +FollowSymLinks
    AllowOverride All
    Require all granted
    
            <IfModule mod_rewrite.c>
    
                    # Uncomment to implement server-side URL rewriting
                    # (cf. <http://www.dokuwiki.org/config:userewrite>).
                            # Do *not* mix that with multisite!
                    #RewriteEngine on
                    #RewriteBase /dokuwiki
                    #RewriteRule ^lib                      - [L]
                    #RewriteRule ^doku.php                 - [L]
                    #RewriteRule ^feed.php                 - [L]
                    #RewriteRule ^_media/(.*)              lib/exe/fetch.php?media=$1  [QSA,L]
                    #RewriteRule ^_detail/(.*)             lib/exe/detail.php?media=$1 [QSA,L]
                    #RewriteRule ^_export/([^/]+)/(.*)     doku.php?do=export_$1&id=$2 [QSA,L]
                    #RewriteRule ^$                        doku.php  [L]
                    #RewriteRule (.*)                      doku.php?id=$1  [QSA,L]
            </IfModule>
    </Directory>
    
    <Directory /home/www-data/dokuwiki/bin>
            Require all denied
    </Directory>
    
    <Directory /home/www-data/dokuwiki/data>
            Require all denied
    </Directory>

Now link that into the list of sites available to apache2 and enable it:

    sudo ln apache2.conf /etc/apache2/sites-available/dokuwiki.conf
    sudo a2ensite dokuwiki
    sudo service apache2 restart
 
 That should expose the wiki site here:
 
    http://ec2-52-50-144-96.eu-west-1.compute.amazonaws.com/dokuwiki/install.php

The `install.php` site exposes an initial configuration page:

[https://www.dokuwiki.org/installer](https://www.dokuwiki.org/installer)
 
 It then needs to be deleted as it is an insecure  point of entry. 

    sudo rm /home/www-data/dokuwiki/install.php

The commented out rewrite rules in the apache2.conf file can now be uncommented to provide nicer looking links:

    sudo sed -i -e 's/^#Rewrite/Rewrite/' /home/www-data/dokuwiki/apache2.conf
    sudo service apache2 restart

Next, install extensions that will be used from the admin extension manager:

move (restrict to @admin in config),

#### Making Dokuwiki work with the Web2Py DB auth tables ####

This is a bit awkward as we need:

1. To get the two systems to agree on a password hashing format so that both can use the same table of hashed passwords.
2. To then set Dokuwiki up to read the remote PostgreSQL tables for users and to access hashed passwords.

#### Password hashing ####

I've created a new hashing method for Dokuwiki that allows it to authenticate against the default web2py hashing 

#### Remote connection ####

Firstly, in the Dokuwiki extension manager, enable the PostgreSQL Auth plugin and then install the require PHP modules to support it.

    sudo apt-get install php5-pgsql

We now need to configure the Dokuwiki `authpgsql` extension to correctly query the authorisation tables within the web2py database. First, there needs to be a group in the web2py `auth_group` table (`wiki_user`), and then change the default group in the Dokuwiki Configuration Manager to use `wiki_user` as the default group: a user then has to be a member of this group to be let into Dokuwiki.

The config file to map all this up is:

    /**
     * Example PgSQL Auth Plugin settings
     * See https://www.dokuwiki.org/plugin:authpgsql for details and explanation
     */
     
    /**
     * Options
     */
    $conf['authtype'] = "authpgsql";
    $conf['plugin']['authpgsql']['debug'] = 0;
    $conf['plugin']['authpgsql']['server'] = 'earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com';
    $conf['plugin']['authpgsql']['user'] = 'safe_admin';
    $conf['plugin']['authpgsql']['password'] = 'Safe2016';
    $conf['plugin']['authpgsql']['database'] = 'safe_web2py';
    $conf['plugin']['authpgsql']['forwardClearPass'] = 0;
     
    /**
     * SQL User Authentication
     */
     
    $conf['plugin']['authpgsql']['checkPass'] = "SELECT password
                                                 FROM auth_membership AS ug
                                                 JOIN auth_user AS u ON u.id = ug.user_id
                                                 JOIN auth_group AS g ON g.id = ug.group_id
                                                 WHERE u.email='%{user}'
                                                 AND g.role='%{dgroup}'";
    $conf['plugin']['authpgsql']['FilterLogin'] = "u.email LIKE '%{user}'";
    $conf['plugin']['authpgsql']['getUserInfo'] = "SELECT password, first_name || ' ' || last_name AS name, email AS mail
                                                   FROM auth_user
                                                   WHERE email='%{user}'";
    $conf['plugin']['authpgsql']['getGroups'] = "SELECT g.role as group
                                                 FROM auth_group g, auth_user u, auth_membership ug
                                                 WHERE u.id = ug.user_id
                                                   AND g.id = ug.group_id
                                                   AND u.email='%{user}'";
    					       
    $conf['plugin']['authpgsql']['getUsers'] = "SELECT DISTINCT u.email AS user
                                                FROM auth_user AS u 
                                                LEFT JOIN auth_membership AS ug ON u.id = ug.user_id
                                                LEFT JOIN auth_group AS g ON ug.group_id = g.id";
    
    $conf['plugin']['authpgsql']['FilterName']  = "u.fullname || '' || u.last_name LIKE '%{name}'";
    $conf['plugin']['authpgsql']['FilterEmail'] = "u.email LIKE '%{email}'";
    $conf['plugin']['authpgsql']['FilterGroup'] = "g.role LIKE '%{group}'";
    $conf['plugin']['authpgsql']['SortOrder']   = "ORDER BY u.email";


Once this has been set up, in the access control section of the Configuration Manager on Dokuwiki, change the `authtype` to  `authpgsql`. You'll be kicked out and need to log back in as a web2py admin user to make further changes.