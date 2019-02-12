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

def saveStationData(sdata):
    dpath = 'https://solarpanel-0.firebaseio.com'
    firebaseDb.put(dpath, "stations", sdata)

### get session
def getSkwSession():
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
    
    return sess

def timeIndex(str):
    str = str[-8:]
    h = int(str[:2])
    m = int(str[3:5])
    t = (h * 60 + m) // 5
    # print(t, str)
    return t

def reduceInvData(invDict):
    klist = sorted(invDict.keys())
    
    last = 0
    newdict = {}
    for i, k in enumerate(klist):
        idx = timeIndex(k)
        addit = False
        if idx > last:
            addit = True
        elif i == len(klist) - 1:
            addit = True

        if addit:
            newdict[k] = invDict[k]
        last = idx
    return newdict

def getSolarRawdata(sdata, sess, stations):

    t = datetime.now()
    if t.hour < 5:
        t -= timedelta(hours=6)
    print(t)

    urlQuery = 'http://skwentex.cloudapp.net/PowerPlantInformation/StationReportExport.aspx'

    data = {
        'ctl00$ctl00$ddlLanguage': 'zh-TW',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$hfItem': 'Inverter',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$hfInterval': 'Raw',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlFromYear': t.year,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlToYear': t.year,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlFromMonth': "{:02}".format(t.month),
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlToMonth': "{:02}".format(t.month),
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlFromDay': "{:02}".format(t.day),
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlToDay': "{:02}".format(t.day),
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlHour': 12,
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
            
    for sid, name, dstart, dend, sname in stations:
        
        # get last index of sdata
        inverters = sdata[sname]["inverters"]
        
        data['ctl00$ctl00$MainContent$ContentPlaceHolder1$hfStation'] = sid
        stationdata = {}
        for did in range(dstart, dend + 1):
            inv = "inv{:02}".format(did - dstart + 1)
            rawdata = {}
            if "data" in inverters[inv]:
                rawdata = inverters[inv]["data"]

            end_hour = t.hour
            if rawdata:
                lastkey = sorted(list(rawdata.keys()))[-1]
                lastday = lastkey[:10]
                reqday = "{:04}-{:02}-{:02}".format(t.year, t.month, t.day)
                if lastday != reqday:
                    # newday, clear all
                    rawdata = {}
                    start_hour = 5
                else:
                    start_hour = int(lastkey[-8:-6])
            else:
                start_hour = 5
                
            if start_hour < 5:
                start_hour = 5
            if end_hour > 18:
                end_hour = 18
            
            print("hour range: {}-{}".format(start_hour, end_hour))
            data['ctl00$ctl00$MainContent$ContentPlaceHolder1$hfDevice'] = did

            try:
                for hh in range(start_hour, end_hour+1):
                    data['ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlHour'] = hh
                    print("query: S{}, {}, H{}".format(sid, inv, hh))

                    # we just set timeout as 20 seconds
                    # we don't want to wait to long in case the server busy
                    page = sess.post(urlQuery, data=data, timeout=20)
                    dfs = pd.read_html(page.text, header=0)
                    n = len(dfs)
                    if n < 2 or len(dfs[n-1]) == 0:
                        continue
                    df = dfs[n-1]
                    
                    cols = df.columns[[0,1,2,3,7]]
                    for index, row in df[cols].iterrows():
                        time = row[0].replace('/', '-')
                        rawdata[time] = "{},{},{},{}".format(row[1],row[2],row[3],row[4])

            except requests.exceptions.Timeout:
                print("** request timeout **")
            except Exception as ex:
                print(str(ex).encode('utf-8'))
                # sys.exit(1)
                
            inverters[inv]["data"] = reduceInvData(rawdata)
            print("rawdata:", len(rawdata), "reduced:", len(inverters[inv]["data"]))

def getAuoPower(sdata, sname, plant):
    interval = 'Day'
    date1 = "2018/04/01"
    date2 = datetime.now().strftime("%Y/%m/%d")
    url = 'https://gms.auo.com/BenQWebDBsource/EnergyList/GetEnergyLIst?plantNo={}&Data_Type=kWh&Start_Time={}&End_Time={}&Time_Interval={}&timeZoneOffset=8'
    url = url.format(plant, date1, date2, interval)
    jtxt = requests.get(url).text
    db = json.loads(jtxt)
    
    day = {}
    for rec in db['lstValue']:
        tag = rec['shift_time']
        if tag=='Total':
            continue
        tag = tag[:4] + tag[5:7] + tag[8:]
        val = sum([float(x) for x in rec['strValue'].split(',')])
        day[tag] = val
    
    station = sdata[sname]
    if "power" not in station:
        station["power"] = {}
    station["power"]["day"] = day   
    
    # merge month data
    month = {}
    for i in range(10, 13):
        tag = str(201700 + i)
        month[tag] = 0.0
    for i in range(1, 8):
        tag = str(201800 + i)
        month[tag] = 0.0        
    for t, val in day.items():
        tag = t[:6]
        if tag not in month:
            month[tag] = 0
        month[tag] += val
    station["power"]["month"] = month 
    
    # get hour data
    interval = 'HOUR'
    date1 = (datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")
    date2 = datetime.now().strftime("%Y/%m/%d")
    url = 'https://gms.auo.com/BenQWebDBsource/EnergyList/GetEnergyList?plantNo={}&Data_Type=kWh&Start_Time={}&End_Time={}&Time_Interval={}&timeType=UTC&timeZoneOffset=8'
    url = url.format(plant, date1, date2, interval)
    jtxt = requests.get(url).text
    db = json.loads(jtxt)
    hour = {}
    for rec in db['lstValue']:
        tag = rec['shift_time']
        if tag=='Total':
            continue
        xmonth = int(tag[:2])
        xday = int(tag[3:5])
        xhour = int(tag[6:8]) - 1
        # print(xmonth, xday, xhour, rec['strValue'])
        if xhour<5 or xhour>18:
            continue
        xyear = date1[:4] if xmonth > 6 else date2[:4]
        tag = "{}{:02}{:02}{:02}".format(xyear, xmonth, xday, xhour)
        val = sum([float(x) for x in rec['strValue'].split(',')])
        hour[tag] = val
    station["power"]["hour"] = hour 
    
    return db
    
def getLastTimestamp(station):
    ts = "2000-01-01 00:00:00"
    for _, inv in station["inverters"].items():
        if "data" in inv:
            keylist = sorted(list(inv["data"].keys()))
            if keylist and keylist[-1] > ts:
                ts = keylist[-1]
    return ts          

def updateLastTimestamp(sdata):
    for _, station in sdata.items():
        station["summary"]["timetag"] = getLastTimestamp(station)

def getAuoInverters(sdata, sname, plant, inv_count):    
    date = (datetime.now() - timedelta(hours=6)).strftime("%Y/%m/%d")
    inverters = sdata[sname]["inverters"]
    for uid in range(1, inv_count+1):
        inv = {}
        url = 'https://gms.auo.com/BenQWebDBsource/RawData/GetRawDataValue?pck={}&uid=COM1_{:03}&sTime={}&eTime={}'
        url = url.format(plant, uid, date, date)
        # print(url)
        jtxt = requests.get(url).text
        db = json.loads(jtxt)
        for rec in db:
            tag = rec["CollectionTime"]
            tag = tag.replace('/', '-')
            tstr = tag[-8:]
            V = rec["v4"]
            I = rec["v5"]
            KW = rec["v6"]
            Power = rec["v13"]
            strValue = "{},{},{},{}".format(V, I, KW, Power)
            if tstr < "05:00:00" or tstr >= "19:00:00":
                continue
            if float(Power) <= 1:
                continue
            inv[tag] = strValue
        
        inverters["inv{:02}".format(uid)]["data"] = inv
        print("inv{:02}: {}".format(uid, len(inv)))

def updateHour(sname, station, inverters, dtag):
    allhours = [0] * 24
    for _, inv in inverters.items():
        tags = sorted(list(inv["data"].keys()))
        if len(tags)==0:
            continue
        
        hours = [0] * 24   
        hours[4] = float(inv["data"][tags[0]].split(',')[3])  # hour4 as first
        for tag in tags:
            val = inv["data"][tag]
            power = float(val.split(',')[3])
            htag = int(tag[11:13])
            if htag>=5 and htag<=18:
                hours[htag] = power
            
        for htag in range(5, 19):
            if hours[htag] == 0:
                hours[htag] = hours[htag-1]

        for htag in range(18, 4, -1):
            if hours[htag]>0:
                hours[htag] -= hours[htag-1]
        
        hours[4] = 0
        for i in range(5, 19):
            allhours[i] += hours[i]
            
    for i in range(5, 19):
        hstr = dtag + "{:02}".format(i)
        station["power"]["hour"][hstr] = allhours[i]
        
def updateDay(sname, station, inverters, dtag):
    dayPower = 0
    for _, inv in inverters.items():
        tags = sorted(list(inv["data"].keys()))
        if len(tags)==0:
            continue
        power0 = float(inv["data"][tags[0]].split(',')[3]) 
        power1 = float(inv["data"][tags[-1]].split(',')[3]) 
        dayPower += (power1 - power0)
    station["power"]["day"][dtag] = dayPower

def updateMonth(sname, station, inverters, dtag):
    mtag = dtag[:6]
    mpower = 0
    for day, value in station["power"]["day"].items():
        if day[:6] == mtag:
            mpower += value        
    station["power"]["month"][mtag] = mpower

def updateHourDayMonth(sdata, dtag):
    for sname, station in sdata.items():
        inverters = station["inverters"]
        updateHour(sname, station, inverters, dtag)
        updateDay(sname, station, inverters, dtag)
        updateMonth(sname, station, inverters, dtag)

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

def getAuoAlarmlog(plant):
    url = 'https://gms.auo.com/BenQWebDBsource/eventlog/GetPlantMonthlyMIEvent?plantNo={}&currentPlantMonth={}/{}&timeZoneOffset=8&timeType=UTC&lang=zh-TW&format=json'
    t = datetime.now()
    url = url.format(plant,t.year,t.month)
    jtxt = requests.get(url).text
    js = json.loads(jtxt)
    alarmlog = {}
    for x in js:
        dt = dateutil.parser.parse(x['EventStartTime'])
        dt = dt.strftime('%Y-%m-%d %H:%M:%S')
        inv = x['UnitID'][-2:]
        code = x['EventCode'][-5:].upper()
        desc = x['EventDescription']
        if code == 'F0024':   # COMM1 warning
            continue
        if code == 'AU219':   # 0 kWh
            continue
        msg = "INV{},{},{}".format(inv, code, desc)
        dt = "{} INV{}".format(dt, inv)
        print(dt, msg.encode('utf-8'))
        alarmlog[dt] = msg
    return alarmlog

def mergeAlarmlog(alarmlog1, alarmlog2, keepdays):
    t = "{:%Y-%m-%d}".format(datetime.now() - timedelta(days=keepdays))
    merged = { **alarmlog1, **alarmlog2 }
    
    for k in list(merged):
        if k < t:
            del merged[k]
    
    return merged

def updateAuoAlarmlog(sdata, sname, plant, keepdays):
    station = sdata[sname]
    today = datetime.now().strftime('%Y-%m-%d')
    
    if 'alarmlog' not in station:
        station['alarmlog'] = {}
    
    alarmlog = getAuoAlarmlog(plant)
        
    # calc today alarm count
    station['alarmlog'] = mergeAlarmlog(station['alarmlog'], alarmlog, keepdays)
    alarmlist = [x for x in station['alarmlog'].keys() if x >= today]
    station['summary']['alarm_count'] = len(alarmlist)

def updateSkwAlarmlog(sdata, sess, year, stations):
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

    for stationId, stationName, _, _, sname in stations:
        data['ctl00$ctl00$MainContent$ContentPlaceHolder1$txtStationDropDownList'] = stationId
        page = sess.post(urlQuery, data=data)
        dfs = pd.read_html(page.text, header=0)
        n = len(dfs)
        if n < 2 or len(dfs[n-1]) == 0:
            continue
        df = dfs[n-1]
        # print(df)
        
        station = sdata[sname]
        if 'alarmlog' not in station:
            station['alarmlog'] = {}

        for _, row in df.iterrows():
            inv = row['設備']
            timetag = row['發生時間'].replace('/','-') + " INV{:02}".format(inv)
            code = row['警報代碼']
            desc = row['描述']
            msg = "INV{:02},{},{}".format(inv, code, desc)
            if code != 'DEF23':
                print(sname, timetag, msg.encode('utf-8'))
                station['alarmlog'][timetag] = msg

if __name__ == '__main__':
    print("update solarpanel")
    sdata = loadStationData()
    # print(str(sdata).encode('utf-8'))

    # skw rawdata
    stations = [('113','禹日',933,947,'S02')]
    sess = getSkwSession()
    
    getSolarRawdata(sdata, sess, stations)

    # auo rawdata
    plants = [("S01", "BDL018030127", 15), 
        ("S03", 'BDL018030128', 6),
        ("S04", 'BDL018030166', 17), 
        ("S05", 'BDL018090293', 4), 
        ("S06", 'BDL018090292', 9)]

    for plant in plants:
        getAuoInverters(sdata, plant[0], plant[1], plant[2])


    # get skw alarmlog
    today = datetime.now() - timedelta(hours=5)
    updateSkwAlarmlog(sdata, sess, today.year, stations)  

    # get auo alarmlog 
    for plant in plants:
        updateAuoAlarmlog(sdata, plant[0], plant[1], 30)
    
    # update hour, day, month
    dtag = today.strftime("%Y%m%d")
    updateHourDayMonth(sdata, dtag)

    # update last
    updateLastTimestamp(sdata)
    updateAlarmCount(sdata)

    saveStationData(sdata)

    print("--------------------------------------")
    print("{:%Y-%m-%d %H:%M:%S}: solarpanel is updated".format(datetime.now()))
    print("--------------------------------------")
