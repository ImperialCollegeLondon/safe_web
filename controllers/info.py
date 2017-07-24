import datetime
import dateutil.parser
import requests
from collections import Counter
from gluon.contrib import simplejson
from gluon.serializers import json
import os
from gpxpy import gpx

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


def gazetteer():
    
    """
    Controller to provide a map view of the gazetteer data and a searchable
    interface with GPX download.
    """
    
    # If the grid has set up some search keywords, and the keywords aren't an empty 
    # string then use them to select those rows, otherwise get all rows
    sfields = [db.gazetteer.location, db.gazetteer.type, db.gazetteer.plot_size, 
               db.gazetteer.fractal_order, db.gazetteer.transect_order]
    
    if 'keywords' in request.get_vars and request.vars.keywords != '':
        qry = SQLFORM.build_query(sfields, keywords=request.vars.keywords)
    else:
        qry = db.gazetteer
    
    # get the (selected) rows and turn them into geojson, ordering them
    # so that the bottom ones get added to the leaflet map first
    rws = db(qry).select(orderby=db.gazetteer.display_order)
    
    # Need to put together the tooltip for the gazetteer
    # using a subset of the available columns
    loc = ['<B>' + rw['location'] + '</B></BR>' for rw in rws]
    info = [[key + ': ' + str(rw[key]) for key in ['type','plot_size','parent','fractal_order','transect_order']
             if rw[key] is not None] for rw in rws]
    
    # combine, removing trailing break
    tooltips = [l + '</BR>'.join(i) for l, i in zip(loc, info)]
    
    rws = [{"type": "Feature", "tooltip": tl, 
            "geometry": {"type": r.geom_type,"coordinates": r.geom_coords}}
            for r, tl in zip(rws, tooltips)]
    
    # provide GPX and GeoJSON downloaders and use the magic 
    # 'with_hidden_cols' suffix to allow the Exporter to access
    # fields that aren't shown in the table
    export = dict(gpx_with_hidden_cols=(ExporterGPX, 'GPX'), 
                  geojson_with_hidden_cols=(ExporterGeoJSON, 'GeoJson'), 
                  csv_with_hidden_cols=False,
                  csv=False, xml=False, html=False, json=False,
                  tsv_with_hidden_cols=False, tsv=False)
    
    form = SQLFORM.grid(db.gazetteer,
                        fields=sfields,
                        csv=True,
                        exportclasses=export,
                        maxtextlength=250,
                        deletable=False,
                        editable=False,
                        create=False,
                        details=False)
    
    # format the HTML to move the export button into the search console
    # get a button themed link
    exp_menu = form.element('.w2p_export_menu')
    exp_gpx = A("Export GPX", _class="btn btn-default",
                _href=exp_menu[2].attributes['_href'],
                _style='padding:6px 12px;line-height:20px')
    exp_geojson = A("Export GeoJSON", _class="btn btn-default",
                    _href=exp_menu[1].attributes['_href'],
                    _style='padding:6px 12px;line-height:20px')
    console = form.element('.web2py_console form')
    console.insert(len(console), CAT(exp_gpx, exp_geojson))
    
    # get the existing export menu index (a DIV within FORM) and delete it
    export_menu_idx = [x.attributes['_class'] for x in form].index('w2p_export_menu')
    del form[export_menu_idx]
    
    return dict(form=form, sitedata=json(rws))


class ExporterGPX(object):
    
    """
    Used to export a GPX file of the selected rows in SQLFORM grid
    """
    
    file_ext = "gpx"
    content_type = "text/xml"

    def __init__(self, rows):
        self.rows = rows

    def export(self):
        if self.rows:
            # create a new gpx file
            gpx_data = gpx.GPX()
            
            # exclude rows with no centroid data (polylines at present)
            to_gpx = (rw for rw in self.rows if rw.centroid_x is not None)
            
            # add the centroids into the file
            for pt in to_gpx:
                gpx_data.waypoints.append(gpx.GPXWaypoint(name=pt.location, longitude=pt.centroid_x, latitude=pt.centroid_y))
            
            return gpx_data.to_xml()
        else:
            return ''


class ExporterGeoJSON(object):
    
    """
    Used to export a GPX file of the selected rows in SQLFORM grid
    """
    
    file_ext = "geojson"
    content_type = "application/vnd.geo+json"

    def __init__(self, rows):
        self.rows = rows

    def export(self):
        if self.rows:
            
            # get a list of dictionaries of the values
            ft_as_dicts = self.rows.as_dict().values()
            
            # pop out the geometry components and id
            id_number = [ft.pop('id') for ft in ft_as_dicts]
            geom_type = [ft.pop('geom_type') for ft in ft_as_dicts]
            geom_coords = [ft.pop('geom_coords') for ft in ft_as_dicts]
            
            # assemble the features list
            features = [{'type': "Feature", 'id': idn, 'properties': prop,
                         'geometry': {'type': tp, 'coordinates': crds}} for 
                         (idn, prop, tp, crds) in zip(id_number, ft_as_dicts, geom_type, geom_coords)]
            
            # embed that in the Feature collection
            feature_collection = {"type": "FeatureCollection",
                                  "crs": {"type": "name",
                                          "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
                                  "features": features}
            
            return simplejson.dumps(feature_collection)
        else:
            return ''
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
