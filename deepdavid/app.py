from flask import Flask, render_template,request
from werkzeug.exceptions import BadRequest
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
from io import StringIO
import sys

# local modules
from deepdavid import init, predict

#initalize our flask app
app = Flask("deepdavid")

# logger init
handler = RotatingFileHandler('/dvol/log/deepdavid.log', maxBytes=1000000, backupCount=3)
handler.setLevel(logging.INFO)

formatter = logging.Formatter(fmt='[%(asctime)s][%(levelname)-8s] %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# logger test
app.logger.info("-info log test")
app.logger.warning("-warning log test")
app.logger.error("-error log test")

#initialize these variables
print("---load tensorflow model")
app.logger.info("load tensorflow model")
modelBull, modelBear = init()

#decoding an image from base64 into raw representation
def str2ary(inputs):
    ary = np.loadtxt(StringIO(inputs), delimiter=',')
    return ary

def ary2str(ary):
    app.logger.info("result: {}".format(ary))
    return ','.join([str(x) for x in list(ary.astype(int))])

def req_error(msg):
    app.logger.error(msg)
    raise BadRequest(msg)
 
@app.route('/hello/',methods=['GET','POST'])
def hello():
    app.logger.info("call hello")
    return "Hello DeepDavid<br>"

@app.route('/deep_david/',methods=['GET','POST'])
def deep_david():
    try:
        app.logger.info("call deep_david")
        model = request.values.get("model")
        inputs = request.values.get("inputs")
        if not model:
            req_error('no model paramters')
        if not inputs:
            req_error('no inputs parameters')
        
        ary = str2ary(inputs)
        app.logger.info("model: {}, inputs: {}x{}".format(model, *ary.shape))
        
        if model == "bear":
            outputs = predict(modelBear, ary)
        elif model == "bull":
            outputs = predict(modelBull, ary)
        else:
            req_error('not support model: ' + model)
        return ary2str(outputs)
    except Exception as ex:
        req_error(str(ex))

if __name__ == "__main__":
    app.logger.info("start service")
    app.run(host='0.0.0.0', port=5800, use_reloader=False)
