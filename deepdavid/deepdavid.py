import numpy as np
from keras.models import load_model
import tensorflow as tf
import logging

logger = logging.getLogger('deepdavid')

MODEL_BULL = "ModelDavidBull.h5"
MODEL_BEAR = "ModelDavidBear.h5"

def init():
    logger.info("set gpu bound")
    # prevent tensorflow to use all gpu memory
    # config = tf.ConfigProto()
    # config.gpu_options.allow_growth = True
    gpu_options=tf.GPUOptions(per_process_gpu_memory_fraction=0.03)
    config=tf.ConfigProto(gpu_options=gpu_options)
    session = tf.Session(config=config)

    logger.info("loading model " + MODEL_BULL)
    modelBull = load_model(MODEL_BULL)
    logger.info("loading model " + MODEL_BEAR)
    modelBear = load_model(MODEL_BEAR)
    modelBull.summary()
    modelBear.summary()
    logger.info("models loaded")

    return modelBull, modelBear

def predict(model, X):
    y = np.round(model.predict(X).flatten())
    return y
