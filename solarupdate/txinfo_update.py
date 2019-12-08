# -*- coding: utf-8 -*-
 
import sys
import requests
import json
import datetime
import pandas as pd

import logging

logfile = '/dvol/log/txinfo_update.log'
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler(logfile, 'w', 'utf-8'),
        logging.StreamHandler()
    ])

log = logging.getLogger('')

def logit(*args, **kwargs):
    log.info(*args, **kwargs)

### get session
sess = requests.Session()

def linebotMessage(msg):
    url = 'https://script.google.com/macros/s/AKfycbx7wcXkvYReFbTOuPQnYvSorB59AuZpIFNwWvmH/exec'
    jstr = { "events" : [{
        "replyToken" : "",
        "message" : {"text":msg}}]
    }

    r = requests.post(url, json = jstr)
    # print('linebot msg: {}'.format(msg.encode('utf-8')))
    logit('linebot result: {}'.format(r.status_code))

def parseFloat(sval):
    return float(sval.replace(',',''))            

def parse加權指數(txt):
    data = json.loads(txt)
    if 'data1' in data:
        for x in data['data1']:
            if x[0] == '發行量加權股價指數':
                return parseFloat(x[1])
    return 0

def get加權指數():
    try:
        url = 'https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&type=IND'
        x = sess.get(url).text
        加權指數 = round(parse加權指數(x))
        return 加權指數
    except Exception as ex:
        logit("except: {}".format(ex))

    return 0

def get期貨指數():
    try:
        url = 'https://www.taifex.com.tw/cht/3/futDailyMarketExcel'
        x = sess.get(url).text
        df = pd.read_html(x, skiprows=3)[0]
        ym1, price1, ym2, price2 = df.iloc[1,1], df.iloc[1,5], df.iloc[2,1], df.iloc[2,5]
        return int(ym1) % 10000, int(price1), int(ym2) % 10000, int(price2)
    except Exception as ex:
        logit("except: {}".format(ex))

    return 0, 0, 0, 0

def get未平倉():
    try:
        url = 'https://www.taifex.com.tw/cht/3/futContractsDateExcel'
        x = sess.get(url).text
        df = pd.read_html(x)
        未平倉 = df[1].iloc[5,11]
        return 未平倉
    except Exception as ex:
        logit("except: {}".format(ex))

    return 0

def parse買賣超(txt):
    data = json.loads(txt)
    if data['stat'] != 'OK':
        return None
    
    foreign, domestic, dealer = 0, 0, 0
    for x in data['data']:
        # print(x)
        if x[0][:2] == '自營': dealer += parseFloat(x[3])
        elif x[0][:2] == '投信': domestic += parseFloat(x[3])
        elif x[0][:2] == '外資': foreign += parseFloat(x[3])
            
    return foreign, domestic, dealer

def get買賣超():
    try:
        url = 'https://www.twse.com.tw/fund/BFI82U?response=json'
        x = sess.get(url).text
        買賣超 = parse買賣超(x)[0] / 10**8
        return 買賣超
    except Exception as ex:
        logit("except: {}".format(ex))

    return 0

def indexPrice():
    dt = datetime.date.today().strftime('%Y-%m-%d')
    加權指數 = 0
    ym1 = 0
    ym2 = 0
    price1 = 0
    price2 = 0
    spread = 0
    未平倉 = 0
    買賣超 = 0.0
    
    try:
        加權指數 = get加權指數()
        ym1, price1, ym2, price2 = get期貨指數()
        if 加權指數>0 and price1>0:
            spread = price1 - 加權指數
        未平倉 = get未平倉()
        買賣超 = get買賣超()
        
        msg = '!txinfo [{}]\n加權指數: {}\nTX{}: {}\nTX{}: {}\n正逆價差: {}\n未平倉: {}\n買賣超: {:0.2f}億'.format(
            dt,
            加權指數, 
            ym1, price1, ym2, price2,
            spread,
            未平倉, 買賣超)
        linebotMessage(msg)
        logit(msg)

    except Exception as ex:
        logit("except: {}".format(ex))

if __name__ == '__main__':
    indexPrice()
