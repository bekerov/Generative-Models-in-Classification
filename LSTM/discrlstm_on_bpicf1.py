"""

Classifier based on generative LSTM applied to syn_lstm_wins

"""

import numpy as np
from LSTM.lstm_classifier import LSTMDiscriminative

# parameters
lstmsize = 300
fcsize = 100
dropout = 0.0
optim = 'adadelta'
nepochs = 30
batchsize = 512

# load the dataset
print 'Loading the dataset..'
static_train = np.load('/storage/hpc_anna/GMiC/Data/ECoGmixed/fourier/train_data.npy')
dynamic_train = np.load('/storage/hpc_anna/GMiC/Data/ECoGmixed/preprocessed/train_data.npy')
static_val = np.load('/storage/hpc_anna/GMiC/Data/ECoGmixed/fourier/test_data.npy')
dynamic_val = np.load('/storage/hpc_anna/GMiC/Data/ECoGmixed/preprocessed/test_data.npy')
labels_train = np.load('/storage/hpc_anna/GMiC/Data/ECoGmixed/preprocessed/train_labels.npy')
labels_val = np.load('/storage/hpc_anna/GMiC/Data/ECoGmixed/preprocessed/test_labels.npy')
nsamples = dynamic_train.shape[0]

# split the data into training and test
train_idx = np.random.choice(range(0, nsamples), size=np.round(nsamples * 0.7, 0), replace=False)
test_idx = list(set(range(0, nsamples)) - set(train_idx))

# train the model and report performance
lstmcl = LSTMDiscriminative(lstmsize, fcsize, dropout, optim, nepochs, batchsize)
model = lstmcl.train(dynamic_train[train_idx], labels_train[train_idx])
print 'Generative LSTM classifier on dynamic features: %.4f' % lstmcl.test(model, dynamic_train[test_idx], labels_train[test_idx])

