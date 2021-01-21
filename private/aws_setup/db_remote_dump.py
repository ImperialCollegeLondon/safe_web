#!/usr/bin/env python
import datetime
from subprocess import Popen, PIPE
import os

# get the current set of dumps
dumpdir='/home/www-data/safe_web2py_psql_dump'
existing_dumps = os.listdir(dumpdir)

print "Backing up PG database to {}".format(dumpdir)
# Is there an existing snapshot for this day of the week?
today = datetime.date.today()
weekday = today.isoweekday()

# get the weekday of the dump, expecting the format
# "safe_web2py-1900-01-01-day-1.dump"
file_day = [os.path.splitext(x)[0][-1] for x in existing_dumps]

for d, f in zip(file_day, existing_dumps):
    
    if int(d) == weekday:
        os.remove(os.path.join(dumpdir, f))
        print("Removed expired backup: {}".format(f))


# define the command to run the dump of the remote database,
# requiring the user to have a .pgpass file to authenticate
dumpfile =  'safe_web2py-{}-day-{}.dump'.format(today.isoformat(), weekday)
command = ['/usr/bin/pg_dump', 
           '-d', 'safe_web2py', 
           '-h', 'earthcape-pg.cx94g3kqgken.eu-west-1.rds.amazonaws.com',
           '-U','safe_admin', 
           '-f', os.path.join(dumpdir, dumpfile)]

# Run the command
process = Popen(command, stdout=PIPE, stderr=PIPE)
output, err = process.communicate()
process.wait()

# logging
if process.returncode <> 0:
    print 'Error in pg_dump:' + ''.join(err)
else:
    print 'Fresh pg_dump completed successfully to: {}'.format(dumpfile)
