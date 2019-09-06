# -*- coding: utf-8 -*-
 
import sys
import requests
import json

import logging

logfile = '/dvol/log/gold_update.log'
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
def linebotMessage(msg):
    url = 'https://script.google.com/macros/s/AKfycbx7wcXkvYReFbTOuPQnYvSorB59AuZpIFNwWvmH/exec'
    jstr = { "events" : [{
        "replyToken" : "",
        "message" : {"text":msg}}]
    }

    r = requests.post(url, json = jstr)
    # print('linebot msg: {}'.format(msg.encode('utf-8')))
    logit('linebot result: {}'.format(r.status_code))

def getGoldPrice():
    # first, we login the skwentex server with user/password
    url = 'https://www.tw9999.tw/apis/api_price.php'
        
    sess = requests.Session()
    page = sess.get(url)
    db = json.loads(page.text)
    try:
        gold_bid = int(db['gold']['bid_NT'])
        gold_ask = int(db['gold']['ask_NT'])
        goldT_bid = int(db['goldStrip']['bid_NT'])
        goldT_ask = int(db['goldStrip']['ask_NT'])
        msg = '!gold 黃金報價\n國際: {},{}\n銀樓: {},{}\n價差: {},{}'.format(
            gold_bid, gold_ask,
            goldT_bid, goldT_ask,
            gold_bid-goldT_ask, gold_ask-goldT_bid)
        linebotMessage(msg)
        logit(msg)

    except Exception as ex:
        logit("except: {}".format(ex))

if __name__ == '__main__':
    getGoldPrice()
