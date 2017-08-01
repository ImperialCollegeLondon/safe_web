import datetime
import os
import safe_dataset_checker
import simplejson
import requests

"""
This model contains code for scheduled tasks on the 
SAFE website DB. At present these are:

Weekly:
-  Email the deputy coordinator with the current research visit schedule

Daily:
-  Look for research visits with Unknowns that are within a week of the
   research visit start date and email them a reminder to update

As needed:
- Verify the formatting of an uploaded dataset.
"""


def remind_about_unknowns():
    
    """
    Daily emails to research visit proposers who haven't
    completed the visitor details for visits that start 
    within the next week.
    """
    
    # get a list of research visits with <= a week to go.
    today = datetime.date.today()
    one_week_from_now = today + datetime.timedelta(days=7)
    
    # Select a summary to populate the task - implement
    # the SQL query below using the DAL:
    #   select a.first_name, a.email, v.title, v.id, count(m.id)
    #       from auth_user a join research_visit v on (a.id = v.proposer_id)
    #           join research_visit_member m on (m.research_visit_id = v.id)
    #       where m.user_id is null and
    #             v.arrival_date <= now() + interval '7' day and
    #             v.arrival_date > now()
    #       group by a.first_name, a.email, v.title, v.id;
    
    # get the query structure of the data
    query = db((db.research_visit.arrival_date <= one_week_from_now) &
               (db.research_visit.arrival_date > today) &
               (db.auth_user.id == db.research_visit.proposer_id) &
               (db.research_visit_member.research_visit_id == db.research_visit.id) &
               (db.research_visit_member.user_id == None))
    
    offenders = query.select(db.auth_user.first_name,
                             db.auth_user.email,
                             db.research_visit.title,
                             db.research_visit.id,
                             db.research_visit_member.id.count().with_alias('count'),
                             groupby = [db.auth_user.first_name, db.auth_user.email, 
                                        db.research_visit.id, db.research_visit.title])
    
    # now email each offender
    for offence in offenders:
        
        # dictionary to fill out the template
        template_dict = {'name': offence.auth_user.first_name,
                         'title': offence.research_visit.title,
                         'count': offence.count,
                         'url': URL('research_visit', 'research_visit_details',
                                    args=[offence.research_visit.id], scheme='https', 
                                    host='www.safeproject.net')}
        # email this offender
        SAFEmailer(subject='SAFE Research Visit details',
                   to=offence.auth_user.email,
                   template='research_visit_details_reminder.html',
                   template_dict=template_dict)
        
        # commit changes to the db - necessary for things running from models
        db.commit()
    
    ids = [str(o.research_visit.id) for o in offenders]
    if len(ids) > 0:
    	return 'Emailed proposers of the following research visits: ' + ','.join(ids)
    else: 
    	return 'No incomplete research visits found within the next week' 


def update_deputy_coordinator():
    
    """
    Emails the deputy coordinator attaching a text representation
    of the research visit schedule.
    """
    
    # get the file contents
    try:
        schedule = all_rv_summary_text()
        attach = {'SAFE_visits_{}.txt'.format(datetime.date.today().isoformat()): schedule}
    
        SAFEmailer(subject='Weekly research visit summary',
                   to= 'deputy.coord@safeproject.net', # 'd.orme@imperial.ac.uk',
                   template='weekly_rv_summary.html',
                   template_dict=dict(),
                   attachment_string_objects=attach)
        
        # commit changes to the db - necessary for things running from models
        db.commit()
        
        return 'Weekly research visit summary emailed'
    except:
        raise RuntimeError('Failed to email weekly research visit summary')


