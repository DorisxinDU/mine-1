import torch 
import torch.nn as nn 
import torch.optim as optim
import torch.nn.functional as F 

import numpy as np 
import argparse
import time, datetime
from tqdm import trange
import matplotlib.pyplot as plt 
import seaborn as sns
sns.set()

from sklearn.metrics import mutual_info_score

from misc.logger import Logger
from misc.utils import *


class Mine(nn.Module):
    def __init__(self, params):
        super(Mine, self).__init__()
        self.params = params['mine']
        self.fc1_x = nn.Linear(self.params['var1_size'], self.params['hidden'], bias=False)
        self.fc1_y = nn.Linear(self.params['var2_size'], self.params['hidden'], bias=False)
        self.fc1_bias = nn.Parameter(torch.zeros(self.params['hidden']))
        self.fc2 = nn.Linear(self.params['hidden'], self.params['hidden'])
        self.fc3 = nn.Linear(self.params['hidden'], self.params['oc'])

        self.ma_et = None

    def forward(self, x, y):
        x = self.fc1_x(x)
        y = self.fc2_y(y)

        out = F.leaky_relu(x + y + self.fc1_bias, negative_slope=2e-1)
        out = F.leaky_relu(self.fc2(out), negative_slope=2e-1)
        out = self.fc3(out)
        return out


def mutual_information(joint, marginal):
    mi_lb = torch.mean(joint) - torch.log(torch.mean(torch.exp(marginal)))
    return mi_lb


# data
var = 0.2
def func(x):
    return x

def gen_x():
    return np.sign(np.random.normal(0.,1.,[data_size,1]))

def gen_y(x):
    return func(x)+np.random.normal(0.,np.sqrt(var),[data_size,1])

def train(params):
    model.train()
    for epoch in range(params['epoch']):
        loss_dict = {}
        x_sample = torch.from_numpy(gen_x()).type(torch.FloatTensor)
        y_sample = torch.from_numpy(gen_y(x_sample.numpy())).type(torch.FloatTensor)
        y_shuffle = torch.from_numpy(np.random.permutation(y_sample.numpy())).type(torch.FloatTensor)

        if params['use_cuda']:
            x_sample = x_sample.cuda()
            y_sample = y_sample.cuda()
            y_shuffle = y_shuffle.cuda()

        optimizer.zero_grad()

        joint = model(x_sample, y_sample)
        marginal = model(x_sample, y_shuffle)

        mi = mutual_information(joint, marginal)
        loss = - mi  # Taking negative to maximize mutual information 
        loss.backward()
        optimizer.step()

        loss_dict = info_dict('mi_val', loss.item(), loss_dict)
        
        for tag, value in loss_dict.items():
            logger.scalar_summary(tag, value, epoch)

        print("MI value for epoch {} is {}.".format(epoch, loss.item()))


if __name__ == "__main__":
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%d_%m_%Y_%H_%M_%S')

    parser = argparse.ArgumentParser(description='mine')
    parser.add_argument('--config', type=str, default='./configs/mine.yml', 
                        help='Path to config file')
    opts = parser.parse_args()
    params = get_config(opts.config)
    print(params)

    model = Mine(params)
    if params['use_cuda']:
        model = model.cuda()

    if params['training'] == True and params['visualize'] == False:
        exp_logs = params['logs'] + params['exp_name'] + '_' + timestamp + '/'
        exp_results = params['results'] + params['exp_name'] + '_' + timestamp + '/'  
        mkdir_p(exp_logs)
        mkdir_p(exp_results)
        
        config_logfile = exp_logs + 'config.json'
        with open(config_logfile, 'w+') as cf:
            json.dump(params, cf)

        optimizer = optim.Adam(model.parameters(), lr=params['lr'])
        logger = Logger(exp_logs)

        train(params)