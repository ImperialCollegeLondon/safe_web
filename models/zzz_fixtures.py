# -*- coding: utf-8 -*-

#########################################################################
## This file loads static data into the database
## - it should only be run during the first setup
## - It can also be used to empty the database of data, which is dangerous
#########################################################################

import os # for file path handling
import csv
import datetime

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
## LOAD EXISTING USERS
## NOTE - the serial id mechanism means that the web2py import regenerates id
##         numbers, breaking the link to projects and members, so these need
##         to be linked up again manually in the project_members import 
## ------------------------------------------------------------------------

if db(db.auth_user).count() == 0:
    
    
    # set up some groups
    db.auth_group.insert(role='admin',
                         description='People who have access to the SAFE admin forms')
    
    db.auth_group.insert(role='species_profiler',
                         description='People who can add and edit species profiles')
    
    db.auth_group.insert(role='bloggers',
                         description='People who can add blog posts')
    
    db.auth_group.insert(role='wiki_user',
                         description='People who can edit the wiki')
    
    
    # insert 'users' from previous website: people associated with projects
    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/final_users.csv')
    
    with open(data_file, 'rU') as csvfile:
        
        reader = csv.DictReader(csvfile)
        for row in reader:
            
            # insert the information
            details_id = db.auth_user.insert(first_name = row['FirstName'],
                                            last_name = row["LastName"],
                                            institution = row["Affiliation"],
                                            email = row['Email'],
                                            alternative_email = row['alt_email'],
                                            legacy_user_id = row['legacy_user_id'])
    
    # add the developer to the admin group
    rows = db(db.auth_user.email == 'd.orme@imperial.ac.uk').select()
    r = rows.first()
    r.update_record(password=db.auth_user.password.requires('password23')[0])
    auth.add_membership('admin', r.id)
    auth.add_membership('bloggers', r.id)
    
    # add test users to the admin group
    rows = db(db.auth_user.last_name == 'Ewers').select()
    r = rows.first()
    r.update_record(password=db.auth_user.password.requires('password23')[0])
    auth.add_membership('admin', r.id)
    auth.add_membership('bloggers', r.id)
    
    rows = db(db.auth_user.email == 'olivia.daniel08@imperial.ac.uk').select()
    r = rows.first()
    r.update_record(password=db.auth_user.password.requires('password23')[0])
    auth.add_membership('admin', r.id)
    auth.add_membership('bloggers', r.id)


## ------------------------------------------------------------------------
## LOAD EXISTING PROJECTS
## - assumes all existing projects signed up to data sharing
## - assumes all existing projects are approved
## - needs to populate project_details and a project_id entry and then pair them up
## ------------------------------------------------------------------------

if db(db.project_details).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/final_projects.csv')

    # can't just use import_from_csv() here because of the image and file links
    # so need to insert programatically to file everything correctly
    # db.outputs.import_from_csv_file(open(data_file, 'rb'))

    img_dir = 'private/db_preload_data/images/projects'

    with open(data_file, 'rU') as csvfile:
        
        reader = csv.DictReader(csvfile)
        for row in reader:
            # get the image, truncating any stupidly long filenames
            if row['img_file'] != 'NA' and row['img_file'] != '':
                img_in = os.path.join(request.folder, img_dir, row['img_file'])
                short_fn = os.path.splitext(row['img_file'])
                short_fn = short_fn[0][:50] + short_fn[1]
                img_st = db.project_details.picture.store(open(img_in, 'rb'), short_fn)
            else:
                img_st = None
            
            # get a new row from the project_id table
            project_id = db.project_id.insert()
            
            # now insert all the information
            details_id = db.project_details.insert(picture = img_st,
                                                   project_id = project_id,
                                                   version = 1,
                                                   title = row['title'],
                                                   research_areas = row['tags'],
                                                   start_date = row['start_date'],
                                                   end_date = row['end_date'],
                                                   rationale = row['methods'], # stupidly switched
                                                   methods = row['rationale'],
                                                   requires_ra = row['requires_ra'],
                                                   requires_vehicle = row['requires_vehicle'],
                                                   resource_notes = row['resource_notes'],
                                                   data_sharing = True,
                                                   proposal_date = datetime.datetime.now(),
                                                   admin_status = 'Approved',
                                                   legacy_project_id = row['Code'],
                                                   which_animal_taxa = '||')
            
            # link the project_id to the details
            details = db.project_details(details_id)
            id_record = db.project_id(project_id)
            id_record.update_record(project_details_id=details.id,
                                    project_details_uuid=details.uuid)
    
    csvfile.close()