def verify_dataset(id, email=False):
    """
    Scheduler task to run dataset checks on an uploaded file. There
    are three possible outcomes for a dataset: PASS or FAIL if the check
    catches known formatting problems and ERROR if check hits an exception,
    which probably means an update to the checker code to handle the new
    and exciting way of getting the file wrong.
    
    The email argument allows the function to be run by admins without
    spamming the uploader. Useful in error checking problem uploads.
    
    Args:
        id: The id of the record from the dataset table that is to be checked.
        email: Should the dataset uploader be emailed the outcome?
    
    Returns:
        A string describing the outcome of the check
    """

    # get the record
    record = db.datasets[id]
    
    if record is None:
        return 'Verifying dataset: unknown record ID {}'.format(id)
    else:
        # run the check, with exception checking to handle any errors in the
        # dataset checker (or anywhere else in the handling code!)
        try:
            fname = os.path.join(request.folder,'uploads','datasets', record.file)
            # use a local locations file - there is some issue with using the service from within the code
            locs = os.path.join(request.folder,'static','files','locations.json')
            check_results = safe_dataset_checker.check_file(fname, verbose=False, locations_json=locs)
            
            # get the report
            messages = check_results['messages']
            report = messages.report().getvalue()
            # substitute in the user name for the local web2py filename
            report = report.replace(fname, record.file_name)
            
            # get the summary metadata as json, to store in the database
            summary = check_results['summary']
            summary_json = simplejson.dumps(summary)
            
            # double check the project ID from the file matches the submission
            if ('project_id' in summary) and (summary['project_id'] != record.project_id):
                report += ('\n! Project IDs in dataset and when submitting do not match\n')
                messages.n_warnings += 1
                outcome = 'FAIL'
                record.update_record(check_outcome=outcome,
                                     check_report=PRE(report),
                                     n_warnings=messages.n_warnings,
                                     title=summary['title'] if 'title' in summary else None,
                                     description=summary['description'] if 'description' in summary else None,
                                     summary = summary_json)
            
            if messages.n_warnings:
                outcome = 'FAIL'
                record.update_record(check_outcome=outcome,
                                     check_report=PRE(report),
                                     n_warnings=messages.n_warnings,
                                     title=summary['title'],
                                     description=summary['description'],
                                     summary = summary_json)
            else:
                outcome = 'PASS'
                record.update_record(check_outcome=outcome,
                                     check_report=PRE(report),
                                     n_warnings=0,
                                     title=summary['title'],
                                     description=summary['description'],
                                     summary = summary_json)
        except Exception as e:
            outcome = 'ERROR'
            record.update_record(check_outcome=outcome + ':' + type(e).__name__)
            report = ''
        
        # notify the user
        opts = {'PASS': ['Dataset passed checks', 'dataset_check_pass.html'],
                'FAIL': ['Dataset failed checks', 'dataset_check_fail.html'],
                'ERROR': ['Error checking dataset', 'dataset_check_error.html']}
        res = opts[outcome]
        
        if email:
            SAFEmailer(to=record.uploader_id.email,
                       subject=res[0],
                       template=res[1],
                       template_dict= {'id': id, 
                                       'report': report, 
                                       'filename': record.file_name,
                                       'name': record.uploader_id.first_name})

        return 'Verifying dataset ID {}: {}'.format(id, outcome)


