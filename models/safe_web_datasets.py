import lxml
import simplejson
import copy

"""
Functions to handle datasets. These are called from the datasets controller but 
are also needed from other locations, such as the scheduler, so are defined here
in their own model.
"""


def verify_dataset(id, email=False):
    """
    Function to run the safe_dataset_checker on an uploaded file. There
    are three possible outcomes for a dataset: PASS; FAIL, if the check
    catches known formatting problems; and ERROR if check hits an exception,
    which probably means an update to the checker code to handle the new
    and exciting way of getting the file wrong.
    
    The email argument allows the function to be run by admins directly
    using the administer_datasets controller without spamming the uploader. 
    Useful in error checking problem uploads.
    
    Args:
        id: The id of the record from the dataset table that is to be checked.
        email: Should the dataset uploader be emailed the outcome?
    
    Returns:
        A string describing the outcome of the check that gets stored in the
        scheduler results or sent back to the administer_datasets controller.
    """

    
    # check the configuration includes a path to the ete3_database
    if 'ete3' not in myconf or 'ete3_database' not in myconf['ete3']:
        raise RuntimeError('Site not correctly configured to use ete3 for taxon checking')
    
    # get the record
    record = db.datasets[id]
    
    # track errors to avoid hideous nesting
    error = False
        
    if record is None:
        ret_msg = 'Verifying dataset {}: unknown record ID'.format(id)
        ret_dict = {'id': id, 'report': '', 'filename': '', 'name': record.uploader_id.first_name}
        error = True
    
    # Initialise the dataset checker:
    if not error:
        # - get paths to dataset file. Failure to find is handled by safe_dataset_checker methods.
        fname = os.path.join(request.folder,'uploads','datasets', record.file)
        # get the Dataset object from the file checker - don't use the high level
        # check file function to separate ete3 config problems
        try:
            dataset = safe_dataset_checker.Dataset(fname, verbose=False, 
                                                   ete3_database=myconf['ete3']['ete3_database'])
        except Exception as e:
            record.update_record(dataset_check_outcome='ERROR',
                                 dataset_check_error=repr(e))
            ret_msg = 'Verifying dataset {}: error initialising dataset checker'.format(id)
            ret_dict = {'id': id, 'report': '', 'filename': record.file_name,
                        'name': record.uploader_id.first_name}
            error = True
    
    # make sure we are using ete3
    if not error and not dataset.use_ete:
        record.update_record(dataset_check_outcome='ERROR',
                             dataset_check_error=dataset.ete_failure)
        ret_msg = 'Verifying dataset {}: error setting up ete3 taxonomy checking'.format(id)
        ret_dict = {'id': id, 'report': '', 'filename': record.file_name,
                    'name': record.uploader_id.first_name}
        error = True
    
    # main processing of the dataset
    if not error:
        try:
            # load the metadata sheets
            dataset.load_summary()
            dataset.load_taxa(check_all_ranks=False)
            # use a local locations file - there is some issue with using the service from within the code
            locations_json = os.path.join(request.folder,'static','files','locations.json')
            dataset.load_locations(locations_json=locations_json)
            
            # check the datasets
            if dataset.dataworksheet_summaries:
                for ws in dataset.dataworksheet_summaries:
                    dataset.load_data_worksheet(ws)
            else:
                dataset.warn('No data worksheets found')
        
        except Exception as e:
            outcome = 'ERROR'
            ret_msg = 'Verifying dataset {}: error running dataset checking'.format(id)
            dataset_check_error = repr(e)
        else:
            # Catch the only bit of cross-validation: does the dataset project id match
            # to the one chosen on upload
            if dataset.project_id != record.project_id:
                dataset.warn('Project ID in dataset and on upload do not match')
        
            if dataset.n_warnings:
                outcome = 'FAIL'
                ret_msg = 'Verifying dataset {}: dataset checking FAILED'.format(id)
            else:
                outcome = 'PASS'
                ret_msg = 'Verifying dataset {}: dataset checking PASSED'.format(id)
            
            dataset_check_error = ''
        
        # At this point, we have a Dataset object, so can populate the record with 
        # what information is available, regardless of Error, Fail or Pass
        # i) the sample locations as JSON
        if dataset.locations is not None:
            locations_json = simplejson.dumps(list(dataset.locations))
        else:
            locations_json = simplejson.dumps([])
        
        # ii) the taxon index as JSON
        if dataset.taxon_index is not None:
            taxon_index_json = simplejson.dumps(dataset.taxon_index)
        else:
            taxon_index_json = simplejson.dumps([])
        
        # iii) the check report as str
        report_text = dataset.report().getvalue()
        
        # substitute in the user filename for the local web2py filename
        report_text = report_text.replace(fname, record.file_name)
        
        # iv) the dataset metadata, converting to JSON using a convertor
        #   to handle datetime objects.
        metadata = dataset.export_metadata_dict()
        metadata_json = simplejson.dumps(metadata, default=json_datetime)
            
        record.update_record(dataset_check_outcome=outcome,
                             dataset_check_report=PRE(report_text),
                             dataset_check_error=dataset_check_error,
                             dataset_title = dataset.title,
                             dataset_metadata = metadata_json,
                             dataset_taxon_index = taxon_index_json,
                             dataset_locations = locations_json)
        
        ret_dict = {'id': id, 'report': report_text, 
                    'filename': record.file_name,
                    'name': record.uploader_id.first_name}
        
    # notify the user
    if email:
        opts = {'PASS': ['Dataset passed checks', 'dataset_check_pass.html'],
                'FAIL': ['Dataset failed checks', 'dataset_check_fail.html'],
                'ERROR': ['Error checking dataset', 'dataset_check_error.html']}
        
        SAFEmailer(to=record.uploader_id.email,
                   subject=opts[outcome][0],
                   template=opts[outcome][1],
                   template_dict= ret_dict)
    
    return ret_msg


