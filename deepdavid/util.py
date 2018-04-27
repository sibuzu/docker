from flask import Flask, render_template,request
from werkzeug.exceptions import BadRequest
import numpy as np
import logging
from io import StringIO

logger = logging.getLogger('deepdavid')

#decoding an image from base64 into raw representation
def str2ary(inputs):
    ary = np.loadtxt(StringIO(inputs), delimiter=',')
    return ary

def ary2str(ary):
    logger.info("result: {}".format(ary.shape))
    return ','.join([str(x) for x in list(ary.astype(int))])

def req_error(msg):
    logger.error(msg)
    raise BadRequest(msg)
 