def submit_dataset_to_zenodo(id):
    
    """
    Controller to submit a dataset to Zenodo and to update the
    dataset record with the result of that attempt.
    
    Args:
        id: The id of the dataset table record to be submitted
    
    Returns:
        A string describing the outcome.
    """
    
    # check the record exists and hasn't already been submitted
    record = db.datasets[id]
    
    if record is None:
        return 'Publishing dataset: unknown record ID {}'.format(id)
    elif record.check_outcome != 'PASS':
        return 'Publishing dataset: record ID {} has not passed format checking'.format(id)
    elif record.zenodo_submission_status == 'Published':
        return 'Publishing dataset: record ID {} already published'.format(id)
    else:
        
        # A) BUILD THE METADATA FOR THIS DATASET
        # - load the check summary from the database to populate the contents
        summary = simplejson.loads(record.summary)
        
        # basic contents
        metadata = {
            'metadata': {
                	"upload_type": "dataset",
                	"publication_date": datetime.date.today().isoformat(),
                	"title": summary['title'], 
                	"keywords": summary['keywords'],
                    "license": 'cc-by',
                	"contributors": [
                		{"name": "The SAFE Project", "type": "ContactPerson", 
                         "affiliation": "Imperial College London", 
                         "orcid": "0000-0003-3378-2814"},
                	],
                	"communities": [{"identifier": "safe"}]
            }
        }
        
        # set up the access rights
        if summary['access_status'] == 'Embargo':
            metadata['metadata']['access_right'] = 'embargoed'
            metadata['metadata']['embargo_date'] = summary['embargo_date']
        elif summary['access_status'] == 'Open':
            metadata['metadata']['access_right'] = 'open'
        else:
            return 'Publishing dataset: record ID {} has unknown access status'.format(id)
        
        # set up the dataset creators
        metadata['metadata']['creators'] = []
        for auth in  summary['authors']:
            creator = {ky: auth[ky] for ky in ('name', 'affiliation')}
            if auth['orcid'] is not None:
                creator['orcid'] = auth['orcid']
            
            metadata['metadata']['creators'].append(creator)
        
        # set up the Description
        # - get a project link back to the website (although Zenodo doesn't support links)
        qry = db((db.project_id.id == record.project_id))
        proj = qry.select(left=db.project_id.on(db.project_id.project_details_id == db.project_details.id))
        title = proj.first().project_details.title
        
        desc = ('This dataset was collected as part of the following SAFE research project:<br><b>{}</b> '
                 '<br><br>For more information see:<br> https://www.safeproject.net/projects/project_view/{}').format(title, record.project_id)
        
        desc += '<br><br><b>Description</b><br>'+ summary['description'].replace('\n', '<br>')
        desc += '<br><br>There are {} data worksheets in this dataset:<br><br>'.format(len(summary['data_worksheets']))
        
        sheet_desc = "<b>{}</b> (Worksheet '{}')<br>Dimensions: {} rows by {} columns <br> Description: {}<br>Fields:"
        field_desc = "<li><em>{}</em> ({}): {}"
        
        for ds in summary['data_worksheets']:
            desc += sheet_desc.format(ds['title'], ds['worksheet'], ds['nrow'], ds['ncol'], ds['description'])
            desc += '<ul>'
            for fld in ds['fields']:
                desc += field_desc.format(fld['field_name'],  fld['field_type'], fld['description'])
            desc += '</ul>'
        
        metadata['metadata']['description'] = desc
        
        
        # B) NOW PUSH TO ZENODO
        # get the authentication token from the private folder
        auth = os.path.join(request.folder, 'private','zenodo_token.json')
        token = simplejson.load(open(auth))
        
        # headers description
        hdr = {"Content-Type": "application/json"}
        
        # get a new deposit resource
        dep = requests.post('https://sandbox.zenodo.org/api/deposit/depositions', 
                             params=token, json={}, headers= hdr)
        
        # NOTES - for new versions of files, need to request a newversion from the original record (not concept)
        # and then edit the latest draft deposit
        # new_draft = requests.post('https://sandbox.zenodo.org/api/deposit/depositions/{}/actions/newversion'.format('77504'), params=token)
        # dep = new_draft.json()['links']['latest_draft']
        
        # trap errors in creating the resource
        if dep.status_code != 201:
            record.update_record(zenodo_submission_status = 'Failed to obtain deposit',
                                 zenodo_response = dep.json())
            return "Failed to obtain deposit"
        
        # get the links dictionary out of the deposit resource
        links = dep.json()['links']
                
        # attach the metadata to the deposit resource
        mtd = requests.put(links['self'], params=token, data=simplejson.dumps(metadata), headers=hdr)
        
        # trap errors in uploading metadata and tidy up
        if mtd.status_code != 200:
            record.update_record(zenodo_submission_status = 'Failed to upload metadata',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_response = mtd.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to upload metadata"
        
        # upload the file
        fname = os.path.join(request.folder, 'uploads', 'datasets', record.file)
        fls = requests.post(links['files'], params=token, 
                            files={'file': open(fname, 'rb')})
        
        # trap errors in uploading file
        # - no success or mismatch in md5 checksums
        if fls.status_code != 201:
            record.update_record(zenodo_submission_status = 'Failed to upload dataset',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_response = fls.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to upload dataset"
        elif fls.json()['checksum'] != record.file_hash:
            record.update_record(zenodo_submission_status = 'Mismatch in local and uploaded MD5 hashes',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_response = fls.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to upload dataset"
        
        # update the name to the one originally provided by the user
        data = simplejson.dumps({'filename': record.file_name})
        upd = requests.put(fls.json()['links']['self'], data=data, headers=hdr, params=token)
        
        # trap errors in updating name
        if upd.status_code != 200:
            record.update_record(zenodo_submission_status = 'Failed to update filename',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_response = upd.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to update filename"
        
        # publish
        pub = requests.post(links['publish'], params=token)
        
        # trap errors in publishing
        if pub.status_code != 202:
            record.update_record(zenodo_submission_status = 'Failed to publish dataset',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_response = pub.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to publish dataset"
        else:
            # modify the record html to point to the concept url
            record_url = pub.json()['links']['record_html']
            concept_record = record_url.replace(str(pub.json()['record_id']),
                                                str(pub.json()['conceptrecid']))
            record_doi = pub.json()['doi_url']
            concept_doi = record_doi.replace(str(pub.json()['record_id']),
                                             str(pub.json()['conceptrecid']))
            
            record.update_record(zenodo_submission_status = 'Published',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_response = pub.json(),
                                 zenodo_concept_record = concept_record,
                                 zenodo_concept_doi = concept_doi,
                                 zenodo_version_doi = record_doi)
            
            return "Published dataset to {}".format(concept_record)


# Load the scheduler and set the task names, setting a 5 minute heartbeat.
# As the current tasks are daily activities at most, there is no need for
# the scheduler to do frenetic checks every 3 seconds, which is the default

from gluon.scheduler import Scheduler
scheduler = Scheduler(db, 
                      tasks=dict(remind_about_unknowns=remind_about_unknowns,
                                 update_deputy_coordinator=update_deputy_coordinator,
                                 verify_dataset=verify_dataset),
                      heartbeat=5*60)

# These tasks then need to be queued using scheduler.queue_task or manually via 
# the appadmin interface. Don't do it here as they'll be queued every time the 
# model runs, which is basically every time a webpage is loaded! So, 
# programatically, they can go in a controller which an admin can run once to 
# get a defined set of queues going.
