# -*- coding: utf-8 -*-

## ----------------------------------------------------------------------------
## File is released under public domain and you can use without limitations
## ----------------------------------------------------------------------------

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

import uuid

## app configuration made easy. Look inside private/appconfig.ini
from gluon.contrib.appconfig import AppConfig
# from gluon.tools import Recaptcha

import base64

## once in production, remove reload=True to gain full speed
myconf = AppConfig(reload=True)

## ----------------------------------------------------------------------------
## DB connection definitions
## -- both connections (local/remote) need to have a created database in order
##    to create and populate tables
## ----------------------------------------------------------------------------

# PG LOCAL setup
connection = "postgres://test:test@localhost/safe_web2py"

# PG REMOTE setup
# - this is a link to an AWS RDS instance, which could then be shared by Earthcape
# connection = "postgres://safe_admin:Safe2016@earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com/safe_web2py"

# # MYSQL database on python_anywhere testing environment
# connection = "mysql://DavidOrme:MonteCarloOrBust@DavidOrme.mysql.pythonanywhere-services.com/DavidOrme$safe_web2py"

db = DAL(connection, lazy_tables=False, pool_size=5)

# TODO - look at the myconf.take functionality and config file rather than hard coding
# db = DAL(myconf.take('db.uri'), pool_size=myconf.take('db.pool_size', cast=int), check_reserved=['all'])


## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## choose a style for forms
response.formstyle = myconf.take('forms.formstyle')  # or 'bootstrap3_stacked' or 'bootstrap2' or other
response.form_label_separator = myconf.take('forms.separator')

## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'
## (optional) static assets folder versioning
# response.static_version = '0.0.0'

## ----------------------------------------------------------------------------
## ENABLE AUTH
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## ----------------------------------------------------------------------------


def _simple_hash(text, key='', salt='', digest_alg='md5'):
    # """
    # Generates hash with the given text using the specified
    # digest hashing algorithm
    # """
    # if not digest_alg:
    #     raise RuntimeError("simple_hash with digest_alg=None")
    # elif not isinstance(digest_alg, str):  # manual approach
    #     h = digest_alg(text + key + salt)
    # elif digest_alg.startswith('pbkdf2'):  # latest and coolest!
    #     iterations, keylen, alg = digest_alg[7:-1].split(',')
    #     return pbkdf2_hex(text, salt, int(iterations),
    #                       int(keylen), get_digest(alg))
    # elif key:  # use hmac
    #     digest_alg = get_digest(digest_alg)
    #     h = hmac.new(key + salt, text, digest_alg)
    # else:  # compatible with third party systems
    #     h = get_digest(digest_alg)()
    #     h.update(text + salt)
    # return h.hexdigest()
    return 'leopards'

from gluon.tools import Auth #, Service, PluginManager

auth = Auth(db)
# service = Service()
# plugins = PluginManager()


## -----------------------------------------------------------------------------
## EXTEND THE USER TABLE DEFINITION
## -- defaults are: first_name, last_name, email, password
##                  registration_key, reset_password_key, registration_id
## -- legacy_user_id is purely for matching up imported users
## -- integrate ORCid login
## -- TODO - phone number formatting
## -- TODO - enforcing not null - problematic with upload of legacy users
## -----------------------------------------------------------------------------

academic_status_set = ['Undergraduate', 'Masters Student',
                       'PhD Student', 'Postdoc', 'Research Fellow', 'Faculty',
                       'Volunteer', 'Other', 'SAFE Research Assistant']

titles_set = [None, 'Dr','Prof', 'Assist. Prof', 'Assoc. Prof']

auth.settings.extra_fields['auth_user']= [
    Field('uuid', length=64, default=uuid.uuid4), # user OID
    Field('title', 'string', requires=IS_IN_SET(titles_set)), 
    Field('nationality', 'string'),
    Field('academic_status', 'string', requires=IS_IN_SET(academic_status_set)),
    Field('orcid', 'string'),
    Field('phone', 'string'),
    Field('mobile_phone', 'string'),
    Field('alternative_email', 'string', requires=IS_EMPTY_OR(IS_EMAIL())),
    Field('institution', 'string'),
    Field('institution_address', 'string'),
    Field('institution_phone', 'string'),
    Field('supervisor_id', 'reference auth_user'),
    Field('legacy_user_id','integer'),
    Field('h_and_s_id', 'integer')]