def json_datetime(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        serial = obj.isoformat()
        return serial

    raise TypeError("Type %s not serializable" % type(obj))


def submit_dataset_to_zenodo(recid):
    
    """
    Controller to submit a dataset to Zenodo and to update the
    dataset record with the result of that attempt.
    
    Args:
        id: The id of the dataset table record to be submitted
    
    Returns:
        A string describing the outcome.
    """
    
    # check the record exists and hasn't already been submitted
    record = db.datasets[recid]
    
    if record is None:
        return 'Publishing dataset: unknown record ID {}'.format(id)
    elif record.dataset_check_outcome != 'PASS':
        return 'Publishing dataset: record ID {} has not passed format checking'.format(id)
    elif record.zenodo_submission_status == 'Published':
        return 'Publishing dataset: record ID {} already published'.format(id)
    else:
        
        # A) BUILD THE METADATA FOR THIS DATASET
        # - load the metadata from the database to populate the contents
        metadata = simplejson.loads(record.dataset_metadata)
        
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
        
        zenodo_metadata['metadata']['description'] = str(_dataset_description(metadata))
        
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
                                 zenodo_error = dep.json())
            return "Failed to obtain deposit"
        
        # get the links dictionary out of the deposit resource
        links = dep.json()['links']
                
        # attach the metadata to the deposit resource
        mtd = requests.put(links['self'], params=token, data=simplejson.dumps(zenodo_metadata), headers=hdr)
        
        # trap errors in uploading metadata and tidy up
        if mtd.status_code != 200:
            record.update_record(zenodo_submission_status = 'Failed to upload metadata',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = mtd.json())
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
                                 zenodo_error = fls.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to upload dataset"
        elif fls.json()['checksum'] != record.file_hash:
            record.update_record(zenodo_submission_status = 'Mismatch in local and uploaded MD5 hashes',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = fls.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to upload dataset"
        
        # update the name to the one originally provided by the user
        data = simplejson.dumps({'filename': record.file_name})
        upd = requests.put(fls.json()['links']['self'], data=data, headers=hdr, params=token)
        
        # trap errors in updating name
        if upd.status_code != 200:
            record.update_record(zenodo_submission_status = 'Failed to update filename',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_error = upd.json())
            delete = requests.delete(links['self'], params=token)
            return "Failed to update filename"
        
        # publish
        pub = requests.post(links['publish'], params=token)
        
        # trap errors in publishing
        if pub.status_code != 202:
            record.update_record(zenodo_submission_status = 'Failed to publish dataset',
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
            
            record.update_record(zenodo_submission_status = 'Published',
                                 zenodo_submission_date=datetime.datetime.now(),
                                 zenodo_metadata = pub_json,
                                 zenodo_record_id = pub_json['record_id'],
                                 zenodo_doi = pub_json['doi_url'],
                                 zenodo_badge = pub_json['links']['badge'])
            
            return "Published dataset to {}".format(pub_json['doi_url'])


def _dataset_description(metadata):
    """
    Function to turn a dataset metadata record into html to send
    to Zenodo and to populate the dataset view. Zenodo has a limited
    set of permitted HTML tags, so this is quite simple HTML, but having
    the exact same information and layout makes sense.
    
    Available tags (but a at least doesn't work at present)
    a, p, br, blockquote, strong, b, u, i, em, ul, ol, li, sub, sup, div, strike.
    """
    
    # - get a project link back to the safe website (although Zenodo doesn't support links)
    qry = db((db.project_id.id == metadata['project_id']))
    proj = qry.select(left=db.project_id.on(db.project_id.project_details_id == db.project_details.id))
    title = proj.first().project_details.title
    
    # dataset summart
    desc = CAT(P(B('Description: ')), XML(metadata['description'].replace('\n', '<br>')), BR()*2,
               P(B('Date range: '), '{0[0]} - {0[1]}'.format([x[:10] for x in metadata['temporal_extent']])), 
               P(B('Latitudinal extent: '), '{0[0]:.4f} - {0[1]:.4f}'.format(metadata['latitudinal_extent'])), 
               P(B('Longitudinal extent: '), '{0[0]:.4f} - {0[1]:.4f}'.format(metadata['longitudinal_extent'])),
               P(B('Data worksheets: '), 'There are {} data worksheets in this '
                 'dataset:'.format(len(metadata['dataworksheets']))))
    
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
                           ', Description: ', each_fld['description'],
                           ', Field type: ', each_fld['field_type']))
        
        dwshts.append(LI(CAT(dwsh, flds, BR())))
    
    desc += dwshts
    
    proj_url = URL('projects','project_view', scheme=True, args=[metadata['project_id']])
    desc += CAT(P('This dataset was collected as part of the following SAFE research project: ', B(title)),
                P('For more information see: ', A(proj_url, _href=proj_url)))
    
    return desc


