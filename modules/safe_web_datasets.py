import os
import datetime
from lxml import etree
import simplejson
import copy
import safe_dataset_checker
from networkx import Graph, bfs_successors, get_node_attributes
import requests
from safe_web_global_functions import safe_mailer
from itertools import groupby

# The web2py HTML helpers are provided by gluon. This also provides the 'current' object, which
# provides the web2py 'request' API (note the single letter difference from the requests package!).
# The 'current' object is also extended by models/db.py to include the current 'db' DAL object
# and the 'myconf' AppConfig object so that they can accessed by this module

from gluon import *

"""
This module providese functions to handle datasets within the SAFE website. 
These are called from the datasets controller but are also needed from other locations, 
such as the scheduler, so are defined here in their own module.
"""


def verify_dataset(record_id, email=False):
    """
    Function to run the safe_dataset_checker on an uploaded file. There
    are three possible outcomes for a dataset: PASS; FAIL, if the check
    catches known formatting problems; and ERROR if check hits an exception,
    which probably means an update to the checker code to handle the new
    and exciting way of getting the file wrong.
    
    The email argument allows the function to be run by admins directly
    using the administer_datasets controller without spamming the uploader. 
    Useful in error checking problem uploads.
    
    This function is also used as a scheduler task, so needs some extra
    care to make sure it runs in the environment of a scheduler worker
    as well as in the environment of the website.
    
    Args:
        record_id: The id of the record from the dataset table that is to be checked.
        email: Should the dataset uploader be emailed the outcome?
    
    Returns:
        A string describing the outcome of the check that gets stored in the
        scheduler results or sent back to the administer_datasets controller.
        This is primarily a user friendly bit of text for popping up in a 
        website flash, not an Exception message, so those are stored elsewhere
        for an admin to look at.
    """
    
    # check the configuration includes a path to the gbif_database
    try:
        gbif_db = current.myconf.take('gbif.gbif_database')
    except BaseException:
        raise RuntimeError('Site config does not provide a path for the gbif database')
    
    # Load the host name from the configuration. When run from a controller,
    # the URL(host=TRUE) has access to the host name from requests. This isn't
    # true when it is run by a scheduler worker, which isn't operating as part
    # of the website. So rather than hardcoding, store the host name in the config
    try:
        host = current.myconf.take('host.host_name')
    except BaseException:
        raise RuntimeError('Site config does provide not the host name')
    
    # get the record
    record = current.db.datasets[record_id]
    
    # track errors to avoid hideous nested try statements
    error = False
        
    if record is None:
        # not a valid record? Can't email anyone so turn that off
        ret_msg = 'Verifying dataset {}: unknown record ID'.format(record_id)
        email = False
        error = True
    else:
        # otherwise, create a return dictionary for all remaining failure 
        # modes (no report, but file, uploader and URL should fine) and
        # set the default outcome
        ret_dict = {'dataset_id': int(record.dataset_id), 
                    'report': '',
                    'filename': record.file_name,
                    'name': record.uploader_id.first_name,
                    'dataset_url': URL('datasets', 'submit_dataset', 
                                       vars={'dataset_id': record.dataset_id},
                                       scheme=True, host=host)}
        outcome = 'ERROR'
    
    # Initialise the dataset checker:
    if not error:
        # - get paths to dataset file. Failure to find is handled by safe_dataset_checker methods.
        fname = os.path.join(current.request.folder, 'uploads', 'datasets',
                             str(record.dataset_id), record.file)
        # get the Dataset object from the file checker
        try:
            dataset = safe_dataset_checker.Dataset(fname, verbose=False, gbif_database=gbif_db)
        except Exception as e:
            # We don't want to bail here because we might want to email the uploader,
            # but we do want to record what went wrong. We store it in the dataset record, which
            # is the only venue when run from a controller. If I could work out where the scheduler 
            # run output comes from, I'd do that too.
            record.update_record(dataset_check_outcome='ERROR',
                                 dataset_check_error=repr(e))
            ret_msg = 'Verifying dataset {}: error initialising dataset checker'
            ret_msg = ret_msg.format(record.dataset_id)
            error = True
    
    # main processing of the dataset
    if not error:
        try:
            # load the metadata sheets
            dataset.load_summary(validate_doi=True, project_id=record.project_id)
            dataset.load_taxa()
            # use a local locations file - there is some issue with using the
            # service from within the code
            locations_json = os.path.join(current.request.folder, 'static',
                                          'files', 'locations.json')
            dataset.load_locations(locations_json=locations_json)
            
            # check the datasets
            for ws in dataset.dataworksheet_summaries:
                dataset.load_data_worksheet(ws)
            
            # cross check the taxa and locations
            dataset.final_checks()
            
        except Exception as e:
            ret_msg = 'Verifying dataset {}: error running dataset checking'
            ret_msg = ret_msg.format(record.dataset_id)
            dataset_check_error = repr(e)
        else:
            if dataset.passed:
                outcome = 'PASS'
                ret_msg = 'Verifying dataset {}: dataset checking PASSED'.format(record.dataset_id)
            else:
                outcome = 'FAIL'
                ret_msg = 'Verifying dataset {}: dataset checking FAILED'.format(record.dataset_id)
            
            dataset_check_error = ''
        
        # At this point, we have a Dataset object, so can populate the record with 
        # what information is available, regardless of Error, Fail or Pass
        # - The DAL handles conversion of the python structure into JSON, so
        #   can just pass the objects. Previously, used simplejson.dumps, which 
        #   meant they were stored as a string, so needed reloading rather than 
        #   being saved natively as JSON
        
        # First, need to extract the check report from the StringIO object and
        # substitute in the user filename for the local web2py filename. Also,
        # wrap it in <pre> for display purposes.
        if outcome == 'ERROR':
            report_text = ""
        else:
            report_text = dataset.report().getvalue()
            report_text = PRE(report_text.replace(fname, record.file_name))
            # Update the ret_dict to insert the report text
            ret_dict['report'] = report_text
            
        record.update_record(dataset_check_outcome=outcome,
                             dataset_check_report=report_text,
                             dataset_check_error=dataset_check_error,
                             dataset_title=dataset.title,
                             dataset_metadata=dataset.export_metadata_dict(),
                             dataset_taxon_index=dataset.taxon_index,
                             dataset_locations=dataset.locations)
    
    # notify the user
    if email:
        opts = {'PASS': ['Dataset passed checks', 'dataset_check_pass.html'],
                'FAIL': ['Dataset failed checks', 'dataset_check_fail.html'],
                'ERROR': ['Error checking dataset', 'dataset_check_error.html']}
        
        safe_mailer(to=record.uploader_id.email,
                    subject=opts[outcome][0],
                    template=opts[outcome][1],
                    template_dict=ret_dict)
    
    # A task run by a worker does not automatically commit changes, so
    # save any by changes before ending
    current.db.commit()
    
    return ret_msg


