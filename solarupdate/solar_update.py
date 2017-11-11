import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
from firebase import firebase
from datetime import date, datetime, timedelta
import dateutil

def get_solar_station_data(year, month, day, plist):
    username = 'mingshing.su@gmail.com'
    password = 'jack6819'

    data = {'LoginCloud$UserName': username, 
            'LoginCloud$Password': password, 
            'LoginCloud$LoginButton': '登入'}

    url = 'http://skwentex.cloudapp.net/Login.aspx'
        
    sess = requests.Session()
    page = sess.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    data['__VIEWSTATE'] = soup.select_one('#__VIEWSTATE')["value"]
    data['__VIEWSTATEGENERATOR'] = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    data['__EVENTVALIDATION'] = soup.select_one('#__EVENTVALIDATION')["value"]
    page1 = sess.post(url, data=data)

    default_url = 'http://skwentex.cloudapp.net/Default.aspx'
    open_page = sess.get(default_url)

    soup = BeautifulSoup(open_page.text, 'html.parser')
    data['__VIEWSTATE'] = soup.select_one('#__VIEWSTATE')["value"]
    data['__VIEWSTATEGENERATOR'] = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    data['__EVENTVALIDATION'] = soup.select_one('#__EVENTVALIDATION')["value"]
    data['__EVENTTARGET'] = 'ctl00$MainContent$lstViewAllStationsInfo$ctrl0$ctl00$lkbtn'
    data['__EVENTARGUMENT'] = ''
    open_page = sess.post(default_url, data=data)

    url_daily = 'http://skwentex.cloudapp.net/PowerPlantInformation/DailyReport.aspx'

    data = {
        'ctl00$ctl00$ddlLanguage': 'zh-TW',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlReportLevel':'Inverter',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlReportType':'Daily',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtFileType':'view',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ReportRowStyle':'rbNormal',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlYearStart':year,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlYearEnd':year,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlMonthStart':month,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlMonthEnd':month,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$hdDayStart':day,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$hdDayEnd':day,
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtStationCheckBoxList$0':'112',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$txtStationCheckBoxList$1':'113',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlStation':'112',
        'ctl00$ctl00$MainContent$ContentPlaceHolder1$ExportDailyReport':'送出'}
    
    page_daily = sess.get(url_daily)
        
    soup = BeautifulSoup(page_daily.text, 'html.parser')
    data['__VIEWSTATE'] = soup.select_one('#__VIEWSTATE')["value"]
    data['__VIEWSTATEGENERATOR'] = soup.select_one('#__VIEWSTATEGENERATOR')["value"]
    data['__EVENTVALIDATION'] = soup.select_one('#__EVENTVALIDATION')["value"]
    data['__EVENTTARGET'] = ''
    data['__EVENTARGUMENT'] = ''
    data['__LASTFOCUS'] = ''

    res = []
    for station in plist:
        data['ctl00$ctl00$MainContent$ContentPlaceHolder1$ddlStation'] = station
        page_daily = sess.post(url_daily, data=data)
        df = pd.read_html(page_daily.text, header=0)[1]
        res.append(df)

    return res

def write_solar_db(df, station):
    fb = firebase.FirebaseApplication('https://solar-0.firebaseio.com', None)

    for index, row in df.iterrows():
        if row["H05":"H18"].isnull().all():
            break

        row = row.fillna(0)
        dev = int(row["Device"])
        month, day = row["Day"].split('/')
        month = int(month)
        day = int(day)
        dstr = "{}{:02}{:02}".format(year, month, day)
        inv = "inv{:02}".format(dev)
        dpath = '/db/{}/power/{}'.format(station, inv)
        power = {}
        for t in range(5, 19):
            hour = "{:02}".format(t)
            col = "H" + hour
            val = float(row[col])
            power[hour] = val
        print(dpath, dstr, power)
        fb.put(dpath, dstr, power)

sunshine_tbls = {}
sunshine_url = "http://e-service.cwb.gov.tw/HistoryDataQuery/DayDataController.do?command=viewMain&station=467440&stname=%25E9%25AB%2598%25E9%259B%2584&datepicker="
def get_sunshine(year, month, day, hour):
    dstr = "{}-{:02}-{:02}".format(year, month, day)
    if dstr not in sunshine_tbls:
        url = sunshine_url + dstr
        sunshine_tbls[dstr] = pd.read_html(url, header=1, encoding="cp950")[0]
    tbl = sunshine_tbls[dstr]["全天空日射量(MJ/㎡)GloblRad"] / 3.6
    return tbl.get(hour)

def update_sunshine_date(dt):
    station = '/sunshine/高雄'
    year, month, day = dt.year, dt.month, dt.day
    dstr = "{}{:02}{:02}".format(year, month, day)
    fb = firebase.FirebaseApplication('https://solar-0.firebaseio.com', None)

    if fb.get(station, dstr):
        # already has data, just return
        return

    # save sunshine data
    vals = {}
    dstr = '{}{:02}{:02}'.format(year, month, day)
    for hour in range(5, 19):
        sunshine = get_sunshine(year, month, day, hour)
        if sunshine is not None:
            vals["{:02}".format(hour)] = sunshine
    if vals:
        print(station, dstr, vals)
        fb.put(station, dstr, vals)

if __name__ == '__main__':
    n = len(sys.argv)
    if n == 1:
        dt = date.today()
    elif n == 2:
        dt = dateutil.parser.parse(sys.argv[1])
    else:
        print("usage: solar_update.py [date]")
        print("  if date is not given, implying today")

    year, month, day = dt.year, dt.month, dt.day
    print("{:%Y-%m-%d %H:%M:%S}: get solar data of {}-{:02}-{:02}".format(datetime.now(), year, month, day))
    exit()

    plist = ['112', '113']
    stations = ['solar01', 'solar02']
    dfs = get_solar_station_data(year, month, day, plist)

    for df, station in zip(dfs, stations):
        write_solar_db(df, station)

    prevday = dt - timedelta(days=1)
    update_sunshine_date(prevday)
