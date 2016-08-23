# SAFE website and deployment recipe#

This is the bitbucket repository for the code underlying the SAFE website. The web application is written using the [web2py](http://web2py.com/) framework and is intended to work alongside a database for the SAFE Earthcape database. In practice, using the _same_ DB backend involves too many hacks to both systems and made everything more fragile.


### Creating the AWS virtual machine and web interface ###

The overview is:

  1. Create and Amazon EC2 instance - the free tier options provide a reasonable processing and disk space
  2. In order to enable SSH, we're using the LetsEncrypt software and certification authority.
  3. The DB backend for the website is running in PostgreSQL on an Amazon RDS instance. This is so that the DB can be accessed by Earthcape as well as by the website, otherwise we could just run it from a local sqlite database.
  4. Backup. Amazon Cloudwatch allows scheduling of snapshots of the volume. These are incremental, so daily backups are just a matter of creating a rule on Cloudwatch. However, because the DB is external, that also needs backup, so we need to schedule a db dump into the volume, which can then be backed up by the snapshot.

## EC2 setup ##

You need to setup an EC2 account and then walk through creating a new EC2 instance running `linux`: I've used Ubuntu 14.04 LTS.  This is all done through the browser UI.  Make sure to **tag the instance with the name 'SAFE Webserver'**, as this tag is used to identify the server instance for some of the automatic steps below. Also make sure you setup the security rules to allow the server to listen to all HTTP, SSH and HTTPS requests. The website will redirect http to https but we'll get to that later.

This gives you a virtual server, and in the process of creating it you'll get a key file (`.pem`), that allows you to connect to the server remotely via SSH. This allows you to then set up other aspects of the server:

  1. Once a VM instance is up and running, it has some hard drive space and an IP address, so you can theoretically run everything from there. But... you need to think of them as temporary and substitutable: the disk space associated with the root device on an instance **does not persist** if the instance is shut down **nor does the IP address**. So you can run everything from it, but if the instance is stopped for any reason, you've got to start over and you've probably lost data.
    So, we need a couple of extra resources:
  2. **A data volume** which we can attach to our VM instance. This then acts as a drive that the VM can use for storage but it also persistent: if the VM goes down, the attached volume is preserved. It can also be backed up automatically to provide recovery (see below).
  3. ** An elastic IP**, which is a mechanism to link the IP of a VM instance (lost at VM shutdown) to a permanent IP. In the event of a crash, you can switch the VM linked to the IP to the new VM and carry on as before.

So. First, connect to the EC2 Instance and install some tools. For reproducability, the AWS command line interface is used to set up these components.

You willl need to get the public DNS name for the instance from the EC2 Dashboard. You will also need the PEM file and - because the operating system is extremely cautious about these files and who can edit and view them - you may need to make it 'read only by owner' using `chmod` :

    # EC2 instance connection
    chmod 400 AWS_SAFE_Web.pem
    ssh -i AWS_SAFE_Web.pem ubuntu@ec2-52-210-141-41.eu-west-1.compute.amazonaws.com

**Note that this file contains the keys to the whole server** - it should not be saved anywhere publically accessible or shared with people outside the project admin.


### Identity and Access Managment (IAM ) setup

To use command line tools and protect the server, you need to setup users and groups through the IAM web console. You will need to create a developer group with the AdministratorAccess Policy and then create and add a user to this group. Note down (or download) the secret keys associated with the user in order to do the next step.

### Set up command line tools 

We need to install the command line tools from `apt-get` and then configure them. You'll need the user credentials associated with your EC2 account to configure the tools.

    sudo apt-get install awscli
    aws configure # and enter secret details
    
    # install pip and a python package to script tools
    sudo apt-get update
    sudo apt-get install python-pip
    sudo pip install boto3

### Creating the data volume

Once you're logged in via SSH and have set up the AWS CLI tools, then we can use python to create and attach a storage volume to the instance. The AWS CLI tools have a shell interface (`aws ec2 ...`) but because the script gets responses in JSON format, it is easier to use the python boto3 interface, which handles the responses as Python dictionaries.

The python scripty below creates a  new Elastic Block Storage (EBS) volume, which is just a fancy name for a virtual hard drive that works directly with your VM instance. The free tier for AWS comes with 30GB of EBS storage and the default VM uses 8GB (which might be excessive), so this can be ~20GB without running up costs. It then attaches it to the instance tagged with the name `SAFE Webserver`.

    python launch_and_attach_data_volume.py

The volume now exists as a device (`/dev/xvdb` is used in the script) on the instance, but doesn't have a file system and isn't mounted. So:

    sudo mkfs -t ext4 /dev/xvdb
    sudo mkdir /home/www-data
    sudo mount /dev/xvdb /home/www-data

### Installing web2py ###

This downloads and runs a web2py script that sets sets up web2py, postgres, postfix and a bunch of other stuff and restarts Apache. This installation therefore sets up a machine that could run its own internal DB and mailserver, although AWS try to get you to use their RDS service, which isn't available for free.

    cd /home/www-data
    sudo wget https://raw.githubusercontent.com/web2py/web2py/master/scripts/setup-web2py-ubuntu.sh
    sudo chmod +x setup-web2py-ubuntu.sh
    sudo ./setup-web2py-ubuntu.sh

As part of this script you have the opportunity to configure postfix for email (choose None in the configuration options) and to configure a SSL certificate to allow HTTPS. This self-signed certificate is basically worthless.

You then need to set the password for the admin web2py app to enable admin access via the web interface, which involves running a command from within the web2py python modules:

    cd /home/www-data/web2py
    sudo -u www-data python -c "from gluon.main import save_password; save_password(raw_input('admin password: '),443)"


### Update PostgreSQL

At the time of writing, the AWS Ubuntu is 14.04 LTS, which installs postgresql 9.3 but the AWS RDS servers run 9.4. This isn't a problem except if we want to use the `pg_dump` command on the webserver to create a remote dump of the DB. This is a bit paranoid, since the RDS servers keep daily backups for 7 days, but you can't be too careful.

1. Stop the 9.3 Server and remove the package

        sudo /etc/init.d/postgresql stop
        sudo apt-get --purge remove postgresql\*

2. Create the file /etc/apt/sources.list.d/pgdg.list, and add a line for the repository  

        deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main

3. Get the packages available from that repo:

        wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
        sudo apt-get update

4. Install the version specific apt package

        sudo apt-get install postgresql-9.4

### Section progress report #1

At this point, we should have a webserver running web2py with the default applications. However at the moment, it is only accessible via the Public DNS of the VM instance. If you copy that from the EC2 console into the browser, you should see the welcome to web2py application.

If you try going to https://<public dns>, you'll get warnings about the certificate not being trusted. We need a proper certificate from a trusted authority to enable HTTPS but before we do that, we'll get the web application up and running

## Deploying the web application

This is basically just a matter of cloning the repository and then setting up the configuration for the application running on this server.

### Install python modules

The application needs a few extra python modules. I didn't muck around with virtualenv for packages as these ones should probably should be globally available rather than just for the user www-data. I needed:

    sudo pip install gitpython 
    sudo pip install --upgrade google-api-python-client
    sudo pip install openpyxl
    sudo pip install fs
    sudo pip install html2text

### Initial deployment 

**Read the next statement very carefully**: The SAFE web application is deploying a lot of existing data, so the first deployment calls some code to copy across existing files and to load the database with legacy data from the previous system. This code is only needed once at **initial deployment**. The code in this section assumes that this is what you're doing - essentially a bunch of stuff that is only used while the application is in development. If you follow this section once the application has actually been live, you're burning down a live system. The recovery plan for the production system is **very** different and is described below.

OK. So warning over. First up, install git:

    sudo apt-get install git

Now clone the repo into the web2py applications folder. You could set up SSH, which gives the advantage of not needing to provide a password every time. However it is a pain to set up the keypairs and you'd expect that there are  going to be relatively infrequent roll outs of updated versions. So go with an clone via https, requiring your bitbucket password:

    cd /home/www-data/web2py/applications
    sudo -u www-data git clone https://davidorme@bitbucket.org/davidorme/safe_web.git

Before the application can work, we need to setup the database backend and edit the `appconfig.ini` file for the application to point to this database and to the correct SMTP server to send mail.

  1. **Create the DB**. Currently we are using a PostgreSQL DB running on an AWS Relational Database Server (RDS) set up by Evgeniy for the Earthcape database. We need to create a database instance on this called `safe_web2py`. So, log into the server (you will need the password for the RDS user `safe_admin`):
 
    psql -h earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com template1 -U safe_admin
    create database safe_web2py;

Quit from the `psql` terminal using the command `\q`. If the database already exists then *think very hard about what you're doing* and look at the section below on resetting the database during development:

   2. **Edit the appconfig**. We now need to point the application to the database backend.
   
    cd /home/www-data/web2py/applications/safe_web/private/
    sudo cp appconfig_template.ini appconfig.ini
    sudo vi appconfig.ini

Edit that using `vi` to fill in the details for the DB and SMTP.

  3. **Cross your fingers**. The URL http://<Public DNS>/safe_web/default/index should now open the web application. There will be a delay as on the initial deployment, the application has to run the file `model/zzz_fixtures.py`, which is responsible for loading all the legacy data.

### Setting the default application 

Rather than including `safe\_web` in every URL, we can set a default application for the web2py server. Create a file called `routes.py` in the base of the web2py installation (_outside_ of the git repo) with the contents:

    routers = dict(
        BASE = dict(
            default_application='safe_web',
        )
    )

Then restart apache:

    sudo service apache2 restart

### Section progress report #2

We've now got a live web application running on the Public DNS of an AWS EC2 server. Now what we need to do is to associate the instance with the IP of an Elastic IP address and to setup a secure HTTPS certificate. 

## Making the site use https://www.safeproject.net

### Elastic IP Address

The Elastic IP address can be created programatically but then has to be associated with the DNS entry for https://www.safeproject.net. This has already been done, so the next step is to connect the new instance to that Elastic IP. The script below uses Python and boto3 again:

    python attach_instance_to_elastic_ip.py

At this point, the IP address for your instance has been changed, so your SSH connection will terminate!

### Fix the HTTPS connection

We're  using the LetsEncrypt open source certification. These commands install LetsEncrypt and load any required packages.

    ssh -i AWS_SAFE_Web.pem ubuntu@beta.safeproject.net
    cd /home/www-data/
    git clone https://github.com/letsencrypt/letsencrypt
    cd letsencrypt
    ./letsencrypt-auto --help

The next command then requests the certificate request, which will look up the IP address registered for the machine against the DN registrar and create the certificate. You will need to specify a contact email for emergencies and should specify that all HTTP traffic is redirected to HTTPS.

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

So, any http request to this server is now forwarded on to use https, for all sites. Now reload it:

    sudo service apache2 reload

The installation suggests checking the resulting domain name using:

    https://www.ssllabs.com/ssltest/analyze.html?d=beta.safeproject.net


### Fix the Apache configuration 

We now have a valid HTTPS vertificate but the installer has broken the link that directs Apache to the web2py server, so we need to fix that up.

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
    
    AliasMatch ^/([^/]+)/static/(?:_[\d]+.[\d]+.[\d]+/)?(.*) /home/www-data/web2py/applications/$1/static/$2
    
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


## Install Dokuwiki

First, you will need to ssh into the EC2 instance:

    ssh -i AWS_SAFE_Web.pem ubuntu@beta.safeproject.net

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

    cd /home/www-data/dokuwiki/
    sudo -u www-data vi apache2.conf

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

Now copy that into the list of sites available to apache2 and enable it:

    sudo cp apache2.conf /etc/apache2/sites-available/dokuwiki.conf
    sudo a2ensite dokuwiki
    sudo service apache2 restart
 
 That should expose the wiki site here:
 
    http://beta.safeproject.net/dokuwiki/install.php

The `install.php` site exposes an initial configuration page:

[https://www.dokuwiki.org/installer](https://www.dokuwiki.org/installer)
 
 It then needs to be deleted as it is an insecure  point of entry. 

    sudo rm /home/www-data/dokuwiki/install.php

The commented out rewrite rules in the apache2.conf file can now be uncommented to provide nicer looking links:

    sudo sed -i -e 's/^#Rewrite/Rewrite/' /etc/apache2/sites-available/dokuwiki.conf
    sudo service apache2 restart

Next, install extensions that will be used from the admin extension manager:

    move (restrict to @admin in config),
    etc


## Resetting the DB in development 

As noted above, in production, the DB is the ultimate source of truth, but in the startup, this is populated from the `zzz_fixtures.py file`. In order to reset the development version, the following steps are used. It is wise to disable the app from the web2py admin site before updating! The web server provides a nice maintenance banner whilst it is disabled.


  1. Update the code from the repo using the following:  
  
    sudo git remote update
    sudo git pull

  2. In the DB, delete all the tables and recreate the db (as above): 
  
    # requires password
    psql -h earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com template1 safe_admin

And then in SQL:

    -- may need to kill sessions attached to it
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = 'safe_web2py'
      AND pid <> pg_backend_pid();
    -- recreate
    drop database safe_web2py;
    create database safe_web2py;

  3. In the file system the upload directory contains copies of files loaded in. These won't be purged by deleting the DB content, so avoid duplicating them on reload: 
  
    cd /home/www-data/web2py/applications/safe_web/uploads
    sudo find . -type f -delete
 
  4. Kill the web2py databases table description files - they need to be regenerated when the DB is brought back up
 
    cd /home/www-data/web2py/applications/safe_web/databases
    sudo rm *.table
    sudo rm sql.log

This should now be the DB empty of data, ready to repopulate everything, once the models run. You may also need to restart the server:

    sudo service apache2 restart

**Remember**: once the system is in production this is a disasterous thing to do and you should use the production reset recipe.

## Backup and restore in production

We want to do two things: i) copy the contents of database out of the RDS and onto the  volume mounted at `/home/www-data`; and then ii) use the AWS snapshot mechanism to backup the volume.

