import datetime
import dateutil.parser
import requests
from collections import Counter
from gluon.contrib import simplejson
from gluon.serializers import json
import os

## -----------------------------------------------------------------------------
## A collection of controllers handling mostly static information pages
## -----------------------------------------------------------------------------

def design():
    
    return response.render()

def requirements():
    
    return response.render()

def submitting_proposals():
    
    return response.render()

def logistics():
    
    # load costs from the json data
    f = os.path.join(request.folder, 'private','content/en/info/costs.json')
    costs = simplejson.load(open(f))
    
    return dict(costs=costs)

def data_policy():
    
    return response.render()

def health_and_safety():
    
    return response.render()

def steps_to_follow():
    
    return response.render()

def concept():
    
    return response.render()

def biosecurity():
    
    return response.render()

def funders():
    
    """
    Apart from Sime Darby at the top, the funder information is stored in a JSON
    file that provides rows of sets of funders. Each row contains a number of image/link pairs,
    and an overall row height. The code below packages them into bootstrap rows of DIVs with 
    centred, containing, non-repeating background images. 
    The number of links in a row should pack into the bootstrap 12 column grid!
    """
    
    
    # load funders from the json data
    f = os.path.join(request.folder, 'private','content/en/info/funders.json')
    content = simplejson.load(open(f))
    
    funders = []
    
    for r in content:
        
        row_class = 'img-responsive col-sm-' + str(12/len(r['links']))
        
        links = [A(DIV(_style='background-image:url(' +  URL('static', str(ln['image'])) + ');' + 
                              'background-size:contain;background-repeat: no-repeat;background-position:center;' +
                              'height:' + r['height'], _class=row_class),
                       _href=ln['url']) for ln in r['links']]
        funders.append(DIV(*links, _class='row', _style='margin:20px 0px;'))
    
    return dict(funders=funders)


def research_areas():
    
    """
    Loads an image and some blurb from a JSON file for each research area
    and looks up the number of projects associated with each area
    """
    
    
    # get the research areas of the most recent version of approved projects
    proj_query = db((db.project_id.project_details_id == db.project_details.id) &
                    (db.project_details.admin_status == 'Approved'))
    
    research_areas = proj_query.select(db.project_details.research_areas)
    
    ra_list = [r.research_areas for r in research_areas]
    ra_list = [item for sublist in ra_list for item in sublist]
    ra_table = Counter(ra_list)
    
    f = os.path.join(request.folder, 'private','content/en/info/research_areas.json')
    content = simplejson.load(open(f))
    
    content_formatted = []
    for k in content.keys():
        block = DIV(H3(k),
                    DIV(IMG(_src=URL('static', str(content[k]['image'])), 
                            _width=150, _align='left', 
                            _style='margin:0px 15px 15px 0px'),
                        _class="media-left"),
                    DIV(P(XML(content[k]['text'])),
                        P(B(ra_table[k], ' projects'), ' are currently tagged with this research area. See them ',
                          A('here', _href=URL('projects','projects', 
                            vars={'keywords':'project_details.research_areas contains "' + k + '"'}))),
                    _class="media-body"))
        
        content_formatted.append(block)
    
    return dict(content = content_formatted)


def gazeteer():
    
    # Set the fields available for searching
    sfields = [db.gazeteer.location, db.gazeteer.geom_type]
    
    # If the grid has set up some search keywords, then
    # use them to select those rows, otherwise get all rows
    if 'keywords' in request.get_vars:
        qry = SQLFORM.build_query(sfields, keywords=request.vars.keywords)
    else:
        qry = db.gazeteer
    
    # get the (selected) rows and turn them into geojson
    rws = db(qry).select()
    rws = [{"type": "Feature", "properties": r.properties, 
            "geometry": {"type": r.geom_type,"coordinates": r.geom_coords}}
            for r in rws]
    
    form = SQLFORM.grid(db.gazeteer, fields=sfields,
                        csv=False,
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False)
    
    search_form = form.element('.web2py_console')[1]
    
    return dict(form=form, sitedata=json(rws), search_form=search_form)


# def calendars():
#
#     return response.render()

def mailing_list():
    
    return response.render()

def newsletter():
    
    # query the mailchimp archive and get a list of links
    r = requests.get('https://us6.api.mailchimp.com/3.0/campaigns', auth=('apikey','c028335ab2baec6ee9710ed466cd9146-us6'), params={'count': 100})
    data =  r.json()['campaigns']
    
    table = [ [r['archive_url'], r['settings']['title'], dateutil.parser.parse(r['create_time'])] for r in data if r['status'] == 'sent']
    
    # sort by date going back
    table.sort(key = lambda r: r[2], reverse=True)
    
    return dict(table=table)

@auth.requires_membership('admin')
def public_holidays():
    
    
    form = SQLFORM.grid(query=(db.public_holidays), csv=False,
                         maxtextlength=250,
                         deletable=True,
                         editable=True,
                         create=True,
                         details=False)
    
    return dict(form=form)
