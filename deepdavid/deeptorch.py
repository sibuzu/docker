import numpy as np
import logging
import os
import glob

from util import *

# pyporch
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.utils.data as Data

use_cuda = True
use_cuda = use_cuda and torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")
kwargs = {'num_workers': 2, 'pin_memory': True} if use_cuda else {}

logger = logging.getLogger('deepdavid')

global _model, _modelname
_model = None
_modelname = ""
_tmpmodelname = ""

# modelname: "Bull", "Bear"
# model inputs (17 parameters)
# ['權證','台50','中100','小型股','上櫃','區間N','漲跌7%','T1開盤比','RB1','RB2','RB3','UD1','UD2','UD3','VOL1','VOL2','VOL3']

class BasicBlock(nn.Module):
    def __init__(self, N):
        super(BasicBlock, self).__init__()
        self.block = nn.Sequential(
            nn.Linear(N, N),
            nn.BatchNorm1d(N),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(N, N),
            nn.BatchNorm1d(N),      
        )
        
    def forward(self, x):
        out = self.block(x)
        out += x
        return out

class Net(nn.Module):
    def __init__(self, N):
        super(Net, self).__init__()

        N2 = N // 2
        self.net = nn.Sequential(
            nn.Linear(17, N2),
            nn.ReLU(),
            nn.BatchNorm1d(N2),
            nn.Dropout(0.5),
            nn.Linear(N2, N),
            nn.BatchNorm1d(N),
            BasicBlock(N),
            BasicBlock(N),
            BasicBlock(N),
            BasicBlock(N),
            nn.Linear(N, N2),
            nn.ReLU(),
            nn.BatchNorm1d(N2),
            nn.Linear(N2, 2),
        )
        self.optimizer = optim.Adam(self.parameters())
        self.loss = None
        
    def forward(self, x):
        return self.net(x)

def init_torch():
    global _model
    logger.info("setup device {}, {}".format(device, kwargs))
    if _model is None:
        _model = Net(64).to(device)

def loadmodel(modelname):
    global _model, _modelname, _tmpmodelname
    if _modelname == modelname:
        return _model

    if os.path.isfile(modelname):
        _model.load_state_dict(torch.load(modelname))
        _modelname = modelname
        _tmpmodelname = ""
        logger.info("model {} loaded".format(modelname))
        return _model
    else:
        # try to local last model
        tmp = modelname[:-9] + "*" + ".mdl"
        files = sorted(glob.glob(tmp))
        if len(files) == 0:
            req_error("Cannot load model " + modelname)
        tmpmodelname = files[-1]

        # tmp model (last model) has been loaded
        if tmpmodelname == _tmpmodelname:
            return _model

        # load the last model
        _model.load_state_dict(torch.load(tmpmodelname))
        _modelname = ""
        _tmpmodelname = tmpmodelname
        msg = "cannot load model {}, use {} instead".format(modelname, tmpmodelname)
        logger.info(msg)
        print(msg)
        return _model

def expand(X, N):
    exary = np.linspace(-0.8, 0.8, N)
    rows = X.shape[0]
    X = np.repeat(X, N, axis=0)
    X[:, 7] = np.tile(exary, rows)
    # print(X[:N, 7])
    return X

def ModifiedName(modelname, ensemble):
    return modelname[:-10] + ensemble + modelname[-10:]

def torch_predict(modelname, mode, X, buysell, ensemble):
    n = len(ensemble)
    if n == 1:  ## 'A', 'B', 'C'
        name1 = ModifiedName(modelname, ensemble)
        predict =  torch_predict_kern(name1, mode, X, buysell)
    elif n == 3: ## 'A+B', 'AxB'
        name1 = ModifiedName(modelname, ensemble[0])
        name2 = ModifiedName(modelname, ensemble[2])
        predict1 =  torch_predict_kern(name1, mode, X, buysell)
        predict2 =  torch_predict_kern(name2, mode, X, buysell)
        predict = predict1 + predict2
        if ensemble[1] == '+':
            predict = np.where(predict>=1, 1, 0)
        else:
            predict = np.where(predict==2, 1, 0)
    elif n == 4: ## 'G5#1', 'G5#2', 'G7#1', ...
        group = int(ensemble[1])
        glist = [chr(i) for i in range(ord('A'),ord('A')+group)]
        thresh = int(ensemble[3])
        predict = 0
        for tag in glist:
            name = ModifiedName(modelname, tag)
            px = torch_predict_kern(name, mode, X, buysell)
            predict = predict + px
        predict = np.where(predict>=thresh, 1, 0)
    elif n == 5: ## 'A+B+C', 'AxBxC', 'A#B#C'
        name1 = ModifiedName(modelname, ensemble[0])
        name2 = ModifiedName(modelname, ensemble[2])
        name3 = ModifiedName(modelname, ensemble[4])
        predict1 =  torch_predict_kern(name1, mode, X, buysell)
        predict2 =  torch_predict_kern(name2, mode, X, buysell)
        predict3 =  torch_predict_kern(name3, mode, X, buysell)
        predict = predict1 + predict2 + predict3
        if ensemble[1] == '+':
            predict = np.where(predict>=1, 1, 0)
        elif ensemble[1] == 'x':
            predict = np.where(predict==3, 1, 0)
        elif ensemble[1] == '#':
            predict = np.where(predict>=2, 1, 0)
    else:
        req_error("invalid ensemble ({})".format(ensemble)) 

    return predict

def torch_predict_kern(modelname, mode, X, buysell):
    if mode=='candidate':
        X = expand(X, 161)
    elif mode=='candidate2':
        X = expand(X, 1601)
    
    print("modelname", modelname)
    model = loadmodel(modelname)
    
    model.eval()
    with torch.no_grad():
        testX = torch.from_numpy(X).float().to(device)
        predict = model(testX).cpu()
    predict = np.where(predict > 0, 1, 0)
    y = predict[:,0] + predict[:,1] * 2
    y[y>2] = 0
    if buysell=="bull":
        y = np.where(y==1, 1, 0)
    else:
        y = np.where(y==2, 1, 0)
    return y
