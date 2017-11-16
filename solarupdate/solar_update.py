# -*- coding: utf-8 -*-
 
import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
from firebase import firebase
from datetime import date, datetime, timedelta
import dateutil

firebaseDb = firebase.FirebaseApplication('https://solar-0.firebaseio.com', None)
firebaseRaw = firebase.FirebaseApplication('https://solar-2.firebaseio.com', None)

def updateSolarAlarmlog(sess, year, stations):
    urlQuery = 'http://skwentex.cloudapp.net/PowerPlantInformation/AlarmReport.aspx'

    data = {
        'ctl00$ctl00$ddlLanguage': 'zh-TW',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtYearDropDownList': year,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtStateDropDownList': 'ON',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtFromDate': '',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtToDate': '',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlAlarmCode': '',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtFileType': 'view',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$Button1': '送出'}
    
    page = sess.get(urlQuery)
        
    soup = BeautifulSoup(page.text, 'html.parser')
    data['__VIEWSTATE'] = soup.select_one('#__VIEWSTATE')["value"]
    data['__VIEWSTATEGENERATOR'] = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    data['__EVENTVALIDATION'] = soup.select_one('#__EVENTVALIDATION')["value"]
    data['__EVENTTARGET'] = ''
    data['__EVENTARGUMENT'] = ''
    data['__LASTFOCUS'] = ''

    page = sess.get(urlQuery)
        
    soup = BeautifulSoup(page.text, 'html.parser')
    data['__VIEWSTATE'] = soup.select_one('#__VIEWSTATE')["value"]
    data['__VIEWSTATEGENERATOR'] = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    data['__EVENTVALIDATION'] = soup.select_one('#__EVENTVALIDATION')["value"]
    data['__EVENTTARGET'] = ''
    data['__EVENTARGUMENT'] = ''
    data['__LASTFOCUS'] = ''

    alarmlog = {}
    for stationId, stationName, _, _ in stations:
        data['ctl00$ctl00$MainContent$ContentPlaceHolder1$txtStationDropDownList'] = stationId
        page = sess.post(urlQuery, data=data)
        dfs = pd.read_html(page.text, header=0)
        if len(dfs) < 2 or len(dfs[1]) == 0:
            continue
        df = dfs[1]

        for _, row in df.iterrows():
            timetag = row['發生時間'].replace('/','-')
            inv = row['設備']
            code = row['警報代碼']
            desc = row['描述']
            msg = "INV{:02},{},{}".format(inv, code, desc)
            print(timetag, msg)

            # write to db /alarmlog/正霆/"2017-11-16 18:05:02"
            # dpath = /alarmlog/正霆/
            # data = "2017-11-16 18:05:02" -> "INV02,DEF23,HW COMM1"
            dpath = '/alarmlog/{}'.format(stationName)
            firebaseDb.patch(dpath, {timetag: msg})

def updateSolarRawdata(sess, year, month, day, hour, stations):

    urlQuery = 'http://skwentex.cloudapp.net/PowerPlantInformation/StationReportExport.aspx'

    data = {
        'ctl00$ctl00$ddlLanguage': 'zh-TW',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$hfItem': 'Inverter',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$hfInterval': 'Raw',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlFromYear': year,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlToYear': year,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlFromMonth': "{:02}".format(month),
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlToMonth': "{:02}".format(month),
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlFromDay': "{:02}".format(day),
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlToDay': "{:02}".format(day),
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlHour': hour,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtFileType':'view',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$btnSubmit': '送出'}
    
    page = sess.get(urlQuery)

    soup = BeautifulSoup(page.text, 'html.parser')
    data['__VIEWSTATE'] = soup.select_one('#__VIEWSTATE')["value"]
    data['__VIEWSTATEGENERATOR'] = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    data['__EVENTVALIDATION'] = soup.select_one('#__EVENTVALIDATION')["value"]
    data['__EVENTTARGET'] = ''
    data['__EVENTARGUMENT'] = ''
    data['__LASTFOCUS'] = ''

    hourstart = 5
    hourend = hour
    if hourend < 5 or hourend > 18:
        hourend = 18
    rawdata = {}
    for sid, name, dstart, dend in stations:
        data['ctl00$ctl00$MainContent$ContentPlaceHolder1$hfStation'] = sid
        for did in range(dstart, dend+1):
            inv = did - dstart + 1

            # try to read rawdata from firebase, and then we just download from the end 
            # read db from /rawdata/正霆/inv01/20171101
            # dpath = /rawdata/正霆/inv01
            # dstr = 20171101
            # rawdata = 06:05:01 -> "30,9.8,2.1,132"
            dpath = '/rawdata/{}/inv{:02}'.format(name, inv)
            dstr = "{}{:02}{:02}".format(year, month, day) 
            rawdata = firebaseRaw.get(dpath, dstr) or {}

            # read db from 05:00AM if db is empty
            hourstart = lastHour(rawdata) if rawdata else 5
            
            print("hour range: {}-{}".format(hourstart, hourend))
            data['ctl00$ctl00$MainContent$ContentPlaceHolder1$hfDevice'] = did
            try:
                for hh in range(hourstart, hourend+1):
                    data['ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlHour'] = hh
                    print("query: S{}, Inv{:02}, {} H{}".format(sid, inv, dstr, hh))

                    # we just set timeout as 20 seconds
                    # we don't want to wait to long in case the server busy
                    page = sess.post(urlQuery, data=data, timeout=20)
                    dfs = pd.read_html(page.text, header=0)
                    if len(dfs) < 2 or len(dfs[1]) == 0:
                        continue
                    df = dfs[1]
                    cols = df.columns[[0,1,2,3,7]]
                    for index, row in df[cols].iterrows():
                        time = row[0][-8:]
                        rawdata[time] = "{},{},{},{}".format(row[1],row[2],row[3],row[4])

            except requests.exceptions.Timeout:
                print("** request timeout **")
            except Exception as ex:
                print(ex)
                sys.exit(1)

            # write to raw-db /rawdata/正霆/inv01/20171101
            # dpath = /rawdata/正霆/inv01
            # dstr = 20171101
            # rawdata = 06:05:01 -> "30,9.8,2.1,132"
            dpath = '/rawdata/{}/inv{:02}'.format(name, inv)
            dstr = "{}{:02}{:02}".format(year, month, day) 
            firebaseRaw.put(dpath, dstr, rawdata)

def getRawdataFromDb(stationName, inv, dstr):
    # read rawdata from db /rawdata/正霆/inv01/20171101
    # dpath = /rawdata/正霆/inv01
    # dstr = 20171101
    # rawdata = "06:05:01" -> "30,9.8,2.1,132"
    dpath = '/rawdata/{}/inv{:02}'.format(stationName, inv)
    rawdata = firebaseRaw.get(dpath, dstr)
    
    # convert to "timetag" -> V, A, KW, KWH
    # data = "06:05:01" -> 30, 9.8, 2.1, 132
    data = {}
    if rawdata:
        for k, v in rawdata.items():
            vals = [float(x) for x in v.split(',')]
            data[k] = vals
    else:
        data['05:00:00'] = [0.0,0.0,0.0,0.0]

    # convert dict to DataFrame
    return pd.DataFrame.from_dict(data, orient='index')
    
def updateSolarPower(stations, year, month, day):   
    for _, stationName, _, _ in stations: 
        data = {}
        total = 0
        dstr = "{}{:02}{:02}".format(year, month, day)
        for inv in range(1, 16):
            df = getRawdataFromDb(stationName, inv, dstr)
            # print(df)
            vbase = df.ix[0,3]
            vtotal = df.ix[-1,3]
            total += vtotal - vbase
            # print(vbase, vtotal)
            for h in range(5,19):
                t0 = "{:02}:00:00".format(h)
                t1 = "{:02}:00:00".format(h+1)
                sdf0 = df[df.index<t0]
                sdf1 = df[df.index<t1]
                v0 = sdf0.ix[-1,3] if len(sdf0) else vbase
                v1 = sdf1.ix[-1,3] if len(sdf1) else vbase
                power = v1 - v0
                key = 'inv{:02}_{:02}'.format(inv, h)
                data[key] = power
        data['total'] = total

        # write power to /power/正霆/20171101
        # dpath = /power/正霆
        # dstr = 20171101
        # data = "inv01_09" -> 2.16
        dpath = "/power/{}".format(stationName)
        firebaseDb.put(dpath, dstr, data)

    print("--------------------------------------")
    print("{}-{:02}-{:02} power is updated".format(year, month, day))
    print("--------------------------------------")

def cpSolarLastRawDb(stations, year, month, day):   
    # copy raw data
    # rawDB: /rawdata/正霆/inv01/<lastday> -> /rawdata/正霆/inv01

    dstr = "{}{:02}{:02}".format(year, month, day)
    dataAll = {}
    for _, stationName, _, _ in stations: 
        dataStation = {}
        dstr = "{}{:02}{:02}".format(year, month, day)
        for inv in range(1, 16):
            # rawDB: /rawdata/正霆/inv01/<lastday> 
            sinv = 'inv{:02}'.format(inv)
            dpath = '/rawdata/{}/inv{:02}'.format(stationName, inv)
            data = firebaseRaw.get(dpath, dstr) 
            dataStation[sinv] = data
        dataAll[stationName] = dataStation 

    # cp /rawdata/正霆/20171101
    # dpath = /
    # dstr = rawdata
    # data = "正霆" -> "inv01" -> rawdata
    firebaseDb.put('/', 'rawdata', dataAll)

    print("--------------------------------------")
    print("{}-{:02}-{:02} last rawdata is copied".format(year, month, day))
    print("--------------------------------------")

def updateSolarRawDb(year, month, day, hour, stations):
    username = 'mingshing.su@gmail.com'
    password = 'jack6819'

    data = {'LoginCloud$UserName': username, 
            'LoginCloud$Password': password, 
            'LoginCloud$LoginButton': '登入'}

    # first, we login the skwentex server with user/password
    url = 'http://skwentex.cloudapp.net/Login.aspx'
        
    sess = requests.Session()
    page = sess.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    data['__VIEWSTATE'] = soup.select_one('#__VIEWSTATE')["value"]
    data['__VIEWSTATEGENERATOR'] = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    data['__EVENTVALIDATION'] = soup.select_one('#__EVENTVALIDATION')["value"]
    page = sess.post(url, data=data)

    urlDefault = 'http://skwentex.cloudapp.net/Default.aspx'
    page = sess.get(urlDefault)

    soup = BeautifulSoup(page.text, 'html.parser')
    data['__VIEWSTATE'] = soup.select_one('#__VIEWSTATE')["value"]
    data['__VIEWSTATEGENERATOR'] = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    data['__EVENTVALIDATION'] = soup.select_one('#__EVENTVALIDATION')["value"]
    data['__EVENTTARGET'] = 'ctl00$MainContent$lstViewAllStationsInfo$ctrl0$ctl00$lkbtn'
    data['__EVENTARGUMENT'] = ''
    page = sess.post(urlDefault, data=data)

    # alarmlog section
    updateSolarAlarmlog(sess, year, stations)

    # rawdata section
    updateSolarRawdata(sess, year, month, day, hour, stations)    
    print("--------------------------------------")
    print("{}-{:02}-{:02} rawdata is updated".format(year, month, day))
    print("--------------------------------------")

def lastHour(rawdata):
    return int(sorted(list(rawdata.keys()))[-1][:2])

# sunshine website: http://e-service.cwb.gov.tw/HistoryDataQuery/
tblSunshines = {}
urlSunshine = "http://e-service.cwb.gov.tw/HistoryDataQuery/DayDataController.do?command=viewMain&station=467440&stname=%25E9%25AB%2598%25E9%259B%2584&datepicker="
def getSunshine(year, month, day, hour):
    dstr = "{}-{:02}-{:02}".format(year, month, day)
    if dstr not in tblSunshines:
        url = urlSunshine + dstr
        tblSunshines[dstr] = pd.read_html(url, header=1, encoding="utf-8")[0]
    tbl = tblSunshines[dstr]["全天空日射量(MJ/㎡)GloblRad"] / 3.6
    return tbl.get(hour)

def updateSunshineDb(dt):
    year, month, day = dt.year, dt.month, dt.day

    # try to read sunshine from firebase, skip read again if existed
    # read db from /sunshine/高雄/20171101
    # dpath = /sunshine/高雄/
    # dstr = 20171101
    # data = 13 -> 0.78
    dpath = '/sunshine/高雄/'
    dstr = "{}{:02}{:02}".format(year, month, day)
    if firebaseDb.get(dpath, dstr):
        # already has data, just return
        return

    # save sunshine data
    vals = {}
    for hour in range(5, 19):
        sunshine = getSunshine(year, month, day, hour)
        if sunshine is not None:
            vals["{:02}".format(hour)] = sunshine
    if vals:
        firebaseDb.put(dpath, dstr, vals)
        print("--------------------------------------")
        print("{}-{:02}-{:02} sunshine is updated".format(year, month, day))
        print("--------------------------------------")

if __name__ == '__main__':
    n = len(sys.argv)
    if n == 1:
        dt = datetime.now()
    elif n == 2:
        dt = dateutil.parser.parse(sys.argv[1])
    else:
        print("usage: solar_update.py [date]")
        print("  if date is not given, implying today")

    year, month, day, hour = dt.year, dt.month, dt.day, dt.hour
    print("{:%Y-%m-%d %H:%M:%S}: get solar data of {}-{:02}-{:02} H{:02}".format(datetime.now(), 
        year, month, day, hour))
    
    # sunshine
    prevday = dt - timedelta(days=1)
    updateSunshineDb(prevday)

    # station: stationId, stationName, deviceStartId, deviceEndId
    stations = [('112','正霆',918,932), ('113','禹日',933,947)]
    updateSolarRawDb(year, month, day, hour, stations)

    # convert rawdata to power section
    updateSolarPower(stations, year, month, day)

    # copy raw data
    # rawDB: /rawdata/正霆/inv01/<lastday> -> /rawdata/正霆/inv01
    cpSolarLastRawDb(stations, year, month, day)