def submit_dataset_to_zenodo(record_id, deposit_id=None, sandbox=False):
    
    """
    Function to submit a dataset record to Zenodo and to update the
    dataset record with the result of that attempt. This handles the
    logic of selecting which method to use: create excel, update excel
    or adopt external.
    
    Args:
        record_id: The id of the dataset table record to be submitted
        deposit_id: An integer giving the id of an existing Zenodo deposit to adopt
            using this dataset record.
        sandbox: Should the sandbox API be used - retained for testing
    Returns:
        A string describing the outcome.
    """
    
    # check the record exists and hasn't already been submitted
    record = current.db.datasets[record_id]

    if record is None:
        return 'Publishing dataset: unknown record ID {}'.format(record_id)
    elif record.dataset_check_outcome != 'PASS':
        return 'Publishing dataset: record ID {} has not passed format checking'.format(record_id)
    elif record.zenodo_submission_status == 'ZEN_PASS':
        return 'Publishing dataset: record ID {} already published'.format(record_id)

    # load the correct API and token
    if sandbox:
        try:
            token = {'access_token': current.myconf.take('zenodo.sandbox_access_token')}
        except BaseException:
            raise RuntimeError('Site config does not provide zenodo.sandbox_access_token')

        api = 'https://sandbox.zenodo.org/api/'
    else:
        try:
            token = {'access_token': current.myconf.take('zenodo.access_token')}
        except BaseException:
            raise RuntimeError('Site config does not provide zenodo.access_token')

        api = 'https://zenodo.org/api/'

    # There are then four possible options of things that could be published:
    # 1) a brand new excel-only dataset,
    # 2) an update to an existing excel-only dataset,
    # 3) a brand new dataset with external files and
    # 4) an update to an existing dataset with online files.

    metadata = record.dataset_metadata

    # external_files contains an empty list or a list of dictionaries
    if metadata['external_files']:
        code, links, response = adopt_external_zenodo(api, token, record, deposit_id)
        external = True
    else:
        if record.zenodo_parent_id is None:
            code, links, response = create_excel_zenodo(api, token, record)
        else:
            code, links, response = update_excel_zenodo(api, token, record)
        external = False

    if code > 0:
        # There has been a problem. If this is an internal Excel file only, then try
        # and delete the failed deposit and update the record
        if links is not None and not external:
            # This can fail and leave a hanging deposit, but we won't let that stop the function
            _, _ = delete_deposit(links, token)

        # update the record
        record.update_record(zenodo_submission_status='ZEN_FAIL',
                             zenodo_submission_date=datetime.datetime.now(),
                             zenodo_error=response)
        return "Failed to publish record"
    else:
        # Update the record with the publication details
        record.update_record(zenodo_submission_status='ZEN_PASS',
                             zenodo_submission_date=datetime.datetime.now(),
                             zenodo_metadata=response,
                             zenodo_record_id=response['record_id'],
                             zenodo_version_doi=response['doi_url'],
                             zenodo_version_badge=response['links']['badge'],
                             zenodo_concept_doi=response['links']['conceptdoi'],
                             zenodo_concept_badge=response['links']['conceptbadge'])

        return "Published dataset to {}".format(response['doi_url'])


