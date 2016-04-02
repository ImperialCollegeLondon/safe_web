# -*- coding: utf-8 -*-

#########################################################################
## This file loads static data, such as RCUK tags, into the database
## - it should only be run during the first setup
## It can also be used to empty the database of data, which is dangerous
#########################################################################

import os # for file path handling
import csv
from gluon.contrib.populate import populate

## CHANGING THIS TO True WILL EMPTY ALL TABLES FROM THE DB 
## - DO NOT ALTER THIS UNLESS YOU ARE REALLY SURE WHAT YOU'RE DOING
##   AND CHANGE IT BACK IMMEDIATELY OR EVERY SINGLE PAGE CALL WILL 
##   DESTROY AND RELOAD THE DB, WHICH HAS PERFORMANCE IMPLICATIONS

# Need to remove the records in the databases folder to.

RESET = False

if RESET:
    for table in db.tables:
        # Make sure to cascade, or this will fail 
        # for tables that have FK references.
        db[table].truncate("CASCADE")
    db.commit()
    


## ------------------------------------------------------------------------
## LOAD RCUK TAGS
## - has to come early, so projects and users can reference them
## ------------------------------------------------------------------------

# if db(db.rcuk_tags).count() == 0:
#
#     # load definition files
#     data_file = os.path.join(request.folder, 'private/db_preload_data/RCUK_classification.csv')
#     # note that the next command imports data only from fields with
#     # headers matching the format table_name.field_name
#     # e.g. rcuk_tags.level,rcuk_tags.subject,rcuk_tags.topic,rcuk_tags.tag
#     db.rcuk_tags.import_from_csv_file(open(data_file, 'rb'))
#     db.commit()


## ------------------------------------------------------------------------
## LOAD EXISTING USERS
## NOTE - the serial id mechanism means that the web2py import regenerates id
##         numbers, breaking the link to projects and members, so these need
##         to be linked up again manually in the project_members import 
## ------------------------------------------------------------------------

if db(db.auth_user).count() == 0:
    
    # now insert all the information
    db.auth_user.insert(first_name = 'David', 
                        last_name = 'Orme',
                        email = 'd.orme@imperial.ac.uk',
                        password = db.auth_user.password.requires[0]('password23')[0],
                        title = 'Dr',
                        nationality = 'British',
                        academic_status = 'Research Fellow',
                        phone = '00000',
                        mobile_phone = '00000',
                        institution = 'Imperial College London',
                        institution_address = 'Imperial College London',
                        institution_phone = '00000')
    
   # Add beta tester
    db.auth_user.insert(first_name = 'Olivia', 
                        last_name = 'Daniel',
                        email = 'olivia.daniel08@imperial.ac.uk',
                        password = db.auth_user.password.requires[0]('password23')[0],
                        title = '',
                        nationality = 'British',
                        academic_status = 'Other',
                        phone = '00000',
                        mobile_phone = '00000',
                        institution = 'Imperial College London',
                        institution_address = 'Imperial College London',
                        institution_phone = '00000')
    
    # set up some groups
    db.auth_group.insert(role='admin',
                         description='People who have access to the SAFE admin forms')
    
    db.auth_group.insert(role='species_profiler',
                         description='People who can add and edit species profiles')
    
    db.auth_group.insert(role='bloggers',
                         description='People who can add blog posts')
    
    # insert 'users' from previous website: people associated with projects
    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/Users_table.csv')
    # note that the next command imports data only from fields with
    # headers matching the format table_name.field_name
    db.auth_user.import_from_csv_file(open(data_file, 'rb'))
    db.commit()

    # add the developer to the admin group
    rows = db(db.auth_user.email == 'd.orme@imperial.ac.uk').select()
    r = rows.first()
    auth.add_membership('admin', r.id)
    auth.add_membership('bloggers', r.id)
    
    # add test users to the admin group
    rows = db(db.auth_user.last_name == 'Ewers').select()
    r = rows.first()
    r.update_record(email='r.ewers@imperial.ac.uk',
                    password=db.auth_user.password.requires[0]('password23')[0])
    auth.add_membership('admin', r.id)
    auth.add_membership('bloggers', r.id)
    
    rows = db(db.auth_user.email == 'olivia.daniel08@imperial.ac.uk').select()
    r = rows.first()
    auth.add_membership('admin', r.id)
    auth.add_membership('bloggers', r.id)

## ------------------------------------------------------------------------
## LOAD EXISTING PROJECTS
## - which requires a more sophisticated loading approach, 
##   as there are images to link up
## - assumes all existing projects signed up to data sharing
## - assumes all existing projects are approved
## ------------------------------------------------------------------------

