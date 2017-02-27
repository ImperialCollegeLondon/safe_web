import datetime

"""
This model contains code for scheduled tasks on the 
SAFE website DB. At present these are:

Weekly:
-  Email the deputy coordinator with the current research visit schedule

Daily:
-  Look for research visits with Unknowns that are within a week of the
   research visit start date and email them a reminder to update
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
                                    args=[offence.research_visit.id], scheme=True, host=True)}
        # email this offender
        SAFEmailer(subject='SAFE Research Visit details',
                   to=offence.auth_user.email,
                   template='research_visit_details_reminder.html',
                   template_dict=template_dict)
    
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
                   to= 'd.orme@imperial.ac.uk',
                   template='weekly_rv_summary.html',
                   template_dict=dict(),
                   attachment_string_objects=attach)
        
        return 'Weekly research visit summary emailed'
    except:
        return 'Failed to email weekly research visit summary'

# Load the scheduler and set the task names, setting a slow 1 hour heartbeat.
# As the current tasks are daily activities at most, there is no need for
# the scheduler to do frenetic checks every 3 seconds, which is the default

from gluon.scheduler import Scheduler
scheduler = Scheduler(db, 
                      tasks=dict(remind_about_unknowns=remind_about_unknowns,
                                 update_deputy_coordinator=update_deputy_coordinator),
                      heartbeat=5*60)

# These tasks then need to be queued using scheduler.queue_task or manually via 
# the appadmin interface. Don't do it here as they'll be queued every time the 
# model runs, which is basically every time a webpage is loaded! So, 
# programatically, they can go in a controller which an admin can run once to 
# get a defined set of queues going.
