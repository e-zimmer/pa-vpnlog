#!/usr/bin/env python3
from argparse import ArgumentParser
import csv
from datetime import datetime, timedelta
import logging
import os
from py_dotenv import read_dotenv
import re
import requests
import time
import urllib3
urllib3.disable_warnings()
import xml.etree.ElementTree as ET

envfile = os.path.join('./.paenv')
read_dotenv(envfile)
api_key = os.getenv('API_KEY')
server = os.getenv('SERVER')
tstamp = datetime.now()
newfile = f"PAVPN-log-{tstamp}.csv"
qdate = (tstamp - timedelta(days=7)).strftime("%Y/%m/%d")
query_time = f"receive_time geq '{qdate} 08:00:00'"


def get_system_log(server=server, api_key=api_key):
    payload = {
        'type': 'log',
        'log-type': 'system',
        'query': f'( subtype eq globalprotect ) and ( eventid eq globalprotectgateway-config-succ ) or ( eventid eq globalprotectgateway-config-release ) and ( {query_time} )',
        'nlogs': '5000'
    }
    headers = {
        'X-PAN-KEY': api_key
    }
    URL = f"https://{server}/api"
    r = requests.get(URL, params=payload, headers=headers, verify=False)
    logging.debug(f"Got URL: {r.url}")
    return r

def parse_jobId(result):
    #logging.info(f"Getting job ID: {result}")
    root = ET.fromstring(result)
    for result in root.findall("result"):
        jobId = result.find('job').text
        logging.info(f"Got jobId: {jobId}")
    return jobId

def get_job(jobId, server=server, api_key=api_key, counter=0, skip=None):
    logging.debug(f"Getting job output: {jobId}")
    payload = {
        'type': 'log',
        'action': 'get',
        'skip': skip,
        'job-id': jobId
    }
    headers = {
        'X-PAN-KEY': api_key
    }
    URL = f"https://{server}/api"
    r = requests.get(URL, params=payload, headers=headers, verify=False)
    logging.debug(f"Got result: {r}")
    status, max_count, count = job_status(r.text)
    logging.debug(f"Job status: {status}")
    logging.debug(f"Max count: {max_count} Type: {type(max_count)}")
    logging.debug(f"Count: {count} Type: {type(count)}")
    logging.debug(f"Counter: {counter} Type: {type(counter)}")
    if status != 'FIN':
        get_job(jobId)
    elif counter != max_count:
        logging.debug("No match")
        parse_xml(r.text)
        get_job(jobId, skip=count, counter=counter + count)
    else:
        print(f"Completed export {max_count} records")

def job_status(result):
    #logging.info(f"Getting job status: {result}")
    root = ET.fromstring(result)
    for i in root.iter(tag='job'):
        max_count = int(i.find('cached-logs').text)
    for j in root.iter(tag='log'):
        count = int(j.find('logs').attrib['count'])
    if root.attrib['status'] == "success":
        for response in root.iter("status"):
            status = response.text
    return status, max_count, count

def delete_job(jobId, server=server, api_key=api_key):
    logging.info(f"Deleting job: {jobId}")
    payload = {
        'type': 'log',
        'action': 'finish',
        'job-id': jobId
    }
    headers = {
        'X-PAN-KEY': api_key
    }
    URL = f"https://{server}/api"
    r = requests.get(URL, params=payload, headers=headers, verify=False)
    logging.debug(f"Deleted: {r.text}")
    return r

def read_file(path):
    with open(path) as file:
        csvreader = csv.reader(file)
        for line in csvreader:
            #print(line)
            #date = line[1]
            client_info = parse_line(line)
            write_file(client_info)

def write_file(line):
    with open(newfile, 'a') as nf:
        csvwriter = csv.writer(nf)
        csvwriter.writerow(line)

def parse_xml(result):
    #client = ["Time", "User Name", "Status", "IP address", "Client Version", "Device Name", "OS Version", "PA Device"]
    #write_file(client)
    nroot = ET.fromstring(result)
    for e in nroot.iter(tag='entry'):
        r_time = [e.find('receive_time').text]
        client_info = parse_line(e.find('opaque').text)
        dev_name = [e.find('device_name').text]
        client_info = (r_time + client_info + dev_name)
        write_file(client_info)

def parse_line(line):
    client = []
    if "succ" in line[8]:
        status = "start"
    else:
        status = "stop"
    user = re.search('(?<=User name: )\w*', line)
    ipaddr = re.search('(?<=Private IP: )(?:.*?\,)', line)
    cli_ver = re.search('(?<=Client version: )(?:.*?,)', line)
    dev_name = re.search('(?<=Device name: )(?:.*?,)', line)
    os_ver = re.search('(?<=Client OS version: )(?:.*?VPN)', line)
    client = [
              user.group(0),
              status,
              ipaddr.group(0)[:-1],
              cli_ver.group(0)[:-1],
              dev_name.group(0)[:-1],
              os_ver.group(0)[:-5]
              ]
    return client


if __name__ == "__main__":
    logging.basicConfig(format = '%(asctime)s - %(levelname)s - %(message)s')
    parser = ArgumentParser(description='Select options.')
    required = parser.add_argument_group('required arguments')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="verbose")
    parser.add_argument('-d', '--debug', action='store_true',
                        help="debug")

    #parser.add_argument('-f', metavar='file', type=str,
    #                    help="File to import")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    #read_file(args.infile)
    result = get_system_log()
    if result.status_code == requests.codes.ok:
        jobId = parse_jobId(result.text)
        get_job(jobId)
        delete_job(jobId)
    else:
        print(f"Failure: {result}")