def create_excel_zenodo(api, token, record):
    """
    A function to work through the Zenodo API steps to publish an new Excel only dataset.
    It works through the publication steps as long as each step keeps returning a zero
    success code, otherwise we get to the end with the most recent failure

    Args:
        api: The API URL to use: sandbox or main site
        token: A dictionary containing the key 'access_token'
        record: The dataset row for the record to publish
    Returns:
        i) An integer code indicating success or failure,
        ii) the links object for the deposit - which is needed to delete
            partially created deposits and
        iii) A response object from Zenodo - which will contain either a
            failure message or the publication details.
    """

    # create the new deposit
    code, response = create_deposit(api, token)

    # upload the record metadata
    if code == 0:
        # store previous response containing the links dictionary
        links = response
        code, response = upload_metadata(links, token, record)
    else:
        links = None

    # upload the file
    if code == 0:
        code, response = upload_file(links, token, record)

    # publish the deposit
    if code == 0:
        code, response = publish_deposit(links, token)

    # Return what we've got
    if code > 0:
        return 1, links, response
    else:
        return 0, links, response


def update_excel_zenodo(api, token, record):
    """
    A function to work through the Zenodo API steps to publish a new version of an Excel
    only dataset. It works through the publication steps as long as each step keeps returning
    a zero success code, otherwise we get to the end with the most recent failure

    Args:
        api: The API URL to use: sandbox or main site
        token: A dictionary containing the key 'access_token'
        record: The dataset row for the record to publish
    Returns:
        i) An integer code indicating success or failure,
        ii) the links object for the deposit - which is needed to delete
            partially created deposits and
        iii) A response object from Zenodo - which will contain either a
            failure message or the publication details.
    """
    # get a new draft of the existing record
    code, response = create_deposit_draft(api, token, record.zenodo_parent_id)

    # upload the record metadata
    if code == 0:
        # store previous response containing the links dictionary
        links = response
        code, response = upload_metadata(links, token, record)
    else:
        links = None

    # delete the existing file
    if code == 0:
        code, response = delete_previous_file(links, token)

    # upload the new file
    if code == 0:
        code, response = upload_file(links, token, record)

    # publish the deposit
    if code == 0:
        code, response = publish_deposit(links, token)

    # Return what we've got
    if code > 0:
        return 1, links, response
    else:
        return 0, links, response


def adopt_external_zenodo(api, token, record, deposit_id):

    """
    A function to work through the Zenodo API steps to publish a dataset that adopts
    external files in an existing deposit. It works through the publication steps as
    long as each step keeps returning a zero success code, otherwise we get to the end
    with the most recent failure

    Args:
        api: The API URL to use: sandbox or main site
        token: A dictionary containing the key 'access_token'
        record: The dataset row for the record to publish
        deposit_id: An integer giving the id of an existing Zenodo deposit to adopt
            using this dataset record.
    Returns:
        i) An integer code indicating success or failure,
        ii) the links object for the deposit - which is needed to delete
            partially created deposits and
        iii) A response object from Zenodo - which will contain either a
            failure message or the publication details.
    """

    # get the deposit
    code, response = get_deposit(api, token, deposit_id)

    # upload the record metadata
    if code == 0:
        # store previous response containing the links dictionary
        # and the list of remote files
        remote_files = response['files']
        links = response['links']
        code, response = upload_metadata(links, token, record)

        # If we got a deposit, check the files found in the deposit match
        # with the external files specified in the record metadata.
        remote_filenames = {rfile['filename'] for rfile in remote_files}
        external_files = set([r['file'] for r in record.dataset_metadata['external_files']])
        
        if not remote_filenames == external_files:
            code = 1
            response = "Files in deposit do not match external files listed in Excel file"
            links = None
    else:
        links = None

    # Upload the Excel file - the expectation here is that the Excel file
    # associated with previous drafts is deleted as part of the manual file
    # update process, so we only have to upload the one submitted to the website
    if code == 0:
        code, response = upload_file(links, token, record)

    # publish the deposit
    if code == 0:
        code, response = publish_deposit(links, token)

    # Return what we've got
    if code > 0:
        return 1, links, response
    else:
        return 0, links, response


"""
Zenodo action functions
"""


def get_deposit(api, token, deposit_id):

    # request the deposit
    dep = requests.get(api + 'deposit/depositions/{}'.format(deposit_id), params=token, json={},
                       headers={"Content-Type": "application/json"})

    # check for success and return the information.
    if dep.status_code != 200:
        return 1, dep.json()
    else:
        return 0, dep.json()


