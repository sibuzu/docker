from flask import Flask, render_template, request
from werkzeug.exceptions import BadRequest
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
import sys

# local modules
# from deepdavid import init_gpu, predict
from deeptorch import init_torch, torch_predict
from util import req_error, ary2str, str2ary

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
# init_gpu()
init_torch()

@app.route('/hello/',methods=['GET','POST'])
def hello():
    app.logger.info("call hello")
    return "Hello DeepDavid"

@app.route('/deep_david/',methods=['GET','POST'])
def deep_david():
    try:
        app.logger.info("call deep_david")
        contents = request.json
        country = contents.get("country")
        
        mode = contents.get("mode")
        model = contents.get("model")
        inputs = contents.get("inputs")
        buysell = contents.get("buysell")
        ensemble = contents.get("ensemble", "A")
        
        if not model:
            req_error('no model paramters')
        if not mode:
            req_error('no mode parameters')
        if not inputs:
            req_error('no inputs parameters')
        
        ary = str2ary(inputs)

        app.logger.info("model: {}, mode: {}, country: {}, buysell: {}, ensemble: {}, inputs: {}x{}".format(
            model, mode, country, buysell, ensemble, *ary.shape))

        # new request
        if country in "tw" :
            ctag = "T"
        elif country=="twn":
            ctag = "N"
        else:
            ctag = ""
 
        # pytorch version
        mpath = "/dvol/deepmodels/pytorch"
        modelname = get_model(mpath, country, ctag, model)

        app.logger.info("model: {}, mode: {}, country: {}, buysell: {}, ensemble: {}, inputs: {}x{}".format(
            model, mode, country, buysell, ensemble, *ary.shape))
        app.logger.info("modelname: {}".format(modelname))
        
        outputs = torch_predict(modelname, mode, country, ary, buysell, ensemble)
        
        return ary2str(outputs)

    except Exception as ex:
        req_error(str(ex))

def get_model(mpath, country, ctag, model):
    if ctag:
        return "{}/{}/Model{}{}.mdl".format(mpath, country, ctag, model[-6:])
    else:
        return "{}/{}/{}.mdl".format(mpath, country, model)

if __name__ == "__main__":
    app.logger.info("start service")
    app.run(host='0.0.0.0', port=5800, use_reloader=False, threaded=False)

