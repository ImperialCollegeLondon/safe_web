from gluon.scheduler import Scheduler
from safe_web_datasets import verify_dataset
from safe_web_scheduler import remind_about_unknowns, send_weekly_summary, outdated_health_and_safety

# The scheduler is loaded and defined in a model, so that it can register the
# required tables with the database. The functions are defined in separate modules.


# Load the scheduler and set the task names. With only daily tasks, a slower
# heartbeat is fine, but with dataset checking, a snappier response is needed,
# so the default 3 second heartbeat is used. Note that individual queue tasks
# can set immediate=TRUE to get prompter running of a task, but that still might
# wait for one or two heartbeats to actually run.

scheduler = Scheduler(db,
                      tasks=dict(remind_about_unknowns=remind_about_unknowns,
                                 send_weekly_summary=send_weekly_summary,
                                 verify_dataset=verify_dataset,
                                 outdated_health_and_safety=outdated_health_and_safety))

# These tasks then need to be queued using scheduler.queue_task or manually via
# the appadmin interface. Don't do it here as they'll be queued every time the
# model runs, which is basically every time a webpage is loaded! So,
# programatically, they can go in a controller which an admin can run once to
# get a defined set of queues going.
