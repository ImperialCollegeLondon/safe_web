# SAFE website #

This is the bitbucket repository for the code underlying the SAFE website. The web application is written using the [web2py](http://web2py.com/) framework and is intended to work with the same database backend as the SAFE Earthcape database.

## Deployment recipe ##


### Creating the AWS virtual machine and web interface ###

The overview is:

  1. Create and Amazon EC2 instance - the free tier options provide a reasonable processing and disk space
  2. In order to enable SSH, we're using the LetsEncrypt software and certification authority.
  3. The DB backend for the website is running in PostgreSQL on an Amazon RDS instance. This is so that the DB can be accessed by Earthcape as well as by the website, otherwise we could just run it from a local sqlite database.
  4. Backup. Amazon Cloudwatch allows scheduling of snapshots of the volume. These are incremental, so daily backups are just a matter of creating a rule on Cloudwatch. However, because the DB is external, that also needs backup, so we need to schedule a db dump into the volume, which can then be backed up by the snapshot.


### Connecting to the EC2 instance by SSH ###

You'll get a PEM file from Amazon when you create the EC2 instance. This is a key file that allows you to connect to your server via SSH. The only trick is that you need to make the file 'read only by owner' using `chmod` :

    # EC2 instance connection
    chmod 400 AWS_SAFE_Web.pem
    ssh -i AWS_SAFE_Web.pem ubuntu@ec2-52-51-38-168.eu-west-1.compute.amazonaws.com

**Note that this file contains the keys to the whole server** - it should not be saved anywhere publically accessible or shared with people outside the project admin.

### Enabling HTTPS ###

We're  using the LetsEncrypt open source certification. These commands install LetsEncrypt and load any required packages.

    git clone https://github.com/letsencrypt/letsencrypt
    cd letsencrypt
    ./letsencrypt-auto --help

This command then requests the certificate request, which will look up the IP address registered for the machine against the DN registrar and create the certificate:

    ./letsencrypt-auto --apache -d beta.safeproject.net

The installation creates an Apache site config file and enables it:

    /etc/apache2/sites-available/000-default-le-ssl.conf

This also point to a config include that turns on the SSL remapping of `http` to `https`:

    /etc/letsencrypt/options-ssl-apache.conf

However, in order to get http:// working, I had to edit the apache configuration to map anything coming  in to port 80 to get rewritten to a https:// request:

    <VirtualHost *:80>
            ServerAdmin webmaster@localhost
            ServerName beta.safeproject.net
    
            HostnameLookups Off
            UseCanonicalName On
            ServerSignature Off
    
            RewriteEngine On
            RewriteCond %{HTTPS} off
            RewriteRule (.*) https://%{SERVER_NAME}$1 [R,L]
    </VirtualHost>

So, any http request to this server is now forwarded on to use https, for all sites.

The installation suggests checking the resulting domain name using:

    https://www.ssllabs.com/ssltest/analyze.html?d=beta.safeproject.net


### Installing web2py ###

This downloads and runs a web2py script that sets sets up web2py, postgres, postfix and a bunch of other stuff and restarts Apache. This installation therefore sets up a machine that could run its own internal DB and mailserver, although AWS try to get you to use their RDS service, which isn't available for free.

    wget https://web2py.googlecode.com/hg/scripts/setup-web2py-ubuntu.sh
    chmod +x setup-web2py-ubuntu.sh
    sudo ./setup-web2py-ubuntu.sh

You then need to set the password for the admin web2py app to enable admin access via the web interface, which involves running a command from within the web2py python modules:

    cd /home/www-data/web2py
    sudo -u www-data python -c "from gluon.main import save_password; save_password(raw_input('admin password: '),443)"

#### Apache configuration ####

The installer creates and enables an apache2 configuration (`default.conf`) that sets a bunch of stuff. However, it tries to create a self signed certificate and create the VirtualHost entries, which have already been handled by LetsEncrypt. You therefore need a new configuration file that points apache2 to the correct directories to serve the website. All the information is in `default.conf` but wrapped in VirtualHost declarations. We're interested in the following, which tells Apache2 to map `www.servername.net/anything` to the web2py WSGI handler and allows the handler access to the content.

    WSGIDaemonProcess web2py user=www-data group=www-data processes=1 threads=1
    WSGIProcessGroup web2py
    WSGIScriptAlias / /home/www-data/web2py/wsgihandler.py
    WSGIPassAuthorization On
    
    <Directory /home/www-data/web2py>
      AllowOverride None
      Require all denied
      <Files wsgihandler.py>
        Require all granted
      </Files>
    </Directory>
    
    AliasMatch ^/([^/]+)/static/(?:_[\d]+.[\d]+.[\d]+/)?(.*) \ /home/www-data/web2py/applications/$1/static/$2
    
    <Directory /home/www-data/web2py/applications/*/static/>
      Options -Indexes
      ExpiresActive On
      ExpiresDefault "access plus 1 hour"
      Require all granted
    </Directory>

It all needs to go into `/etc/apache2/sites-available/web2py.conf` and then we need to switch out the old one. We also need to turn off the default `DocumentRoot` created by LetsEncrypt, so open up `/etc/apache2/sites-available/000-default-le-ssl.conf` and comment that line out and the reload apache2.

    sudo vi /etc/apache2/sites-available/000-default-le-ssl.conf
    # comment out the line: DocumentRoot /var/www/html
    sudo a2dissite default.conf
    sudo a2ensite web2py.conf 
    sudo service apache2 reload

After this the web2py interface should available at (e.g.)

    https://ec2-52-50-144-96.eu-west-1.compute.amazonaws.com/admin


### Setting the default application ###

To set the application at the root of the domain name, create a file called `routes.py` in the base of the web2py installation (_outside_ of the git repo) with the contents:

    routers = dict(
        BASE = dict(
            default_application='safe_web',
        )
    )

Then restart apache:

    sudo service apache2 restart

#### Python package management ####

For any extra python packages, you'll then need:

    sudo apt-get install python-pip

I didn't muck around with virtualenv for packages as these ones should probably should be globally available rather than just for the user www-data. I needed:

    sudo pip install gitpython 
    sudo pip install --upgrade google-api-python-client
    sudo pip install openpyxl
    sudo pip install fs

#### Deploying the web2py application from a bitbucket repo ####

First up, install git:

    sudo apt-get install git

Now clone the repo into the web2py applications folder. You could set up SSH, which gives the advantage of not needing to provide a password every time. However it is a pain to set up the keypairs and you'd expect that there are  going to be relatively infrequent roll outs of updated versions. So go with an clone via https, requiring your bitbucket password:

    cd /home/www-data/web2py/applications
    sudo -u www-data git clone https://davidorme@bitbucket.org/davidorme/safe_web.git

It is wise to disable the app from the admin site before updating! The web server provides a nice maintenance banner whilst it is disabled.


Updating from the repo requires the following:

    sudo git remote update
    sudo git pull


##### Resetting the DB in development NOT once in production #####

In production, the DB is the ultimate source of truth, but in the startup, this is populated from the zzz-fixtures.py file. Between major revisions in development, it is probably wise to purge the DB data and reload it:

1) In the DB, delete all the tables.

    # requires password
    psql -h earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com safe_web2py safe_admin

And then in SQL:

    -- this require write permission
    DROP SCHEMA public CASCADE;
    CREATE SCHEMA public;
    GRANT ALL ON SCHEMA public TO postgres;
    GRANT ALL ON SCHEMA public TO public;
    COMMENT ON SCHEMA public IS 'standard public schema';

or possibly, if you can't figure out what sets schema permissions

    -- may need to kill sessions attached to it
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = 'safe_web2py'
      AND pid <> pg_backend_pid();
    -- recreate
    \c template1
    drop database safe_web2py;
    create database safe_web2py;

2) In the file system the upload directory contains copies of files loaded in. These won't be purged by deleting the DB content, so avoid duplicating them on reload:

    cd uploads
    sudo find . -type f -delete
 
 3) Kill the databases files - they need to be regenerated when the DB is brought back up
 
    cd databases
    sudo rm *.table
    sudo rm sql.log

This should now be the DB empty of data, ready to repopulate everything, once the models run. You may also need to restart the server:

    sudo service apache2 restart

 Once the system is in production, of course, this is a disasterous thing to do. So need a snapshotting system to preserve the file
 structure and a db dump to preserve the DB contents.
 
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
    
    /**
     * SQL Support for Add User
     */
    
    $conf['plugin']['authpgsql']['addUser']     = "INSERT INTO auth_user
                                                     (email, password, first_name)
                                                   VALUES 
                                                     ('%{email}', '%{pass}', '%{name}')";
    $conf['plugin']['authpgsql']['addGroup']    = "INSERT INTO auth_group (role)
                                                   VALUES ('%{group}')";
    $conf['plugin']['authpgsql']['addUserGroup']= "INSERT INTO auth_membership (user_id, group_id)
                                                   VALUES ('%{uid}', '%{gid}')";
    $conf['plugin']['authpgsql']['delGroup']    = "DELETE FROM auth_group
                                                   WHERE group_id='%{gid}'";
    $conf['plugin']['authpgsql']['getUserID']   = "SELECT id AS id FROM auth_user WHERE email='%{user}'";
    $conf['plugin']['authpgsql']['getGroupID']  = "SELECT group_id AS id FROM auth_group WHERE role='%{group}'";
    

Once this has been set up, in the access control section of the Configuration Manager on Dokuwiki, change the `authtype` to  `authpgsql`. You'll be kicked out and need to log back in as a web2py admin user to make further changes.