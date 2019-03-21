import datetime
from safe_web_global_functions import (safe_mailer, all_rv_summary_text, 
                                       get_frm, health_and_safety_report)

"""
The web2py HTML helpers are provided by gluon. This also provides the 'current' object, which
provides the web2py 'request' API (note the single letter difference from the requests package!).
The 'current' object is also extended by models/db.py to include the current 'db' DAL object
and the 'myconf' AppConfig object so that they can accessed by this module
"""

from gluon import *


"""
This module contains code for scheduled tasks on the 
SAFE website DB. At present these are:

Weekly:
-  Email the deputy coordinator with the current research visit schedule

Daily:
-  Look for research visits with Unknowns that are within a week of the
   research visit start date and email them a reminder to update
-  Look for research visits within two weeks and email visitors with
   an outdated or missing health and safety form.

As needed:
- Verify the formatting of an uploaded dataset.
"""


def remind_about_unknowns():
    
    """
    Daily emails to research visit proposers who haven't
    completed the visitor details for visits that start 
    within the next week.
    """

    db = current.db

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
               (db.research_visit_member.user_id is None))
    
    offenders = query.select(db.auth_user.first_name,
                             db.auth_user.email,
                             db.research_visit.title,
                             db.research_visit.id,
                             db.research_visit_member.id.count().with_alias('count'),
                             groupby=[db.auth_user.first_name, db.auth_user.email,
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
        safe_mailer(subject='SAFE Research Visit details',
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

    db = current.db
    
    frm = get_frm()
    frm = [eml for eml in [frm.alternative_email, frm.email] if eml is not None]
    
    send_to = ['deputy.coord@safeproject.net'] + frm
    
    # get the file contents
    try:
        now = datetime.date.today().isoformat()
        attach = {'SAFE_visits_{}.txt'.format(now): all_rv_summary_text(),
                  'Visitor_H_and_S_info_{}.pdf'.format(now): health_and_safety_report()}
        
        
        safe_mailer(subject='Weekly research visit summary',
                    to=send_to,
                    template='weekly_rv_summary.html',
                    template_dict=dict(),
                    attachment_string_objects=attach)
        
        # commit changes to the db - necessary for things running from models
        db.commit()
        
        return 'Weekly research visit summary emailed'
    except BaseException:
        raise RuntimeError('Failed to email weekly research visit summary')


def outdated_health_and_safety():
    
    """
    Daily emails to upcoming research visitors who haven't created their health
    and safety at all or haven't visited that link in more than 6 months
    """

    db = current.db

    # Get some timestamps
    now = datetime.datetime.now()
    old_hs = (now - datetime.timedelta(days=180)).date()
    
    # Find people with bed reservations at SAFE or Maliau who have old or missing H&S
    # There may be a way of combining these two but it seems likely to be slower
    safe_off = db((db.bed_reservations_safe.arrival_date - now <=  14) &
                  (db.bed_reservations_safe.departure_date >= now) &
                  (db.bed_reservations_safe.research_visit_member_id == db.research_visit_member.id) &
                  (db.research_visit_member.user_id == db.auth_user.id) &
                  ((db.health_and_safety.id == None) |
                   (db.health_and_safety.date_last_edited < old_hs))
                  ).select(db.auth_user.ALL, 
                           db.health_and_safety.ALL, 
                           left=db.health_and_safety.on(db.auth_user.id == db.health_and_safety.user_id),
                           distinct=True,
                           orderby=(db.auth_user.last_name, db.auth_user.first_name))

    mali_off = db((db.bed_reservations_maliau.arrival_date - now <=  14) &
                  (db.bed_reservations_maliau.departure_date >= now) &
                  (db.bed_reservations_maliau.research_visit_member_id == db.research_visit_member.id) &
                  (db.research_visit_member.user_id == db.auth_user.id) &
                  ((db.health_and_safety.id == None) |
                   (db.health_and_safety.date_last_edited < old_hs))
                  ).select(db.auth_user.ALL, 
                           db.health_and_safety.ALL, 
                           left=db.health_and_safety.on(db.auth_user.id == db.health_and_safety.user_id),
                           distinct=True,
                           orderby=(db.auth_user.last_name, db.auth_user.first_name))
    
    offenders = safe_off + mali_off
    
    # now email each offender
    for offence in offenders:
        
        # dictionary to fill out the template
        template_dict = {'name': offence.auth_user.first_name}
        
        # email this offender
        safe_mailer(subject='SAFE Research Visit health and safety information',
                    to=offence.auth_user.email,
                    template='research_visit_health_and_safety.html',
                    template_dict=template_dict)
        
        # commit changes to the db - necessary for things running from models
        db.commit()
    
    if len(offenders) > 0:
        offender_names = ', '.join(['{first_name} {last_name}'.format(**rw.auth_user) 
                                    for rw in offenders])
        return 'Emailed {} researchers with outdated or missing H&S info: {}'.format(len(offenders), offender_names)
    else: 
        return 'All H&S up to date'