## create auth tables 
auth.define_tables(username=False, signature=False)

## suppress the legacy_user_id field as a general rule
db.auth_user.legacy_user_id.readable = False
db.auth_user.legacy_user_id.writable = False

# don't let users edit the link to H&S
db.auth_user.h_and_s_id.readable = False
db.auth_user.h_and_s_id.writable = False

# turn user emails into email links
db.auth_user.email.represent = lambda value, row: A(value, _href='mailto:{}'.format(value))

# provide links to user directory for logged in users
# set a string formatting for representing user ID
db.auth_user._format = '%(last_name)s, %(first_name)s'

# make the choice of supervisor a dropdown.
db.auth_user.supervisor_id.requires = IS_EMPTY_OR(IS_IN_DB(db, 'auth_user.id', db.auth_user._format))

db.auth_user.password.requires = CRYPT(digest_alg='sha512')

# code to try and integrate the Earthcape password formatting
from gluon.utils import web2py_uuid, DIGEST_ALG_BY_SIZE
import hashlib
from hashlib import sha512

class safeCRYPT(object):
    """
    This is a local redefinition of the password validator that reverses
    the ordering of salt and password to allow matching of password hashes
    between web2py and Earthcape. See validators.py in web2py for the full 
    details of the class definition
    """

    def __init__(self,
                 key=None,
                 digest_alg='pbkdf2(1000,20,sha512)',
                 min_length=0,
                 error_message='Too short', salt=True,
                 max_length=1024):

        self.key = key
        self.digest_alg = digest_alg
        self.min_length = min_length
        self.max_length = max_length
        self.error_message = error_message
        self.salt = salt

    def __call__(self, value):
        v = value and str(value)[:self.max_length]
        if not v or len(v) < self.min_length:
            return ('', translate(self.error_message))
        if isinstance(value, safeLazyCrypt):
            return (value, None)
        return (safeLazyCrypt(self, value), None)

class safeLazyCrypt(object):
    """
    Stores a lazy password hash
    """
    def __init__(self, crypt, password):
        """
        crypt is an instance of the CRYPT validator,
        password is the password as inserted by the user
        """
        self.crypt = crypt
        self.password = password
        self.crypted = None

    def __str__(self):
        """
        Encrypted self.password and caches it in self.crypted.
        If self.crypt.salt the output is in the format <algorithm>$<salt>$<hash>

        Try get the digest_alg from the key (if it exists)
        else assume the default digest_alg. If not key at all, set key=''

        If a salt is specified use it, if salt is True, set salt to uuid
        (this should all be backward compatible)

        Options:
        key = 'uuid'
        key = 'md5:uuid'
        key = 'sha512:uuid'
        ...
        key = 'pbkdf2(1000,64,sha512):uuid' 1000 iterations and 64 chars length
        """
        if self.crypted:
            return self.crypted
        if self.crypt.key:
            if ':' in self.crypt.key:
                digest_alg, key = self.crypt.key.split(':', 1)
            else:
                digest_alg, key = self.crypt.digest_alg, self.crypt.key
        else:
            digest_alg, key = self.crypt.digest_alg, ''
        if self.crypt.salt:
            if self.crypt.salt == True:
                salt = str(web2py_uuid()).replace('-', '')[-16:]
            else:
                salt = self.crypt.salt
        else:
            salt = ''
        hashed = safe_simple_hash(self.password, key, salt, digest_alg)
        self.crypted = '%s$%s$%s' % (digest_alg, salt, hashed)
        return self.crypted

    def __eq__(self, stored_password):
        """
        compares the current lazy crypted password with a stored password
        """

        # LazyCrypt objects comparison
        if isinstance(stored_password, self.__class__):
            return ((self is stored_password) or
                   ((self.crypt.key == stored_password.crypt.key) and
                   (self.password == stored_password.password)))

        if self.crypt.key:
            if ':' in self.crypt.key:
                key = self.crypt.key.split(':')[1]
            else:
                key = self.crypt.key
        else:
            key = ''
        if stored_password is None:
            return False
        elif stored_password.count('$') == 2:
            (digest_alg, salt, hash) = stored_password.split('$')
            h = safe_simple_hash(self.password, key, salt, digest_alg)
            temp_pass = '%s$%s$%s' % (digest_alg, salt, h)
        else:  # no salting
            # guess digest_alg
            digest_alg = DIGEST_ALG_BY_SIZE.get(len(stored_password), None)
            if not digest_alg:
                return False
            else:
                temp_pass = safe_simple_hash(self.password, key, '', digest_alg)
        return temp_pass == stored_password

    def __ne__(self, other):
        return not self.__eq__(other)