There is a built in AWS service called Lambda that allows scheduling and functions but it is quite tricky to use. As long as we are dealing with a single VM, it is probably easier to use `cron` or something similar. The web application code repository contains a couple of scripts under `private/aws_setup` which can be added to `crontab` to automate this.


These two webpages give some good instructions on how you might do this with Lambda and provide a python backup script that I've ruthlessly repurposed:

https://serverlesscode.com/post/lambda-schedule-ebs-snapshot-backups/
https://serverlesscode.com/post/lambda-schedule-ebs-snapshot-backups-2/

Rather than doing stuff using `sudo` all the time, we'll give the default EC2 user `ubuntu` access to the `www-data` group and allow any group members to write to the `/home/www-data` folder.

    sudo usermod -a -G www-data ubuntu
    sudo chown -R www-data /home/www-data
    sudo chgrp -R www-data /home/www-data
    sudo chmod -R g+w /home/www-data

    sudo find /home/www-data -type d -exec chmod 2775 {} \;
    sudo find /home/www-data -type f -exec chmod ug+rw {} \;

Note that you have to logout and log back in again for this to have an effect! We can now use the `ubuntu` user account to run backups.

### Remote backup of the PostgreSQL DB

The RDS server keeps a daily backup of databases with 7 day retention, but keeping a local copy seems like a sensible strategy. This means a remote dump of the database, which is fine for such a small payload (5 years of legacy data is ~ 1.2 Mb as raw SQL, ~500Kb as compressed format). 

