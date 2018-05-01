import numpy as np
from keras.models import load_model
import tensorflow as tf
import logging
import os

from util import *

logger = logging.getLogger('deepdavid')

global MODELS
MODELS = {}

# modelname: "Bull", "Bear"
# model inputs (17 parameters)
# ['權證','台50','中100','小型股','上櫃','區間N','漲跌7%','T1開盤比','RB1','RB2','RB3','UD1','UD2','UD3','VOL1','VOL2','VOL3']

def init_gpu():
    logger.info("set gpu bound")
    # prevent tensorflow to use all gpu memory
    # config = tf.ConfigProto()
    # config.gpu_options.allow_growth = True
    gpu_options=tf.GPUOptions(per_process_gpu_memory_fraction=0.03)
    config=tf.ConfigProto(gpu_options=gpu_options)
    tf.Session(config=config)

def loadmodel(modelname):
    if modelname in MODELS:
        return MODELS[modelname]
    fname = "ModelDavid{}.h5".format(modelname)
    if os.path.isfile(fname):
        MODELS[modelname] = load_model(fname)
        logger.info("model {} loaded".format(fname))
        return MODELS[modelname]
    else:
        req_error("Cannot load model " + fname)

def expand(X):
    N = 161
    exary = np.linspace(-0.8, 0.8, N)
    rows = X.shape[0]
    X = np.repeat(X, N, axis=0)
    X[:, 7] = np.tile(exary, rows)
    # print(X[:N, 7])
    return X

def predict(modelname, mode, X):
    if mode=='candidate':
        X = expand(X)
    model = loadmodel(modelname)
    Y = model.predict(X, batch_size=8192)
    y = np.where((Y>0.5).flatten(), 1, 0)
    return y