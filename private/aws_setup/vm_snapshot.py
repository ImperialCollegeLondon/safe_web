#!/usr/bin/env python
import boto3
import datetime

# connect to EC2
ec2 = boto3.client('ec2')

# Look for the web server instance
instances = ec2.describe_instances(
    Filters=[
        {'Name': 'tag:Name', 'Values': ['SAFE Webserver']},
    ]
)

# check we found one volume
if len(instances['Reservations'][0]['Instances']) <> 1:
    raise Exception('Unique instance not recovered')
else:
    print "Found SAFE Webserver to backup"


# need to find the volume ID for the root device
inst = instances['Reservations'][0]['Instances'][0]
root =  inst['RootDeviceName']
devices = inst['BlockDeviceMappings']

volume_id = ''
for dev in devices:
    if dev['DeviceName'] == root:
        volume_id = dev['Ebs']['VolumeId']

if volume_id == '':
    raise Exception('Root volume not identified')

## Create the new snapshot and tag it
description_string = "Backup of root volume for SAFE Webserver taken {}".format(datetime.date.today().isoformat())

snapshot = ec2.create_snapshot(
    VolumeId=volume_id,
    Description = description_string
)

if snapshot['State'] == 'error':
    print "Problem creating snapshot"
else:
    tag = ec2.create_tags(
        Resources=[snapshot['SnapshotId']], 
        Tags = [{"Key":'Name', 
                 "Value":'SAFE Webserver backup'}]
    )
    print "Snapshot {} created with description: {}".format(snapshot['SnapshotId'], snapshot['Description'])

