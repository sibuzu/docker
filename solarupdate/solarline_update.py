# -*- coding: utf-8 -*-
 
import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
from firebase import firebase
from datetime import date, datetime, timedelta
import dateutil
import json
import calendar

firebaseDb = firebase.FirebaseApplication('https://solarpanel-0.firebaseio.com', None)

def loadStationData():
    dpath = 'https://solarpanel-0.firebaseio.com'
    sdata = firebaseDb.get(dpath, "stations")
    return sdata

def updateAlarmCount(sdata):
    for sname, station in sdata.items():
        today = (datetime.now()-timedelta(hours=5)).strftime('%Y-%m-%d')
        n = 0
        if 'alarmlog' in station:
            # print(">>>", station['alarmlog'])
            alarmlist = [x for x in station['alarmlog'].keys() if x >= today]
            n = len(alarmlist)
            # print(today, alarmlist)
        station['summary']['alarm_count'] = n
        print("{}: {}".format(sname, n))

def linebotMessage(msg):
    url = 'https://script.google.com/macros/s/AKfycbx7wcXkvYReFbTOuPQnYvSorB59AuZpIFNwWvmH/exec'
    jstr = { "events" : [{
        "replyToken" : "",
        "message" : {"text":msg}}]
    }

    r = requests.post(url, json = jstr)
    # print('linebot msg: {}'.format(msg.encode('utf-8')))
    print('linebot result: {}'.format(r.status_code))

if __name__ == '__main__':
    print("update solarline")
    
    sdata = loadStationData()
    # print(str(sdata).encode('utf-8'))

    today = datetime.now() - timedelta(hours=5)

    # power
    today_str = "{:%Y%m%d}".format(today)
    power_str = ''
    for skey in sorted(sdata.keys()):
        try:
            station = sdata[skey]
            sname = station['info']['name']       
            power = station['power']['day'][today_str] / station['info']['station_scale']  
            warning = station['summary']['alarm_count']
            power_str += '{} 發電量:{:.2f} 警示:{}\n'.format(sname, power, warning)
        except Exception as ex:
            print("except: {}".format(ex))

    linebotMessage('!power ' + power_str.strip())
    # print(power_str.encode('utf-8'))

    # alarm
    today_str = "{:%Y-%m-%d}".format(today)
    alarm_str = ''
    for skey in sorted(sdata.keys()):
        try:
            station = sdata[skey]
            sname = station['info']['name']
            if 'alarmlog' in station:
                alarmlog = station['alarmlog']
                for akey in sorted(alarmlog):
                    if akey[:10] >= today_str:
                        astr = alarmlog[akey].split(',')
                        alarm_str += sname + ' ' + akey[11:] + ' ' + astr[1] + ' ' + astr[2] + '\n'
        except Exception as ex:
            print("except: {}".format(ex))

    linebotMessage('!alarm ' + alarm_str.strip())

    print("--------------------------------------")
    print("{:%Y-%m-%d %H:%M:%S}: solarline is updated".format(datetime.now()))
    print("--------------------------------------")