def generate_inspire_xml(record):
    
    """
    Produces an INSPIRE/GEMINI formatted XML record from a dataset
    record, using a template XML file stored in the static files
    """
    
    # get the dataset and zenodo metadata
    dataset_md = simplejson.loads(record.dataset_metadata)
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
    safe_url = URL('datasets', 'view_dataset', vars={'dataset_id': record.id}, scheme=True)
    citation.find('gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString', nsmap).text = safe_url
    citation.find('gmd:identifier/gmd:RS_Identifier/gmd:code/gco:CharacterString', nsmap).text = record.zenodo_doi
    
    # The citation string
    authors = [au['name'] for au in dataset_md['authors']]
    author_string = ', '.join(authors)
    if len(authors) > 1:
        author_string = author_string.replace(', ' + authors[-1], ' & ' + authors[-1])
    
    cite_string = '{} ({}) {} [Dataset] {}'.format(author_string, record.zenodo_submission_date.year, 
                                                   record.dataset_title, record.zenodo_doi)
    
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
    temp_extent.find('.//gml:beginPosition', nsmap).text = dataset_md['temporal_extent'][0]
    temp_extent.find('.//gml:endPosition', nsmap).text = dataset_md['temporal_extent'][1]
    
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
               "project website: ") + URL('projects', 'view_project', args=record.project_id, scheme=True)
    root.find(('gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/'
               'gmd:statement/gco:CharacterString'), nsmap).text = lineage
    
    # return the string contents
    return lxml.etree.tostring(tree)
    
    