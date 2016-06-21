
import datetime
import dateutil.parser
import requests
from collections import Counter
from gluon.contrib import simplejson
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
    
    return response.render()

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
    
    return response.render()

def ecological_monitoring():
    
    return response.render()

def research_areas():
    
    proj_query = db(db.project_id.project_details_id == db.project_details.id)
    research_areas = proj_query.select(db.project_details.research_areas)
    
    ra_list = [r.research_areas for r in research_areas]
    ra_list = [item for sublist in ra_list for item in sublist]
    ra_table = Counter(ra_list)
    
    f = os.path.join(request.folder, 'private','content/en/info/research_areas.json')
    content = simplejson.load(open(f))
    
    content_formatted = []
    for k in content.keys():
        block = DIV(H3(k),
                    IMG(_src=URL('static', str(content[k]['image'])), 
                        _width=150, _align='left', 
                        _style='margin:0px 15px 15px 0px'),
                    P(content[k]['text']),
                    P(B(ra_table[k], ' projects'), ' are currently tagged with this research area. See them ',
                      A('here', _href=URL('projects','projects', 
                        vars={'keywords':'project_details.research_areas contains "' + k + '"'}))))
        
        content_formatted.append(block)
    
    return dict(content = content_formatted)



def calendars():
    
    return response.render()

def mailing_list():
    
    return response.render()

def newsletter():
    
    # query the mailchimp archive and get a list of links
    r = requests.get('https://us6.api.mailchimp.com/3.0/campaigns', auth=('apikey','c028335ab2baec6ee9710ed466cd9146-us6'), params={'count': 100})
    data =  r.json()['campaigns']
    
    table = [ [r['archive_url'], r['settings']['title'], dateutil.parser.parse(r['create_time'])] for r in data]
    
    # sort by date going back
    table.sort(key = lambda r: r[2], reverse=True)
    
    return dict(table=table)