## ------------------------------------------------------------------------
## LOAD EXISTING PROJECT MEMBERS
## - this needs to make links using the legacy_project_id and legacy_user_id
##   fields to match up the imported records with their id numbers allocated
##   automatically in the database.
## ------------------------------------------------------------------------

if db(db.project_members).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/final_project_members.csv')
    
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
                        
            # now need to find the project.id value by matching 
            # legacy_project_id values. This is clumsy, but there's no
            # easy way to preserve id values as a primary key on import
            # to a table, and this only needs to be done once.
            
            # NB - this code is _assuming_ a single match, but this ought to be true
            proj_rows = db(db.project_details.legacy_project_id == row['Project']).select()
            r = proj_rows.first()
            
            auth_rows = db(db.auth_user.legacy_user_id == row['legacy_user_id']).select()
            a = auth_rows.first()
            
            
            # now insert all the information
            db.project_members.insert(project_id = r.project_id,
                                      user_id = a.id,
                                      project_role = row['Position'],
                                      is_coordinator = True if row['coord'] == 'TRUE' else False)
    
    csvfile.close()


## ------------------------------------------------------------------------
## LOAD EXISTING OUTPUTS
## - which requires a more sophisticated loading approach, 
##   as there are images and files to link up 
## ------------------------------------------------------------------------


# try and load existing outputs
if db(db.outputs).count() == 0:

    # load definition files
    data_file = os.path.join(request.folder, 'private/db_preload_data/final_outputs.csv')

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
            
            # look up the user
            auth_rows = db(db.auth_user.legacy_user_id == row['legacy_user_id']).select()
            a = auth_rows.first()
            
            # now insert all the information
            db.outputs.insert(picture = img_st,
                              file = file_st,
                              title = row['title'],
                              format = row['format'],
                              citation = row['citation'],
                              description = row['description'],
                              user_id = a.id, 
                              submission_date = datetime.datetime.now(),
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
    data_file = os.path.join(request.folder, 'private/db_preload_data/final_project_outputs.csv')
    
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            
            # now need to find the new project and output ids value by matching 
            # legacy ID values. This is clumsy, but there's no
            # easy way to preserve id values as a primary key on import
            # to a table, and this only needs to be done once.
            
            proj_rows = db(db.project_details.legacy_project_id == row['Code']).select()
            p = proj_rows.first()
            output_rows = db(db.outputs.legacy_output_id == row['legacy_output_id']).select()
            o = output_rows.first()
            auth_rows = db(db.auth_user.legacy_user_id == row['legacy_user_id']).select()
            a = auth_rows.first()
            
            db.project_outputs.insert(project_id = p.project_id,
                                      output_id = o.id,
                                      user_id = a.id,
                                      date_added = datetime.datetime.now())
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
            
            # DO assuming ownership
            user_id = db(db.auth_user.email == 'd.orme@imperial.ac.uk').select().first().id
            
            # now insert all the information
            db.blog_posts.insert(thumbnail_figure = img_st,
                              authors = row['authors'],
                              title = row['title'],
                              content = row['content'],
                              date_posted = row['date_posted'],
                              admin_status = 'Approved',
                              user_id = user_id, 
                              # admin_id = 1
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
            
            # DO assuming ownership
            user_id = db(db.auth_user.email == 'd.orme@imperial.ac.uk').select().first().id
            
            # now insert all the information
            db.news_posts.insert(thumbnail_figure = img_st,
                              title = row['title'],
                              content = row['content'],
                              date_posted = row['date_posted'],
                              poster_id = user_id,
                              )
            db.commit()

    csvfile.close()

