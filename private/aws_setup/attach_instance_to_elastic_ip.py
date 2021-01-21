#!/usr/bin/env python

import boto3

# connect to EC2 resources
ec2 = boto3.resource('ec2')

# Look for the webserver instance
instances_filt = ec2.instances.filter(
    Filters = [{'Name':'tag-value','Values':['SAFE Webserver']}]
)

# check we've got a single result
webserver_id = [x.id for x in instances_filt]
if len(webserver_id) <> 1:
   raise  Exception('Unique webserver ID not recovered')

# connect to EC2 client
client = boto3.client('ec2')

# #could create an elastic IP programatically using:
# elastic_ip = client.allocate_address()
# # This would then need to be associated with the DNS record for safeproject.net

addresses = client.describe_addresses()
if len(addresses['Addresses']) <> 1:
   raise  Exception('Unique Elastic IP not recovered')

# associate this instance with the Elastic IP
associate = client.associate_address(
    InstanceId=webserver_id[0],
    PublicIp=addresses['Addresses'][0]['PublicIp']
)
