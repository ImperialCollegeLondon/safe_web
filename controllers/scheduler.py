import datetime

"""
This controller, which has no view so falls back to the generic layout
is simply a way to have a web accessible programmatic way to set up a
defined set of scheduled tasks and then monitor them.
"""

@auth.requires_membership('admin')
def check_task_queue():
    
    
    # get some summary queries
    # - select t.task_name, t.times_run, t.times_failed, t.next_run_time from scheduler_task t;
    active_tasks = db().select(db.scheduler_task.task_name,
                               db.scheduler_task.start_time,
                               db.scheduler_task.times_run,
                               db.scheduler_task.times_failed,
                               db.scheduler_task.next_run_time)
    
    # make it into a pretty table
    active_tasks = TABLE(TR(TH("Task name"), TH("Started"), TH('Times run'), 
                            TH("Times failed"), TH('Next run')),
                         *[TR(r.task_name, r.start_time, r.times_run,
                              r.times_failed, r.next_run_time) for r in active_tasks],
                         _class='table table-striped')
    
    # - select t.task_name, r.status, max(r.stop_time) as most_recent 
    #       from scheduler_task t 
    #           left join scheduler_run r 
    #           on (t.id = r.task_id) 
    #       ////// where r.status is not null 
    #       group by t.task_name, r.status 
    run_status = db().select(db.scheduler_task.task_name,
                             db.scheduler_run.status,
                             db.scheduler_run.stop_time.max().with_alias('most_recent'),
                             left=[db.scheduler_run.on(db.scheduler_run.task_id == db.scheduler_task.id)], 
                             groupby=[db.scheduler_task.task_name,
                                      db.scheduler_run.status])
    
    # make it into a pretty table
    run_status = TABLE(TR(TH("Task name"), TH("Status"), TH('Most recent status occurence')),
                         *[TR(r.scheduler_task.task_name, 
                              r.scheduler_run.status, 
                              r.most_recent) for r in run_status],
                         _class='table table-striped')
    
    # Schedule tasks - look to see if each task name exists in the scheduler table
    # and set it up if not
    
    tasks_checker = []
    
    # list of tasks and queue parameters
    
    def setStart(day, time): 
        
        """
        Function to get a datetime for a given time on the next specific day of 
        the week (Monday=1)
        """
        
        today = datetime.date.today() 
        date = today + datetime.timedelta(days=(day-today.isoweekday()+7)%7)
        dtime = datetime.datetime.combine(date, time)
        return dtime
    
    task_dict = [{'name':'remind_about_unknowns', 'period': 60*60*24, 
                  'start_time': datetime.datetime.now()},
                 {'name':'update_deputy_coordinator', 'period': 60*60*24*7,
                  'start_time': setStart(1, datetime.time(01,00,00))}]
    
    # loop over the tasks
    # - there is a hack in here - start_time should set the first run time
    #   but isn't being respected on the test system on a mac, so I've put
    #   the explicit next run time too.
    for tsk in task_dict:
    
        check_exists = db(db.scheduler_task.task_name == tsk['name']).count()
        if check_exists == 0:
            scheduler.queue_task(tsk['name'],
                                 start_time=tsk['start_time'],
                                 next_run_time=tsk['start_time'],
                                 period=tsk['period'],
                                 prevent_drift=True,
                                 repeats=0)
            tasks_checker.append(TR(TD(B(tsk['name'])), TD(B('Task not found and was recreated', _style='color:red'))))
        else:
            tasks_checker.append(TR(TD(B(tsk['name'])), TD(B('Task found', _style='color:green'))))
    
    tasks_checker = TABLE(TR(TH("Task name"), TH("Task queue status")),
                         *tasks_checker,
                         _class='table table-striped')
    
    return dict(active_tasks=active_tasks, run_status=run_status, tasks_checker=tasks_checker)