In order to automate this, we need to create a file `.pgpass` in the `ubuntu` user's home directory containing connection credentials - you can't set the connection password directly in the `pg_dump` command. The contents should be:

    # e.g. hostname:port:database:username:password
    earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com:*:safe_web2py:safe_admin:password

The file needs to have permissions set:

    chmod 0600 ~/.pgpass

We want the dump to be written to the volume that is about to be backed up, which is mounted at `/home/www-data`, so we should let the backup be handled by the user `www-data`. 

  1. Create a backup directory
  
    sudo mkdir safe_web2py_psql_dump

  2. Configure cron to run the backup script every day in the small hours
  
    (crontab -l ; echo "23 3 * * * python  /home/www-data/web2py/applications/safe_web/private/aws_setup/db_remote_dump.py >> /home/www-data/db_remote_dump.log 2>&1") | crontab -

  3. Edit the system log setup to keep a specific cron log
  
    sudo vi /etc/rsyslog.d/50-default.conf
    # uncomment the cron line
    sudo service rsyslog restart

### Snapshots of the data volume

AWS has a Snapshot facility that allows you to take a copy of a volume. These volumes are iterative backups, so can quickly capture new files, and when they are deleted the mechanism only removes the link to a particular version, not the underlying files.

A python script `data_backup_and_rotate.py` is included in the application under `private/aws_setup`, which can be added to the crontab in order to maintain snapshots.

    (crontab -l ; echo "47 3 * * * python  /home/www-data/web2py/applications/safe_web/private/aws_setup/data_backup_and_rotate.py >> /home/www-data/data_backup_and_rotate.log 2>&1") | crontab -

### Monitoring the backup process

The file `/var/log/cron.log` shows the processes being executed and the two log files in `/home/www-data` show the messages from the scripts.


## Random disorganised thoughts

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





.
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





