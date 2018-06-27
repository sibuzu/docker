from flask import Flask, render_template, request
from werkzeug.exceptions import BadRequest
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
import sys

# local modules
from deepdavid import init_gpu, predict
from deeptorch import init_torch, torch_predict
from util import *

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
init_gpu()
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
        mode = contents.get("mode")
        model = contents.get("model")
        inputs = contents.get("inputs")
        country = contents.get("country")
        buysell = contents.get("buysell")
        pytorch = contents.get("pytorch")
        ensemble = contents.get("ensemble", "A")
        
        pytorch = int(pytorch) if pytorch else 0

        if not model:
            req_error('no model paramters')
        if not mode:
            req_error('no mode parameters')
        if not inputs:
            req_error('no inputs parameters')
        
        ary = str2ary(inputs)

        if not country:
            # old request
            modelname = "ModelDavid{}.h5".format(model)
        else:
            # new request
            if country=="tw":
                ctag = "T"
            elif country=="jp":
                ctag = "J"
            elif country=="us":
                ctag = "A"
            else:
                assert "invalid country: " + country
            bs = "Bull" if buysell=="bull" else "Bear"

            if pytorch:
                mpath = "/dvol/deepmodels/pytorch"
                modelname = "{}/{}/Model{}{}.mdl".format(mpath, country, ctag, model[-6:])
            else:
                mpath = "/dvol/deepmodels"
                modelname = "{}/{}/Model{}{}{}.h5".format(mpath, country, ctag, bs, model[-6:])

        app.logger.info("model: {}, mode: {}, country: {}, pytorch: {}, buysell: {}, ensemble: {}, inputs: {}x{}".format(
            model, mode, country, pytorch, buysell, ensemble, *ary.shape))
        app.logger.info("modelname: {}".format(modelname))
        if pytorch:
            outputs = torch_predict(modelname, mode, ary, buysell, ensemble)
        else:
            outputs = predict(modelname, mode, ary)
        
        return ary2str(outputs)

    except Exception as ex:
        req_error(str(ex))

if __name__ == "__main__":
    app.logger.info("start service")
    app.run(host='0.0.0.0', port=5800, use_reloader=False)

