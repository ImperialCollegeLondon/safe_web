
import datetime
import dateutil.parser
import requests


## -----------------------------------------------------------------------------
## A collection of controllers handling mostly static information pages
## -----------------------------------------------------------------------------

def design():
    
    return response.render()

def requirements():
    
    return response.render()

def submitting_proposals():
    
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