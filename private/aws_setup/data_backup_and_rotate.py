#!/usr/bin/env python

import boto3
import datetime

# connect to EC2
ec2 = boto3.client('ec2')

# Look for the web data volume
volumes = ec2.describe_volumes(
    Filters=[
        {'Name': 'tag:Name', 'Values': ['SAFE Web data']},
    ]
)

# check we found one volume
if len(volumes['Volumes']) <> 1:
    raise Exception('Unique data volume not recovered')
else:
    print "Found SAFE Web data volume to backup"
    volume_to_backup = volumes['Volumes'][0]

# Look for existing snapshots - snapshots all have the Name tag with
# value 'SAFE_Data_backup' and then a description string giving the day
# in the format "Seven day backup for SAFE Data volume taken 1900-01-01: Day 1"

snapshots = ec2.describe_snapshots(
    Filters=[
        {'Name': 'tag:Name', 'Values': ['SAFE_Data_backup']},
    ]
)

# Is there an existing snapshot for this day of the week?
today = datetime.date.today()
weekday = today.isoweekday()

for snap in  snapshots['Snapshots']:
    
    # get the last character
    snapshot_day = int(snap['Description'][-1])
    
    # if the snapshot is for this day of the week, delete it
    if weekday == snapshot_day:
        print 'Deleting expired snapshot {} with description: {}'.format(snap['SnapshotId'], snap['Description'] )
        delete = ec2.delete_snapshot(SnapshotId=snap['SnapshotId'])

## Create the new snapshot
description_string = "Seven day backup for SAFE Data volume taken {}: Day {}".format(today.isoformat(), weekday)

snapshot = ec2.create_snapshot(
    VolumeId=volume_to_backup['VolumeId'],
    Description = description_string
)

if snapshot['State'] == 'error':
    print "Problem creating snapshot"
else:
    tag = ec2.create_tags(
        Resources=[snapshot['SnapshotId']], 
        Tags = [{"Key":'Name', 
                 "Value":'SAFE_Data_backup'}]
    )
    print "Snapshot {} created with description: {}".format(snapshot['SnapshotId'], snapshot['Description'])