def create_deposit(api, token):
    """
    Function to create a new deposit
    Args:
        api: The api URL to be used (standard or sandbox)
        token: The access token to be usedz
    Returns:
        An integer indicating success (0) or failure (1) and either the
        deposit links dictionary or an error message
    """

    # get a new deposit resource
    dep = requests.post(api + '/deposit/depositions', params=token, json={},
                        headers={"Content-Type": "application/json"})

    # trap errors in creating the resource - successful creation of new deposits returns 201
    if dep.status_code != 201:
        return 1, dep.json()
    else:
        return 0, dep.json()['links']


def create_deposit_draft(api, token, deposit_id):
    """
    Function to create a new draft of an existing published record
    Args:
        api: The api URL to be used (standard or sandbox)
        token: The access token to be used
        deposit_id: The id of the published record
    Returns:
        An integer indicating success (0) or failure (1) and either the
        deposit links dictionary for the new draft or an error message
    """

    # get the draft api
    api = api + '/deposit/depositions/{}/actions/newversion'.format(deposit_id)
    new_draft = requests.post(api, params=token, json={},
                              headers={"Content-Type": "application/json"})

    # trap errors in creating the new version
    if new_draft.status_code != 201:
        return 1, new_draft.json()

    # now get the newly created version
    api = new_draft.json()['links']['latest_draft']
    dep = requests.get(api, params=token, json={},
                       headers={"Content-Type": "application/json"})

    # trap errors in creating the resource - successful creation of new version
    #  drafts returns 200
    if dep.status_code != 200:
        return 1, dep.json()
    else:
        return 0, dep.json()['links']