if db(db.project).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/project_inputs.csv')

    # can't just use import_from_csv() here because of the image and file links
    # so need to insert programatically to file everything correctly
    # db.outputs.import_from_csv_file(open(data_file, 'rb'))

    img_dir = 'private/db_preload_data/images/projects'

    with open(data_file, 'rU') as csvfile:
       reader = csv.DictReader(csvfile)
       for row in reader:

           # get the image
           if row['img_file'] != 'NA':
               img_in = os.path.join(request.folder, img_dir, row['img_file'])
               img_st = db.project.picture.store(open(img_in, 'rb'), row['img_file'])
           else:
               img_st = None
           
           # now insert all the information
           db.project.insert(picture = img_st,
                             title = row['title'],
                             project_home_country = row['project_home_country'],
                             legacy_sampling_sites = row['sampling_sites'],
                             legacy_sampling_scales = row['sampling_scales'],
                             start_date = row['start_date'],
                             end_date = row['end_date'],
                             rationale = row['rationale'],
                             methods = row['methods'],
                             requires_ra = row['requires_ra'],
                             requires_vehicle = row['requires_vehicle'],
                             resource_notes = row['resource_notes'],
                             data_sharing = True,
                             admin_status = 'Approved',
                             legacy_project_id = row['legacy_project_id'])
    
    db.commit()
    csvfile.close()

## ------------------------------------------------------------------------
## LOAD EXISTING PROJECT MEMBERS
## - this needs to make links using the legacy_project_id and legacy_user_id
##   fields to match up the imported records with their id numbers allocated
##   automatically in the database.
## ------------------------------------------------------------------------

if db(db.project_members).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/project_members_table.csv')
    
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
                        
            # now need to find the project.id value by matching 
            # legacy_project_id values. This is clumsy, but there's no
            # easy way to preserve id values as a primary key on import
            # to a table, and this only needs to be done once.
            
            # NB - this code is _assuming_ a single match, but this ought to be true
            proj_rows = db(db.project.legacy_project_id == row['legacy_project_id']).select()
            r = proj_rows.first()
            
            auth_rows = db(db.auth_user.legacy_user_id == row['legacy_user_id']).select()
            a = auth_rows.first()
            
            
            # now insert all the information
            db.project_members.insert(project_id = r.id,
                                      user_id = a.id,
                                      project_role = row['project_role'])
            
            db.commit()

    csvfile.close()


## ------------------------------------------------------------------------
## LOAD EXISTING OUTPUTS
## - which requires a more sophisticated loading approach, 
##   as there are images and files to link up 
## ------------------------------------------------------------------------


# try and load existing outputs
if db(db.outputs).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/output_inputs.csv')

    # can't just use import_from_csv() here because of the image and file links
    # so need to insert programatically to file everything correctly
    # db.outputs.import_from_csv_file(open(data_file, 'rb'))

    img_dir = 'private/db_preload_data/images/outputs'
    file_dir = 'private/db_preload_data/files/outputs'
    
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            
            # get the two file objects
            if row['picture'] != 'NA':
                img_in = os.path.join(request.folder, img_dir, row['picture'])
                img_st = db.outputs.picture.store(open(img_in, 'rb'), row['picture'])
            else:
                img_st = None
            
            if row['file'] != 'NA':
                file_in = os.path.join(request.folder, file_dir, row['file'])
                file_st = db.outputs.file.store(open(file_in, 'rb'), row['file'])
            else:
                file_st = None
            
            # now insert all the information
            db.outputs.insert(picture = img_st,
                              file = file_st,
                              title = row['title'],
                              format = row['format'],
                              citation = row['citation'],
                              description = row['description'],
                              url = row['url'],
                              doi = row['doi'],
                              admin_status = 'Approved',
                              legacy_output_id = row['legacy_output_id'])

            db.commit()

    csvfile.close()

## ------------------------------------------------------------------------
## LOAD PAIRINGS BETWEEN OUTPUTS AND PROJECTS
## ------------------------------------------------------------------------

# try and load existing outputs
if db(db.project_outputs).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/project_outputs_inputs.csv')
    
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
    
            # now need to find the new project and output ids value by matching 
            # legacy ID values. This is clumsy, but there's no
            # easy way to preserve id values as a primary key on import
            # to a table, and this only needs to be done once.
            proj_rows = db(db.project.legacy_project_id == row['legacy_project_id']).select()
            p = proj_rows.first()
            output_rows = db(db.outputs.legacy_output_id == row['legacy_output_id']).select()
            o = output_rows.first()
            
            db.project_outputs.insert(project_id = p.id,
                                      output_id = o.id,
                                      added_by = row['added_by'],
                                      date_added = row['date_added'])
            db.commit()

    csvfile.close()

