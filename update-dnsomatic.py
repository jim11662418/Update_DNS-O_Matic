#!/usr/bin/env python


# The last public IP address is read from a configuration file and compared to the public
# IP address retrieved from the web. If the two addresses disagree, DNS-O-Matic is updated
# using an HTTP Request.

# This Python script runs as a cron job at 15 minutes past each hour...

import datetime
import time
from base64 import encodestring
from urllib import urlencode
from urllib2 import Request,urlopen
import logging
import sys
from configparser import ConfigParser
import os
import __main__ as main
from requests import get
import re
import random

# for testing purposes, '-t' or '/t' on the command line forces an IP address update
testing = False
for i in range (1,len(sys.argv)):
   if ((sys.argv[i] == "-t") or (sys.argv[i] == '/t')):
       testing = True

logging.basicConfig(filename=os.path.splitext(main.__file__)[0]+'.log',filemode='a',format='%(asctime)s %(message)s',datefmt='%m/%d/%Y %H:%M:%S',level=logging.INFO)
logging.getLogger('urllib2').setLevel(logging.CRITICAL)

print '\nDNS-O-Matic.com updater is running...\n'
#logging.info('DNS-O-Matic updater is running.')

inifilename=os.path.splitext(main.__file__)[0]+'.ini'       # update-dnsomatic.ini
config=ConfigParser()

# read the configuration file...
# if the configuration file doesn't exist or can't be read, log the error and exit the program
try:
   config.read(inifilename)
except:
   print 'Unable to open configuration file.'
   logging.info('Unable to open configuration file.')
   sys.exit()

# get the IP address stored in the configuration file...
# if the IP address can't be read, log the error and use a dummy address that will force an update
try:   
   lookup=config.get('public','ipaddress')
   print 'The stored IP address from the configuration file is:', lookup
except:
   print 'Unable to read stored IP address from configuration file.'
   logging.info('Unable to read last IP address from configuration file.')
   lookup = '222.222.222'    

# get the urls of the IP address services stored in the configuration file...
# if the urls can't be read, log the error and exit the program
try:
  services=config.items('services')
except:
   print 'Unable to read services section of configuration file.'
   logging.info('Unable to read services section of configuration file.')
   sys.exit()  

myip=str()
maxAttempts=len(services)                               # large enough number to try all the services, maybe
attempts=1           

# Try to get (up to 'maxAttempts' times) the current public IP Address from the web.
while (myip==''):
   ipCheckService = services[random.randint(0,len(services)-1)][1] # select a service at random
   print 'Attempt '+str(attempts)+'. Connecting to '+ipCheckService
   try:
      line = get(ipCheckService,timeout=5).text
   except:
      logging.info('Unable to connect to '+ipCheckService)
      print 'Unable to connect to '+ipCheckService
      attempts=attempts+1
      time.sleep(2)                                     # pause 2 seconds between attempts
   else:
      addresses = re.findall(r'[0-9]+(?:\.[0-9]+){3}',line)
      if addresses:
         myip = addresses[0]
         #logging.info('Attempt '+str(attempts)+'. The current public IP address from '+ipCheckService+' is '+myip)
         print 'The current public IP address from '+ipCheckService+' is:', myip
      else:
         print 'Unable to get current public IP address from '+ipCheckService
         #logging.info('Attempt '+str(attempts)+'. Unable to get current public IP address from '+ipCheckService
         attempts=attempts+1
         if (attempts > maxAttempts):
            print 'Unable to get current public IP address after '+str(maxAttempts)+' attempts. Exiting.'
            logging.info('Unable to get current public IP address after '+str(maxAttempts)+' attempts.')
            exit()
         else:
            time.sleep(2)

# DNS-O-Matic username and password...
username='------------.com'
password='------------'

# if testing OR if the IPs addresses don't match OR if it is now 3:15AM, then update IP addresses...
if (testing) or ((lookup != myip) or (datetime.datetime.now().hour == 3)):
    #change the DNS entry
    data = {}
    data['hostname'] = 'all.dnsomatic.com'
    data['myip'] = myip
    data['wildcard'] = 'NOCHG'
    data['mx'] = 'NOCHG'
    data['backmx'] = 'NOCHG'

    url_values = urlencode(data)
    url = 'https://updates.dnsomatic.com:443/nic/update?' + url_values
    request = Request(url)

    base64string = encodestring(username + ':' + password)[:-1]
    request.add_header('Authorization', 'Basic %s' % base64string)
    request.add_header('User-Agent',username + ' - Home User - 1.0')

    try:
      htmlFile = urlopen(request)
    except:
      logging.info('Unable to connect to DNS-O-Matic update service')
      print 'Unable to connect to DNS-O-Matic update service. Exiting.'
      exit()
    else:
      htmlData = htmlFile.read()
      htmlFile.close()

      results = htmlData.split()
      if results[0] == 'good':
        logging.info('DNS-O-Matic updated to: ' + results[1])
        print 'DNS-O-Matic updated to: ' + results[1]
      else:
        logging.info('DNS-O-Matic update failed with error: ' + results[0])
        print 'DNS-O-Matic update failed with error: ', results[0]
else:
    logging.info('IP addresses match. No DNS update necessary.')
    print 'The stored and current IP addresses match. No DNS update necessary.'

# update the configuration file with the current public IP Address
# if the configuration file doesn't exist, create a new one
try:
   config.set('public','ipaddress',myip)
except:
   config.add_section('public')
   config.set('public','ipaddress',myip)
finally:
   with open(inifilename,'w') as f:
      config.write(f)
