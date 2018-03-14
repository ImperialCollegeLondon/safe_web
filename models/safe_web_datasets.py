import sys
import lxml
import simplejson
import copy
import safe_dataset_checker
from gluon.contrib.appconfig import AppConfig
from networkx import Graph, bfs_successors, get_node_attributes

"""
Functions to handle datasets. These are called from the datasets controller but 
are also needed from other locations, such as the scheduler, so are defined here
in their own model.
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
        gbif_db = myconf.take('gbif.gbif_database')
    except BaseException:
        raise RuntimeError('Site config does not provide a path for the gbif database')
    
    # Load the host name from the configuration. When run from a controller,
    # the URL(host=TRUE) has access to the host name from requests. This isn't
    # true when it is run by a scheduler worker, which isn't operating as part
    # of the website. So rather than hardcoding, store the host name in the config
    try:
        host = myconf.take('host.host_name')
    except BaseException:
        raise RuntimeError('Site config does provide not the host name')
    
    # get the record
    record = db.datasets[record_id]
    
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
        ret_dict = {'dataset_id': record.dataset_id, 
                    'report': '',
                    'filename': record.file_name,
                    'name': record.uploader_id.first_name,
                    'dataset_url': URL('datasets', 'submit_dataset', 
                                       vars={'dataset_id': record.dataset_id}, scheme=True, host=host)}
        outcome = 'ERROR'
    
    # Initialise the dataset checker:
    if not error:
        # - get paths to dataset file. Failure to find is handled by safe_dataset_checker methods.
        fname = os.path.join(request.folder,'uploads','datasets', str(record.dataset_id), record.file)
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
            ret_msg = 'Verifying dataset {}: error initialising dataset checker'.format(record.dataset_id)
            error = True
    
    # main processing of the dataset
    if not error:
        try:
            # load the metadata sheets
            dataset.load_summary(validate_doi=True, project_id=record.project_id)
            dataset.load_taxa()
            # use a local locations file - there is some issue with using the service from within the code
            locations_json = os.path.join(request.folder,'static','files','locations.json')
            dataset.load_locations(locations_json=locations_json)
            
            # check the datasets
            for ws in dataset.dataworksheet_summaries:
                dataset.load_data_worksheet(ws)
            
            # cross check the taxa and locations
            dataset.final_checks()
            
        except Exception as e:
            ret_msg = 'Verifying dataset {}: error running dataset checking'.format(record.dataset_id)
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
                             dataset_title = dataset.title,
                             dataset_metadata = dataset.export_metadata_dict(),
                             dataset_taxon_index = dataset.taxon_index,
                             dataset_locations = dataset.locations)
    
    # notify the user
    if email:
        opts = {'PASS': ['Dataset passed checks', 'dataset_check_pass.html'],
                'FAIL': ['Dataset failed checks', 'dataset_check_fail.html'],
                'ERROR': ['Error checking dataset', 'dataset_check_error.html']}
        
        SAFEmailer(to=record.uploader_id.email,
                   subject=opts[outcome][0],
                   template=opts[outcome][1],
                   template_dict= ret_dict)
    
    # A task run by a worker does not automatically commit changes, so
    # save any by changes before ending
    db.commit()
    
    return ret_msg


def submit_dataset_to_zenodo(recid, sandbox=False):
    
    """
    Controller to submit a dataset to Zenodo and to update the
    dataset record with the result of that attempt.
    
    Args:
        recid: The id of the dataset table record to be submitted
        sandbox: Should the sandbox API be used - retained for 
            admin testing
    Returns:
        A string describing the outcome.
    """
    
    # check the record exists and hasn't already been submitted
    record = db.datasets[recid]
    
    if sandbox:
        api = 'https://sandbox.zenodo.org/api'
    else:
        api = 'https://zenodo.org/api/'
    
    if record is None:
        return 'Publishing dataset: unknown record ID {}'.format(id)
    elif record.dataset_check_outcome != 'PASS':
        return 'Publishing dataset: record ID {} has not passed format checking'.format(id)
    elif record.zenodo_submission_status == 'ZEN_PASS':
        return 'Publishing dataset: record ID {} already published'.format(id)
    else:
        
        # A) BUILD THE METADATA FOR THIS DATASET
        # - load the metadata from the database to populate the contents
        metadata = record.dataset_metadata
        
        # basic contents
        zenodo_metadata = {
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
            zenodo_metadata['metadata']['access_right'] = 'embargoed'
            zenodo_metadata['metadata']['embargo_date'] = metadata['embargo_date']
        elif metadata['access'] == 'Open':
            zenodo_metadata['metadata']['access_right'] = 'open'
        else:
            return 'Publishing dataset: record ID {} has unknown access status: {}'.format(id, metadata['access'])
        
        # set up the dataset creators
        zenodo_metadata['metadata']['creators'] = []
        for auth in  metadata['authors']:
            creator = {ky: auth[ky] for ky in ('name', 'affiliation')}
            if auth['orcid'] is not None:
                creator['orcid'] = auth['orcid']
            
            zenodo_metadata['metadata']['creators'].append(creator)
        
        zenodo_metadata['metadata']['description'] = str(_dataset_description(record, include_gemini=True))
        
        # B) NOW PUSH TO ZENODO
        # get the authentication token from the private folder
        auth = os.path.join(request.folder, 'private','zenodo_token.json')
        token = simplejson.load(open(auth))
        
        # headers description
        hdr = {"Content-Type": "application/json"}
        
        # Are we publishing a new version of a file that has already been published?
        # The record will have a populated zenodo_parent_id field, either None or 
        # inherited from the last published predecessor .
        
        if record.zenodo_parent_id is None:
            # get a new deposit resource
            dep = requests.post(api + '/deposit/depositions', params=token, json={}, headers= hdr)
        else:
            # get a new draft by passing in a reference to the previous version.
            api = api + '/deposit/depositions/{}/actions/newversion'.format(record.zenodo_parent_id)
            new_draft = requests.post(api, params=token, json={}, headers= hdr)
            
            # trap errors in creating the new version
            if new_draft.status_code != 201:
                record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                     zenodo_submission_date=datetime.datetime.now(),
                                     zenodo_error = new_draft.json())
                return "Failed to obtain new version of deposit"
            
            # now get the newly created version
            dep = requests.get(new_draft.json()['links']['latest_draft'],
                               params=token, json={}, headers= hdr)
        
        # trap errors in creating the resource - successful creation of new
        # deposits returns 201 and of new version drafts returns 200
        if dep.status_code not in [200, 201]:
            record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = dep.json())
            return "Failed to obtain deposit"
        
        # get the links dictionary out of the deposit resource
        links = dep.json()['links']
        
        # attach the metadata to the deposit resource
        mtd = requests.put(links['self'], params=token, data=simplejson.dumps(zenodo_metadata), headers=hdr)
        
        # trap errors in uploading metadata and tidy up
        if mtd.status_code != 200:
            record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = mtd.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to upload metadata"
        
        # for new versions of existing datasets delete earlier versions of file
        if record.zenodo_parent_id is not None:
            # get the existing files
            files = requests.get(links['files'], params=token)
            
            if files.status_code != 200:
                record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                     zenodo_submission_date=datetime.datetime.now(),
                                     zenodo_error = files.json())
                delete = requests.delete(links['self'], params=token)
                return "Failed to access existing files"
            elif len(files.json()) != 1:
                record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                     zenodo_submission_date=datetime.datetime.now(),
                                     zenodo_error = files.json())
                delete = requests.delete(links['self'], params=token)
                return "More than one file exists in the deposition"
            
            file_del = requests.delete(files.json()[0]['links']['self'],  params=token)
            
            if file_del.status_code != 204:
                record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                     zenodo_submission_date=datetime.datetime.now(),
                                     zenodo_error = files.json())
                delete = requests.delete(links['self'], params=token)
                return "Failed to delete existing file"
            
        # upload the new file
        fname = os.path.join(request.folder, 'uploads', 'datasets', str(record.dataset_id), record.file)
        fls = requests.post(links['files'], params=token, files={'file': open(fname, 'rb')})
        
        # trap errors in uploading file
        # - no success or mismatch in md5 checksums
        if fls.status_code != 201:
            record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = fls.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to upload dataset"
        elif fls.json()['checksum'] != record.file_hash:
            record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = fls.json())
            delete = requests.delete(links['self'], params=token)
            return "Mismatch in local and uploaded MD5 hashes"
        
        # update the name to the one originally provided by the user
        data = simplejson.dumps({'filename': record.file_name})
        upd = requests.put(fls.json()['links']['self'], data=data, headers=hdr, params=token)
        
        # trap errors in updating name
        if upd.status_code != 200:
            record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = upd.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to update filename"
        
        # publish
        pub = requests.post(links['publish'], params=token)
        
        # trap errors in publishing
        if pub.status_code != 202:
            record.update_record(zenodo_submission_status = 'ZEN_FAIL',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = pub.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to publish dataset"
        else:
            # store the publication metadata - contains DOI, file links etc
            # but remove the metadata element, which duplicates the 
            # content in db.datasets.dataset_metadata
            pub_json = pub.json()
            del pub_json['metadata']
            
            record.update_record(zenodo_submission_status = 'ZEN_PASS',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_metadata = pub_json,
                                 zenodo_record_id = pub_json['record_id'],
                                 zenodo_version_doi = pub_json['doi_url'],
                                 zenodo_version_badge = pub_json['links']['badge'],
                                 zenodo_concept_doi = pub_json['links']['conceptdoi'],
                                 zenodo_concept_badge = pub_json['links']['conceptbadge'])
            
            return "Published dataset to {}".format(pub_json['doi_url'])


def _taxon_index_to_text(taxon_index):
    
    """
    Turns the taxon index for a record into a text representation
    of the taxonomic hierarchy used in the dataset. Loading networkx
    to do this is a bit of a sledgehammer, but reinventing graph from
    edges and depth first search is annoying.
    """
    
    # drop synonyms, which will be represented using the two final tuple entries as_name and as_type
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
    nodes = [(tx[0], {'nm': tx[2], 'lv': tx[3], 'tp': tx[4], 'as': tx[5], 'aslv': tx[6]}) for tx in taxon_index]
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
    current = root
    stack = []
    html = ''
    
    while True:
    
        if current in bfs:
            # if this is an internal node, add its children on to
            # the end of the stack
            stack.append(bfs[current])
    
        if stack[-1] == []:
            # if the end node on the stack has been emptied then
            # pop it off and drop back up to the next node in the stack
            stack.pop()
        else:
            # otherwise, pop the first entry from the node and format and 
            # print out the information for the node
            current = stack[-1].pop(0)
            data = g.node[current]
            
            # format the canonical name
            if data['lv'] in ['genus','species','subspecies']:
                string = '<i>{nm}</i>'.format(**data)
            elif data['lv'] in taxon_indents:
                string = data['nm']
            else:
                string = data['nm']
	    
	    # markup user defined taxa
	    if data['tp'] == 'user':
		string = '[' + string + ']'
                
            # format and add synonym/misapplications
            if data['as'] is not None and data['aslv'] in ['genus','species','subspecies']:
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
    
        if stack == []:
            break
    
    return XML(html)


def _dataset_description(record, include_gemini=False):
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
    
    # - get a project link back to the safe website (although Zenodo doesn't support links)
    qry = db((db.project_id.id == metadata['project_id']))
    proj = qry.select(left=db.project_id.on(db.project_id.project_details_id == db.project_details.id))
    title = proj.first().project_details.title
    
    # dataset summary
    
    desc = CAT(B('Description: '), P(XML(metadata['description'].replace('\n', '<br>'))))
    
    proj_url = URL('projects','project_view', args=[metadata['project_id']], scheme=True, host=True)
    desc += P(B('Project: '),  'This dataset was collected as part of the following '
                'SAFE research project: ', A(B(title), _href=proj_url))
    
    # Can't get the XML metadata link unless it is published, since that 
    # contains references to the zenodo record
    if include_gemini:
        md_url = URL('datasets','xml_metadata', vars={'id': record.id}, scheme=True, host=True)
        desc += P(B('XML metadata: '), 'GEMINI compliant metadata for this dataset '
                  'is available ', A('here', _href=md_url))

    desc += P(B('Data worksheets: '), 'There are {} data worksheets in this '
              'dataset:'.format(len(metadata['dataworksheets'])))
    
    dwshts = OL()
    
    for ds in metadata['dataworksheets']:
        
        # data worksheet summary
        dwsh = CAT(P(B(ds['title']), ' (Worksheet ', ds['name'], ')'),
                    P('Dimensions: ', ds['max_row'], ' rows by ', ds['max_col'], ' columns') +
                    P('Description: ', ds['description']),
                    P('Fields: '))
        
        # fields summary
        flds = UL()
        for each_fld in ds['fields']:
            flds.append(LI(B(each_fld['field_name']), 
                           ': ', each_fld['description'],
                           ' (Field type: ', each_fld['field_type'], ')'))
        
        dwshts.append(LI(CAT(dwsh, flds, BR())))
    
    desc += dwshts
    
    # Add extents if populated
    if metadata['temporal_extent'] is not None:
        desc += P(B('Date range: '), '{0[0]} to {0[1]}'.format([x[:10] for x in metadata['temporal_extent']]))
    if metadata['latitudinal_extent'] is not None:
        desc += P(B('Latitudinal extent: '), '{0[0]:.4f} to {0[1]:.4f}'.format(metadata['latitudinal_extent']))
    if metadata['longitudinal_extent'] is not None:
        desc += P(B('Longitudinal extent: '), '{0[0]:.4f} to {0[1]:.4f}'.format(metadata['longitudinal_extent']))
    if record.dataset_taxon_index is not None and record.dataset_taxon_index != []:
        desc +=  CAT(P(B('Taxonomic coverage: '), BR(), ' All taxon names are validated against the GBIF backbone '
                       'taxonomy. If a dataset uses a synonym, the accepted usage is shown followed by the dataset '
                       'usage in brackets. Taxa that cannot be validated, including new species and other unknown '
                       'taxa, morphospecies, functional groups and taxonomic levels not used in the '
                       'GBIF backbone are shown in square brackets.',
                     DIV(_taxon_index_to_text(record.dataset_taxon_index))))
    
    return desc


def generate_inspire_xml(record):
    
    """
    Produces an INSPIRE/GEMINI formatted XML record from a dataset
    record, using a template XML file stored in the static files
    """
    
    # get the dataset and zenodo metadata
    dataset_md = record.dataset_metadata
    zenodo_md = record.zenodo_metadata
    
    # parse the XML template and get the namespace map
    template = os.path.join(request.folder, 'static', 'files', 'gemini_xml_template.xml')
    tree = lxml.etree.parse(template)
    root = tree.getroot()
    nsmap = root.nsmap
    
    # Use find and XPATH to populate the template, working through from the top of the file
    
    # file identifier
    root.find('./gmd:fileIdentifier/gco:CharacterString', nsmap).text = 'zenodo.' + str(record.zenodo_record_id)
    
    # date stamp (not clear what this is - taken as publication date)
    root.find('./gmd:dateStamp/gco:DateTime', nsmap).text = record.zenodo_submission_date.isoformat()
    
    # Now zoom to the data identication section
    data_id = root.find('.//gmd:MD_DataIdentification', nsmap)
    
    # CITATION
    citation = data_id.find('gmd:citation/gmd:CI_Citation', nsmap)
    citation.find('gmd:title/gco:CharacterString', nsmap).text = dataset_md['title']
    citation.find('gmd:date/gmd:CI_Date/gmd:date/gco:Date', nsmap).text = record.zenodo_submission_date.date().isoformat()

    # two identifiers - the safe project website and the DOI.
    safe_url = URL('datasets', 'view_dataset', vars={'id': record.id}, scheme=True, host=True)
    citation.find('gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString', nsmap).text = safe_url
    citation.find('gmd:identifier/gmd:RS_Identifier/gmd:code/gco:CharacterString', nsmap).text = record.zenodo_version_doi
    
    # The citation string
    authors = [au['name'] for au in dataset_md['authors']]
    author_string = ', '.join(authors)
    if len(authors) > 1:
        author_string = author_string.replace(', ' + authors[-1], ' & ' + authors[-1])
    
    cite_string = '{} ({}) {} [Dataset] {}'.format(author_string, record.zenodo_submission_date.year, 
                                                   record.dataset_title, record.zenodo_version_doi)
    
    citation.find('gmd:otherCitationDetails/gco:CharacterString', nsmap).text = cite_string
    
    # ABSTRACT
    data_id.find('gmd:abstract/gco:CharacterString', nsmap).text = dataset_md['description']
    
    # KEYWORDS
    # - find the container node for the free keywords
    keywords  = data_id.find('./gmd:descriptiveKeywords/gmd:MD_Keywords', nsmap)
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
    au_node = data_id.xpath("./gmd:pointOfContact[gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode='author']", 
                            namespaces=nsmap)[0]
    au_idx = data_id.index(au_node)
    
    # - duplicate it if needed into the tree
    for n in range(len(dataset_md['authors']) - 1):
        data_id.insert(au_idx, copy.deepcopy(au_node))
    
    # now populate the author nodes, there should now be one for each author
    au_node_list = data_id.xpath("./gmd:pointOfContact[gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode='author']", 
                                 namespaces=nsmap)
    
    for au_data, au_node in zip(dataset_md['authors'], au_node_list):
        resp_party = au_node.find('gmd:CI_ResponsibleParty', nsmap)
        resp_party.find('gmd:individualName/gco:CharacterString', nsmap).text = au_data['name']
        resp_party.find('gmd:organisationName/gco:CharacterString', nsmap).text = au_data['affiliation']
        contact_info = resp_party.find('gmd:contactInfo/gmd:CI_Contact', nsmap)
        contact_info.find('gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString', nsmap).text = au_data['email']
        
        # handle orcid resource
        orcid = contact_info.find('gmd:onlineResource', nsmap)
        if au_data['orcid'] is None:
            contact_info.remove(orcid)
        else:
            orcid.find('gmd:CI_OnlineResource/gmd:linkage/gmd:URL', nsmap).text = 'http://orcid.org/' + au_data['orcid']
    
    # CONSTRAINTS 
    # update the citation information in the second md constraint
    md_constraint = data_id.find('gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString', nsmap)
    md_constraint.text += cite_string
    
    # embargo or not?
    embargo_constraint = data_id.find('gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString', nsmap)
    if dataset_md['access'] == 'embargo':
        embargo_constraint = ('This data is under embargo until {}. After that date there are '
                              'no restrictions to public access.').format(dataset_md['embargo_date'])
    else:
        embargo_constraint = 'There are no restrictions to public access.'
    
    # EXTENTS
    temp_extent = root.find('.//gmd:EX_TemporalExtent', nsmap)
    temp_extent.find('.//gml:beginPosition', nsmap).text = dataset_md['temporal_extent'][0][:10]
    temp_extent.find('.//gml:endPosition', nsmap).text = dataset_md['temporal_extent'][1][:10]
    
    geo_extent = root.find('.//gmd:EX_GeographicBoundingBox', nsmap)
    geo_extent.find('./gmd:westBoundLongitude/gco:Decimal', nsmap).text = str(dataset_md['longitudinal_extent'][0])
    geo_extent.find('./gmd:eastBoundLongitude/gco:Decimal', nsmap).text = str(dataset_md['longitudinal_extent'][1])
    geo_extent.find('./gmd:southBoundLatitude/gco:Decimal', nsmap).text = str(dataset_md['latitudinal_extent'][0])
    geo_extent.find('./gmd:northBoundLatitude/gco:Decimal', nsmap).text = str(dataset_md['latitudinal_extent'][1])
    
    # Dataset transfer options: direct download and dataset view on SAFE website
    distrib = root.find('gmd:distributionInfo/gmd:MD_Distribution', nsmap)
    distrib.find(('gmd:transferOptions[1]/gmd:MD_DigitalTransferOptions/gmd:onLine/'
                  'gmd:CI_OnlineResource/gmd:linkage/gmd:URL'), nsmap).text = zenodo_md['files'][0]['links']['download']
    distrib.find(('gmd:transferOptions[2]/gmd:MD_DigitalTransferOptions/gmd:onLine/'
                  'gmd:CI_OnlineResource/gmd:linkage/gmd:URL'), nsmap).text += str(record.id)
    
    # LINEAGE STATEMENT
    lineage = ("This dataset was collected as part of a research project based at The SAFE Project. For details of " 
               "the project and data collection, see the methods information contained within the datafile and the "
               "project website: ") + URL('projects', 'view_project', args=record.project_id, scheme=True, host=True)
    root.find(('gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/'
               'gmd:statement/gco:CharacterString'), nsmap).text = lineage
    
    # return the string contents
    return lxml.etree.tostring(tree)
    
    
