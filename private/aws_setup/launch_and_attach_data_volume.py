#!/usr/bin/env python

import boto3

# connect to EC2
ec2 = boto3.resource('ec2')

# Look for an instance tagged as 'SAFE Webserver' 
# (could create this programatically)
instances_filt = ec2.instances.filter(
    Filters = [{'Name':'tag-value','Values':['SAFE Webserver']}]
)

# check we've got a single result
webserver_id = [x.id for x in instances_filt]
if len(webserver_id) <> 1:
   raise  Exception('Unique webserver ID not recovered')

# create the new volume as a 20GB GP SSD Volume
volume = ec2.create_volume(
    Size=20,
    AvailabilityZone='eu-west-1a',
    VolumeType='gp2',
)

# Tag it with a name for clarity
tag_volume = ec2.create_tags(
    Resources = [volume.id],
    Tags = [{'Key':'Name', 'Value':'SAFE Web data'}]
)

# Attach the volume to the webserver instance
attach_volume = volume.attach_to_instance(
    InstanceId=webserver_id[0], 
    Device='/dev/xvdb'
)