## ------------------------------------------------------------------------
## LOAD SPECIES PROFILES
## - images here are links, currently including some non CC images
## ------------------------------------------------------------------------

# species profiles
if db(db.species_profile).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/species_inputs.csv')
    # note that the next command imports data only from fields with
    # headers matching the format table_name.field_name
    # e.g. rcuk_tags.level,rcuk_tags.subject,rcuk_tags.topic,rcuk_tags.tag
    db.species_profile.import_from_csv_file(open(data_file, 'rb'))
    db.commit()


## ------------------------------------------------------------------------
## LOAD CONTACTS
## - which requires a more sophisticated loading approach, 
##   as there are images to link up 
## ------------------------------------------------------------------------


# try and load existing outputs
if db(db.safe_contacts).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/contacts_table.csv')

    # can't just use import_from_csv() here because of the image and file links
    # so need to insert programatically to file everything correctly
    # db.outputs.import_from_csv_file(open(data_file, 'rb'))

    img_dir = 'private/db_preload_data/images/contacts'
    
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            
            # get the images
            if row['picture'] != '':
                img_in = os.path.join(request.folder, img_dir, row['picture'])
                img_st = db.safe_contacts.picture.store(open(img_in, 'rb'), row['picture'])
            else:
                img_st = None
            
            # now insert all the information
            db.safe_contacts.insert(picture = img_st,
                              display_name = row['display_name'],
                              contact_type = row['contact_type'], 
                              role = row['role'],
                              institution = row['institution'],
                              address = row['address'],
                              email = row['email'],
                              website = row['website'],
                              taxonomic_speciality = row['taxonomic_speciality'])
            
            db.commit()

    csvfile.close()


## ------------------------------------------------------------------------
## LOAD BLOG POSTS
## - which requires a more sophisticated loading approach, 
##   as there are images to link up - we're only properly linking in the 
##   thumbnails, unless I can be bothered to work out how to upload the 
##   blog images via the ckeditor methods
## ------------------------------------------------------------------------


# try and load existing outputs
if db(db.blog_posts).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/blog_inputs.csv')

    # can't just use import_from_csv() here because of the image and file links
    # so need to insert programatically to file everything correctly
    # db.outputs.import_from_csv_file(open(data_file, 'rb'))

    img_dir = 'private/db_preload_data/images/blog_thumbnails'

    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:

            # get the images
            if row['thumb'] != '':
                img_in = os.path.join(request.folder, img_dir, row['thumb'])
                img_st = db.blog_posts.thumbnail_figure.store(open(img_in, 'rb'), row['thumb'])
            else:
                img_st = None

            # now insert all the information
            db.blog_posts.insert(thumbnail_figure = img_st,
                              authors = row['authors'],
                              title = row['title'],
                              content = row['content'],
                              date_posted = row['date_posted'],
                              admin_status = 'Approved',
                              poster_id = 1, # DO assuming ownership
                              admin_id = 1
                              )
            db.commit()

    csvfile.close()


## ------------------------------------------------------------------------
## LOAD NEWS POSTS
## - which requires a more sophisticated loading approach, 
##   as there are images to link up - we're only properly linking in the 
##   thumbnails, unless I can be bothered to work out how to upload the 
##   blog images via the ckeditor methods
## ------------------------------------------------------------------------


# try and load existing outputs
if db(db.news_posts).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/news_inputs.csv')

    # can't just use import_from_csv() here because of the image and file links
    # so need to insert programatically to file everything correctly
    # db.outputs.import_from_csv_file(open(data_file, 'rb'))

    img_dir = 'private/db_preload_data/images/news_thumbnails'

    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:

            # get the images
            if row['thumb'] != '':
                img_in = os.path.join(request.folder, img_dir, row['thumb'])
                img_st = db.news_posts.thumbnail_figure.store(open(img_in, 'rb'), row['thumb'])
            else:
                img_st = None

            # now insert all the information
            db.news_posts.insert(thumbnail_figure = img_st,
                              title = row['title'],
                              content = row['content'],
                              date_posted = row['date_posted'],
                              poster_id = 1, # DO assuming ownership
                              )
            db.commit()

    csvfile.close()