## Monkey patch the simple_hash function
def safe_simple_hash(text, key='', salt='', digest_alg='md5'):
    """
    Generates hash with the given text using the specified
    digest hashing algorithm
    """
    if not digest_alg:
        raise RuntimeError("simple_hash with digest_alg=None")
    elif not isinstance(digest_alg, str):  # manual approach
        h = digest_alg(text + key + salt)
    elif digest_alg.startswith('pbkdf2'):  # latest and coolest!
        iterations, keylen, alg = digest_alg[7:-1].split(',')
        return pbkdf2_hex(text, salt, int(iterations),
                          int(keylen), get_digest(alg))
    elif key:  # use hmac
        digest_alg = get_digest(digest_alg)
        h = hmac.new(key + salt, text, digest_alg)
    else:  # compatible with third party systems
        h = get_digest(digest_alg)()
        h.update(text + salt)
    return h.hexdigest()

def get_digest(value):
    """
    Returns a hashlib digest algorithm from a string
    """
    if not isinstance(value, str):
        return value
    value = value.lower()
    if value == "md5":
        return md5
    elif value == "sha1":
        return sha1
    elif value == "sha224":
        return sha224
    elif value == "sha256":
        return sha256
    elif value == "sha384":
        return sha384
    elif value == "sha512":
        return sha512
    else:
        raise ValueError("Invalid digest algorithm: %s" % value)


#print CRYPT(digest_alg='sha512', salt='leopard')('password')[0]
#print safeCRYPT(digest_alg='sha512', salt='leopard')('password')[0]

# Field('alt_password', compute=lambda r: alt_password(r))

def alt_password(r):
    
    passwd = r.password.split('$')
    alt = base64.b64encode(passwd[1].decode('hex')) + \
                '*' + base64.b64encode(passwd[2].decode('hex'))
    return alt

## configure auth policies
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = True
auth.settings.reset_password_requires_verification = True
# we don't want a group for each user
auth.settings.create_user_groups = False

#auth.settings.on_failed_authentication = lambda url: redirect(url)

# TODO - turn on captcha for regiastration
# auth.settings.register_captcha = Recaptcha()

## -----------------------------------------------------------------------------
## CONFIGURE EMAIL ACCOUNT SETTINGS 
## -- TODO - change to some kind of project admin email
## -- TODO - implement email logging
## -----------------------------------------------------------------------------

mail = auth.settings.mailer

# # testing from imperial account
# mail.settings.server = 'smtp.cc.ic.ac.uk:25' # 'logging' if request.is_local else myconf.take('smtp.server')
# mail.settings.sender = 'd.orme@imperial.ac.uk'
# mail.settings.login = 'dorme:notactuallymypassword'

# use the hostgator SMTP server
mail.settings.server = 'gator4079.hostgator.com:465'
mail.settings.sender = 'info@safeproject.net'
mail.settings.login = 'info@safeproject.net:info654='
mail.settings.ssl = True


## -----------------------------------------------------------------------------
## IMPORT the CKEDITOR PLUGIN TO GIVE A WYSIWYG EDITOR FOR BLOGS AND NEWS
## -- OK, so this editor is neat but one issue is that it dumps files into the 
##    root of uploads, which is messy
## -- Ordinarily, this would be controlled by the upload_folder setting but
##    this is hardcoded in the module. Could edit it there but you can also use
##    a fs object to provide a folder
## -- You'd think it might be possible to have multiple upload folders but
##    it turns out to be quite hard to switch the settings
## -----------------------------------------------------------------------------

from plugin_ckeditor import CKEditor
ckeditor = CKEditor(db)

from fs.osfs import OSFS
app_root = request.folder
app_root_fs = OSFS(app_root)

if not app_root_fs.exists('uploads/news_and_blogs/'):
    blog_fs = app_root_fs.makeopendir('uploads/news_and_blogs/')
else:
    blog_fs = app_root_fs.opendir('uploads/news_and_blogs/')

ckeditor.settings.uploadfs = blog_fs
ckeditor.settings.table_upload_name = 'ckeditor_uploads'
ckeditor.define_tables()
