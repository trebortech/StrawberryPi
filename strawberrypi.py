#! /usr/bin/python


# system libs
import sys
import os
import time
from datetime import datetime
import httplib2

# google cal api libs
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

# RaspberryPI libs
import RPi.GPIO as gpio

# Global vars

mapZonePin = {}
boardPins = (10, 11, 12, 13)
pidfilepath = '/var/run/strawberrypi.pid'
credential_path = '.credentials/calendar.json'
calendarid = 'trebortech.com_rq51u47mudg677gk9uc6gsd8kc@group.calendar.google.com'
datefmt = '%Y-%m-%dT%H:%M:%S'
zoneinterval = 5


# Initialize Board

def initBoard():

    # Set board mode
    # MANDATORY
    # two choices BOARD or BCM
    gpio.setmode(gpio.BOARD)
    gpio.setwarnings(False)

    '''
    My watering zone map

    Zone 1 - Backyard - GPIO 13 - Relay 8
    Zone 2 - Side House - GPIO 12 - Relay 7
    Zone 3 - Flower Bed - GPIO 11 - Relay 6
    Zone 4 - Front yard - GPIO 10 - Relay 5

    '''

    mapZonePin[1] = 13
    mapZonePin[2] = 12
    mapZonePin[3] = 11
    mapZonePin[4] = 10

    # Set all pins to output
    gpio.setup(boardPins, gpio.OUT, initial=gpio.LOW)


# Pull in calendar

def checkschedule():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    eventsResult = service.events().list(
        calendarId=calendarid,
        timeMin=now,
        maxResults=1,
        singleEvents=True,
        orderBy='startTime').execute()

    events = eventsResult.get('items', [])

    if len(events) == 0:
        return 'No upcoming events found.'
    else:
        # Check to see if start time is within last 10 minutes
        eventdate = events[0]['start'].get('dateTime', [])
        timedelta = datetime.strptime(eventdate[:19], datefmt) - datetime.strptime(now[:19], datefmt)

        if timedelta.seconds < 600:
            # Run this event
            tasks = events[0].get('description', [])

            if tasks:
                zonedict = dict((k.strip(), v.strip()) for k,v in (item.split('=') for item in tasks.split('\n')))
                return zonedict

        else:
            return 'No jobs to run'

    return ''


# Water Zone
def setZone(zoneID, status):
    if status == 'ON':
        gpio.output(mapZonePin[zoneID], gpio.HIGH)
    else:
        gpio.output(mapZonePin[zoneID], gpio.LOW)


def shutdownall():
    for pinid in boardPins:
        setZone(pingid, 'OFF')


def main():
    # Check to see if pidfile exist

    if os.path.exists(pidfilepath):
        # Open file to see if processid is still running
        pidfile = open(pidfilepath, 'r')
        
        if checkpid(int(pidfile.read())):
            # Process is already running
            sys.exit()
        else:
            # Process file created but process not running
            os.remove(pidfilepath)
            createpidfile()
    else:
        createpidfile()

    zonedict = checkschedule()

    jobqueue = True
    while jobqueue:
        for zone in zonedict:
            runtime = int(zonedict[zone])

            if runtime < zoneinterval:
                zonedict[zone] = runtime - zoneinterval
                runtime = zoneinterval
            else:
                zonedict[zone] = 0

            setZone(int(zone), 'ON')
            time.sleep(int(runtime) * 60)
            setZone(int(zone), 'OFF')

        jobswaiting = 0
        for zone in zonedict:
            jobswaiting = jobswaiting + int(zonedict[zone])

        if jobswaiting == 0:
            jobqueue = False
    shutdown()

def shutdown():
    os.remove(pidfilepath)
    sys.exit()

def createpidfile():
    pidfile = open(pidfilepath, 'w')
    pidfile.write(os.getpid())
    pidfile.close()


def checkpid(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def get_credentials():
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    return credentials


if __name__ == '__main__':
    main()