def upload_metadata(links, token, record):
    """
    Function to turn a dataset row record into a Zenodo metadata JSON and upload
    it to a deposit.

    Args:
        links: The links dictionary from a created deposit
        token: The access token to be used
        record: The database record containing the metadata to be uploaded.

    Returns:
        An integer indicating success (0) or failure (1) and either the
        deposit links dictionary or an error message
    """

    # extract the metadata from the record
    metadata = record.dataset_metadata

    # basic contents
    zen_md = {
        'metadata': {
            "upload_type": "dataset",
            "publication_date": datetime.date.today().isoformat(),
            "title": metadata['title'],
            "keywords": metadata['keywords'],
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
    if metadata['access'] == 'Embargo':
        zen_md['metadata']['access_right'] = 'embargoed'
        zen_md['metadata']['embargo_date'] = metadata['embargo_date']
    elif metadata['access'] == 'Open':
        zen_md['metadata']['access_right'] = 'open'
    elif metadata['access'] == 'Closed':
        zen_md['metadata']['access_right'] = 'closed'

    # set up the dataset creators - the format has already been checked and names
    # should be present and correct. Everything else is optional, so strip None
    # values and pass the rest to Zenodo
    zen_md['metadata']['creators'] = [
        {ky: auth[ky] for ky in auth if auth[ky] is not None and ky != 'email'}
        for auth in metadata['authors']]

    zen_md['metadata']['description'] = str(dataset_description(record, include_gemini=True))

    # attach the metadata to the deposit resource
    mtd = requests.put(links['self'], params=token, data=simplejson.dumps(zen_md),
                       headers={"Content-Type": "application/json"})

    # trap errors in uploading metadata and tidy up
    if mtd.status_code != 200:
        return 1, mtd.json()
    else:
        return 0, 'success'


def upload_file(links, token, record):
    """
    Function to upload the Excel datafile submitted for a record to Zenodo deposit.

    Args:
        links: The links dictionary from a created deposit
        token: The access token to be used
        record: The database record containing the metadata to be uploaded.

    Returns:
        An integer indicating success (0) or failure (1) and either the
        deposit links dictionary or an error message
    """

    # upload the new file
    fname = os.path.join(current.request.folder, 'uploads', 'datasets',
                         str(record.dataset_id), record.file)
    fls = requests.post(links['files'], params=token, files={'file': open(fname, 'rb')})

    # trap errors in uploading file
    # - no success or mismatch in md5 checksums
    if fls.status_code != 201:
        return 1, fls.json()

    if fls.json()['checksum'] != record.file_hash:
        return 1, "Mismatch in local and uploaded MD5 hashes"

    # update the name to the one originally provided by the user
    data = simplejson.dumps({'filename': record.file_name})
    upd = requests.put(fls.json()['links']['self'], data=data,
                       headers={"Content-Type": "application/json"}, params=token)

    # trap errors in updating name
    if upd.status_code != 200:
        return 1, upd.json()
    else:
        return 0, 'success'


def delete_deposit(links, token):
    """
    Function to delete an (unpublished) partially created deposit if the publication
    process fails.

    Args:
        links: The links dictionary from a created deposit
        token: The access token to be used

    Returns:
        An integer indicating success (0) or failure (1) and either the
        deposit links dictionary or an error message
    """

    delete = requests.delete(links['self'], params=token)

    if delete.status_code != 204:
        return 1, delete.json()
    else:
        return 0, 'success'


def publish_deposit(links, token):
    """
    Function to publish a created deposit .

    Args:
        links: The links dictionary from a created deposit
        token: The access token to be used

    Returns:
        An integer indicating success (0) or failure (1) and either the
        deposit links dictionary or an error message
    """

    # publish
    pub = requests.post(links['publish'], params=token)

    # trap errors in publishing, otherwise return the publication metadata
    if pub.status_code != 202:
        return 1, pub.json()
    else:
        return 0, pub.json()


def delete_previous_file(links, token):
    """
    Function to delete a previously uploaded file from a new version of a deposit,
    prior to replacing it with an updated one.

    Args:
        links: The links dictionary from a created deposit
        token: The access token to be used

    Returns:
        An integer indicating success (0) or failure (1) and either the
        deposit links dictionary or an error message
    """

    # get the existing files
    files = requests.get(links['files'], params=token)

    # check the result of the files request
    if files.status_code != 200:
        # failed to get the files
        return 1, files.json()
    elif len(files.json()) != 1:
        # multiple files
        return 1, files.json()

    # get the delete link to the file and call
    delete_api = files.json()[0]['links']['self']
    file_del = requests.delete(delete_api, params=token)

    if file_del.status_code != 204:
        return 1, file_del.json()
    else:
        return 0, 'success'


"""
Description functions
"""


def taxon_index_to_text(taxon_index):
    
    """
    Turns the taxon index for a record into a text representation
    of the taxonomic hierarchy used in the dataset. Loading networkx
    to do this is a bit of a sledgehammer, but reinventing graph from
    edges and depth first search is annoying.
    """
    
    # drop synonyms, which will be represented using the two final tuple entries
    # as_name and as_type
    taxon_index = [tx for tx in taxon_index if tx[4] in ('doubtful', 'accepted', 'user')]
    
    # the taxon index uses -1 for all unvalidated names, since it isn't
    # possible to assign sensible null values inside safe_dataset_checker
    # These need to be made unique within this tree and the names are 
    # formatted to make it clear they are unvalidated
    root = -1
    tmp_num = -2
    for tx in taxon_index:
        if tx[0] == -1:
            tx[0] = tmp_num
            tmp_num -= 1
        if tx[1] is None:
            tx[1] = root

    # Get a graph representation of the taxon index
    g = Graph()
    nodes = [(tx[0], {'nm': tx[2], 'lv': tx[3], 'tp': tx[4], 'as': tx[5], 'aslv': tx[6]})
             for tx in taxon_index]
    g.add_nodes_from(nodes)
    edges = [[tx[1], tx[0]] for tx in taxon_index]
    g.add_edges_from(edges)

    # get a list of successors at each node
    bfs = dict(bfs_successors(g, root))
    names = get_node_attributes(g, 'nm')

    # order successors alphabetically
    for k, v in bfs.iteritems():
        succ = [[nd, names[nd]] for nd in v]
        succ.sort(key=lambda x: x[1])
        bfs[k] = [s[0] for s in succ]
    
    # indent depths - fixed depths for core taxon levels
    taxon_indents = {'kingdom': 0, 'phylum': 1, 'class': 2, 'order': 3, 
                     'family': 4, 'genus': 5, 'species': 6, 'subspecies': 7}
    indent_str = '&ensp;-&ensp;'
    
    # walk the tree, collecting html
    this_node = root
    stack = []
    html = ''
    
    while True:
    
        if this_node in bfs:
            # if this is an internal node, add its children on to
            # the end of the stack
            stack.append(bfs[this_node])
    
        if not stack[-1]:
            # if the end node on the stack has been emptied then
            # pop it off and drop back up to the next node in the stack
            stack.pop()
        else:
            # otherwise, pop the first entry from the node and format and 
            # print out the information for the node
            this_node = stack[-1].pop(0)
            data = g.node[this_node]
            
            # format the canonical name
            if data['lv'] in ['genus', 'species', 'subspecies']:
                string = '<i>{nm}</i>'.format(**data)
            elif data['lv'] in taxon_indents:
                string = data['nm']
            else:
                string = data['nm']

            # markup user defined taxa
            if data['tp'] == 'user':
                string = '[' + string + ']'

                # format and add synonym/misapplications
                if data['as'] is not None and data['aslv'] in ['genus', 'species', 'subspecies']:
                    string += ' (as <i>{as}</i>)'.format(**data)
                elif data['as'] is not None:
                    string += ' (as {as})'.format(**data)

            # get the indent depth
            if data['lv'] in taxon_indents:
                # use the standard depth for this taxonomic level
                ind = indent_str * taxon_indents[data['lv']]
            else:
                # 1 step further in than the current stack length
                ind = indent_str * (len(stack) - 1)

            html += ind + string + '</br>'
    
        if not stack:
            break
    
    return XML(html)


def dataset_description(record, include_gemini=False):
    """
    Function to turn a dataset metadata record into html to send
    to Zenodo and to populate the dataset view. Zenodo has a limited
    set of permitted HTML tags, so this is quite simple HTML, but having
    the exact same information and layout makes sense.
    
    Available tags:
    a, p, br, blockquote, strong, b, u, i, em, ul, ol, li, sub, sup, div, strike.
    
    Note that <a> is currently only available on Zenodo when descriptions are 
    uploaded programatically. A bug in their web interface strips links.
    
    Args:
        record: The db record for the dataset (a row from db.datasets)
        include_gemini: Should the description include a link to the GEMINI XML 
            service? This isn't available on the site datasets page until a dataset
            is published as it contains links to Zenodo, but should also be included 
            in the description uploaded to Zenodo.
    """
    
    # shortcut to metadata
    metadata = record.dataset_metadata
    
    # - get a project link back to the safe website
    db = current.db
    qry = db((db.project_id.id == metadata['project_id']))
    proj = qry.select(
        left=db.project_id.on(db.project_id.project_details_id == db.project_details.id))
    title = proj.first().project_details.title

    # dataset summary
    desc = CAT(B('Description: '), P(XML(metadata['description'].replace('\n', '<br>'))))

    proj_url = URL('projects', 'project_view', args=[metadata['project_id']],
                   scheme=True, host=True)
    desc += P(B('Project: '), 'This dataset was collected as part of the following '
                              'SAFE research project: ', A(B(title), _href=proj_url))
    
    # Funding information
    if metadata['funders']:
        funder_info = []
        for fnd in metadata['funders']:
            this_funder = fnd['type']
            if fnd['ref']:
                this_funder = CAT(this_funder, ', ' + fnd['ref'])
            if fnd['url']:
                this_funder = CAT(this_funder, ', ', A(fnd['url'], _href=fnd['url']))
            
            funder_info.append(LI(CAT(fnd['body'], ' (', this_funder, ')')))
        
        desc += P(B('Funding: '), 'These data were collected as part of '
                  'research funded by: ', UL(funder_info),
                  P('This dataset is released under the CC-BY 4.0 licence, requiring that '
                    'you cite the dataset in any outputs, but has the additional condition '
                    'that you acknowledge the contribution of these funders in any outputs.'))
    
    # Can't get the XML metadata link unless it is published, since that 
    # contains references to the zenodo record
    if include_gemini:
        md_url = URL('datasets', 'xml_metadata', vars={'id': record.id}, scheme=True, host=True)
        desc += P(B('XML metadata: '),
                  'GEMINI compliant metadata for this dataset is available ',
                  A('here', _href=md_url))

    # Present a description of the file or files including 'external' files
    # (data files loaded directly to Zenodo).
    if metadata['external_files']:
        ex_files = metadata['external_files']
        desc += P(B('Files: '), 'This dataset consists of ', len(ex_files) + 1, ' files: ',
                  ', '.join([record.file_name] + [f['file'] for f in ex_files]))
    else:
        ex_files = []
        desc += P(B('Files: '), 'This consists of 1 file: ', record.file_name)

    # Group the sheets by their 'external' file - which is None for sheets
    # in the submitted workbook - and collect them into a dictionary by source file
    tables_by_source = metadata['dataworksheets']

    # Files submitted using early versions of the dataset submission process
    # don't have external in their worksheet dictionaries (but none of those will
    # have external files).
    for tab in tables_by_source:
        if 'external' not in tab:
            tab['external'] = None

    # now group into a dictionary keyed by source file
    tables_by_source.sort(key=lambda sh: sh['external'])
    tables_by_source = groupby(tables_by_source, key=lambda sh: sh['external'])
    tables_by_source = {g: list(v) for g, v in tables_by_source}

    # We've now got a set of files (worksheet + externals) and a dictionary of table
    # descriptions that might have an entry for each file.

    # Report the worksheet first
    desc += P(B(record.file_name))

    if None in tables_by_source:
        # Report internal tables
        desc += P('This file contains dataset metadata and '
                  '{} data tables:'.format(len(tables_by_source[None])))
        table_ol = OL()
        for tab in tables_by_source[None]:
            table_ol.append(LI(table_description(tab)))

        desc += table_ol
    else:
        # No internal tables at all.
        desc += P('This file only contains metadata for the files below')

    # Report on the other files
    for exf in ex_files:
        desc += P(B(exf['file'])) + P('Description: ' + exf['description'])

        if exf['file'] in tables_by_source:
            # Report table description
            desc += P('This file contains {} data tables:'.format(len(tables_by_source[exf['file']])))
            table_ol = OL()
            for tab in tables_by_source[exf['file']]:
                table_ol.append(LI(P(table_description(tab))))

            desc += table_ol

    # Add extents if populated
    if metadata['temporal_extent'] is not None:
        desc += P(B('Date range: '),
                  '{0[0]} to {0[1]}'.format([x[:10] for x in metadata['temporal_extent']]))
    if metadata['latitudinal_extent'] is not None:
        desc += P(B('Latitudinal extent: '),
                  '{0[0]:.4f} to {0[1]:.4f}'.format(metadata['latitudinal_extent']))
    if metadata['longitudinal_extent'] is not None:
        desc += P(B('Longitudinal extent: '),
                  '{0[0]:.4f} to {0[1]:.4f}'.format(metadata['longitudinal_extent']))
    if record.dataset_taxon_index is not None and record.dataset_taxon_index != []:
        desc += CAT(P(B('Taxonomic coverage: '), BR(),
                      ' All taxon names are validated against the GBIF backbone taxonomy. If a '
                      'dataset uses a synonym, the accepted usage is shown followed by the dataset '
                      'usage in brackets. Taxa that cannot be validated, including new species and '
                      'other unknown taxa, morphospecies, functional groups and taxonomic levels '
                      'not used in the GBIF backbone are shown in square brackets.',
                      DIV(taxon_index_to_text(record.dataset_taxon_index))))
    
    return desc


def table_description(tab):
    """
    Function to return a description for an individual source file in a dataset.
    Typically datasets only have a single source file - the Excel workbook that
    also contains the metadata - but they may also report on external files loaded
    directly to Zenodo, and which uses the same mechanism.

    Args:
        tab: A dict describing a data table

    Returns:
        A gluon object containing an HTML description of the table
    """

    # table summary
    tab_desc = CAT(P(B(tab['title']), ' (described in worksheet ', tab['name'], ')'),
                   P('Description: ', tab['description']),
                   P('Number of fields: ', tab['max_col'] - 1))

    # The explicit n_data_row key isn't available for older records
    if 'n_data_row' in tab:
        if tab['n_data_row'] == 0:
            tab_desc += P('Number of data rows: Unavailable (table metadata description only).')
        else:
            tab_desc += P('Number of data rows: {}'.format(tab['n_data_row']))
    else:
        tab_desc += P('Number of data rows: {}'.format(tab['max_row'] - len(tab['descriptors'])))

    # add fields
    tab_desc += P('Fields: ')

    # fields summary
    flds = UL()
    for each_fld in tab['fields']:
        flds.append(LI(B(each_fld['field_name']),
                       ': ', each_fld['description'],
                       ' (Field type: ', each_fld['field_type'], ')'))

    return tab_desc + flds


def generate_inspire_xml(record):
    
    """
    Produces an INSPIRE/GEMINI formatted XML record from a dataset
    record, using a template XML file stored in the static files
    """
    
    # get the dataset and zenodo metadata
    dataset_md = record.dataset_metadata
    zenodo_md = record.zenodo_metadata
    
    # parse the XML template and get the namespace map
    template = os.path.join(current.request.folder, 'static', 'files', 'gemini_xml_template.xml')
    tree = etree.parse(template)
    root = tree.getroot()
    nsmap = root.nsmap
    
    # Use find and XPATH to populate the template, working through from the top of the file
    
    # file identifier
    root.find('./gmd:fileIdentifier/gco:CharacterString',
              nsmap).text = 'zenodo.' + str(record.zenodo_record_id)
    
    # date stamp (not clear what this is - taken as publication date)
    root.find('./gmd:dateStamp/gco:DateTime',
              nsmap).text = record.zenodo_submission_date.isoformat()
    
    # Now zoom to the data identication section
    data_id = root.find('.//gmd:MD_DataIdentification', nsmap)
    
    # CITATION
    citation = data_id.find('gmd:citation/gmd:CI_Citation', nsmap)
    citation.find('gmd:title/gco:CharacterString',
                  nsmap).text = dataset_md['title']
    citation.find('gmd:date/gmd:CI_Date/gmd:date/gco:Date',
                  nsmap).text = record.zenodo_submission_date.date().isoformat()

    # two identifiers - the safe project website and the DOI.
    safe_url = URL('datasets', 'view_dataset', vars={'id': record.id}, scheme=True, host=True)
    citation.find('gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString',
                  nsmap).text = safe_url
    citation.find('gmd:identifier/gmd:RS_Identifier/gmd:code/gco:CharacterString',
                  nsmap).text = record.zenodo_version_doi
    
    # The citation string
    authors = [au['name'] for au in dataset_md['authors']]
    author_string = ', '.join(authors)
    if len(authors) > 1:
        author_string = author_string.replace(', ' + authors[-1], ' & ' + authors[-1])

    cite_string = '{} ({}) {} [Dataset] {}'.format(author_string,
                                                   record.zenodo_submission_date.year,
                                                   record.dataset_title,
                                                   record.zenodo_version_doi)
    
    citation.find('gmd:otherCitationDetails/gco:CharacterString', nsmap).text = cite_string
    
    # ABSTRACT
    data_id.find('gmd:abstract/gco:CharacterString', nsmap).text = dataset_md['description']
    
    # KEYWORDS
    # - find the container node for the free keywords
    keywords = data_id.find('./gmd:descriptiveKeywords/gmd:MD_Keywords', nsmap)
    # - get the placeholder node
    keywd_node = keywords.getchildren()[0]
    # - duplicate it if needed
    for new_keywd in range(len(dataset_md['keywords']) - 1):
        keywords.append(copy.deepcopy(keywd_node))
    # populate the nodes
    for key_node, val in zip(keywords.getchildren(), dataset_md['keywords']):
        key_node.find('./gco:CharacterString', nsmap).text = val
    
    # AUTHORS - find the point of contact with author role from the template and its index
    # using xpath() here to access full xpath predicate search.
    au_xpath = "./gmd:pointOfContact[gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode='author']"
    au_node = data_id.xpath(au_xpath, namespaces=nsmap)[0]
    au_idx = data_id.index(au_node)
    
    # - duplicate it if needed into the tree
    for n in range(len(dataset_md['authors']) - 1):
        data_id.insert(au_idx, copy.deepcopy(au_node))
    
    # now populate the author nodes, there should now be one for each author
    au_ls_xpath = "./gmd:pointOfContact[gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode='author']"
    au_node_list = data_id.xpath(au_ls_xpath, namespaces=nsmap)
    
    for au_data, au_node in zip(dataset_md['authors'], au_node_list):
        resp_party = au_node.find('gmd:CI_ResponsibleParty', nsmap)
        resp_party.find('gmd:individualName/gco:CharacterString',
                        nsmap).text = au_data['name']
        resp_party.find('gmd:organisationName/gco:CharacterString',
                        nsmap).text = au_data['affiliation']
        contact_info = resp_party.find('gmd:contactInfo/gmd:CI_Contact', nsmap)
        email_path = 'gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString'
        contact_info.find(email_path, nsmap).text = au_data['email']
        
        # handle orcid resource
        orcid = contact_info.find('gmd:onlineResource', nsmap)
        if au_data['orcid'] is None:
            contact_info.remove(orcid)
        else:
            orcid.find('gmd:CI_OnlineResource/gmd:linkage/gmd:URL',
                       nsmap).text = 'http://orcid.org/' + au_data['orcid']
    
    # CONSTRAINTS 
    # update the citation information in the second md constraint
    md_path = 'gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString'
    md_constraint = data_id.find(md_path, nsmap)
    md_constraint.text += cite_string
    
    # embargo or not?
    embargo_path = ('gmd:resourceConstraints/gmd:MD_LegalConstraints/'
                    'gmd:otherConstraints/gco:CharacterString')
    if dataset_md['access'] == 'embargo':
        data_id.find(embargo_path, nsmap).text = ('This data is under embargo until {}. After '
                                                  'that date there are no restrictions to public '
                                                  'access.').format(dataset_md['embargo_date'])
    elif dataset_md['access'] == 'closed':
        data_id.find(embargo_path, nsmap).text = ('This dataset is currently not publicly '
                                                  'available, please contact the authors to '
                                                  'request access.')
    else:
        data_id.find(embargo_path, nsmap).text = 'There are no restrictions to public access.'
    
    # EXTENTS
    temp_extent = root.find('.//gmd:EX_TemporalExtent', nsmap)
    temp_extent.find('.//gml:beginPosition', nsmap).text = dataset_md['temporal_extent'][0][:10]
    temp_extent.find('.//gml:endPosition', nsmap).text = dataset_md['temporal_extent'][1][:10]
    
    geo_extent = root.find('.//gmd:EX_GeographicBoundingBox', nsmap)
    geo_extent.find('./gmd:westBoundLongitude/gco:Decimal',
                    nsmap).text = str(dataset_md['longitudinal_extent'][0])
    geo_extent.find('./gmd:eastBoundLongitude/gco:Decimal',
                    nsmap).text = str(dataset_md['longitudinal_extent'][1])
    geo_extent.find('./gmd:southBoundLatitude/gco:Decimal',
                    nsmap).text = str(dataset_md['latitudinal_extent'][0])
    geo_extent.find('./gmd:northBoundLatitude/gco:Decimal',
                    nsmap).text = str(dataset_md['latitudinal_extent'][1])
    
    # Dataset transfer options: direct download and dataset view on SAFE website
    distrib = root.find('gmd:distributionInfo/gmd:MD_Distribution', nsmap)
    distrib.find(('gmd:transferOptions[1]/gmd:MD_DigitalTransferOptions/gmd:onLine/'
                  'gmd:CI_OnlineResource/gmd:linkage/gmd:URL'),
                 nsmap).text = zenodo_md['files'][0]['links']['download']
    distrib.find(('gmd:transferOptions[2]/gmd:MD_DigitalTransferOptions/gmd:onLine/'
                  'gmd:CI_OnlineResource/gmd:linkage/gmd:URL'), nsmap).text += str(record.id)
    
    # LINEAGE STATEMENT
    lineage = ("This dataset was collected as part of a research project based at The"
               " SAFE Project. For details of the project and data collection, see the "
               "methods information contained within the datafile and the project "
               "website: ") + URL('projects', 'view_project', args=record.project_id,
                                  scheme=True, host=True)
    root.find(('gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/'
               'gmd:statement/gco:CharacterString'), nsmap).text = lineage
    
    # return the string contents
    return etree.tostring(tree)
