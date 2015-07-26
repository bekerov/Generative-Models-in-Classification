# -*- coding: utf-8 -*-
"""
Created on Wed Jul 22 17:58:39 2015

@author: annaleontjeva
"""

import numpy as np
from hmmlearn import hmm
import random as rm
import pylab as pl
import matplotlib.pyplot as plt

# load the data
raw_data = np.loadtxt('../../Data/ECoG/Competition_train_cnt_scaled.txt')
trainval_data = np.reshape(raw_data, (278, 64, 3000))
trainval_labels = np.loadtxt('../../Data/ECoG/Competition_train_lab_onezero.txt')

def class_division(data, labels):
    pos = data[labels==1, :, :]
    neg = data[labels==0, :, :]
    return pos, neg
    
# tensor to list (for HMM input)
def tensor_to_list(tensor):
    """
    from [SUBJECTS, TIME, FEATURES] to   
    list[SUBJECT] = matrix[TIME, FEATURES]
    """    
    lst = []
    for i in range(0, tensor.shape[0]):
        lst.append(tensor[i, :, :].T)
    return lst
    
def random_split(data, labels, ratio=0.5):
    idx_train = np.random.choice(range(0, data.shape[0]), size=int(data.shape[0]*ratio), replace=False)
    idx_val = list(set(range(0, data.shape[0]))- set(idx_train))
    train_data = data[idx_train, :, :]
    train_labels = labels[idx_train]
    val_data = data[idx_val, :, :]
    val_labels = labels[idx_val]
    train_pos, train_neg = class_division(train_data, train_labels)    
    return tensor_to_list(train_pos), tensor_to_list(train_neg), tensor_to_list(val_data), val_labels
 
# Building Maximum likelihood classifier
def ispositive(model_pos, model_neg, instance):
    return model_pos.score(instance) >= model_neg.score(instance)

def accuracy(data, labels, model_pos, model_neg, show_prediction=False):
    pred = []
    for i in range(len(data)):
        pred.append(int(ispositive(model_pos, model_neg, data[i])))
    acc = float(sum(pred == labels))/float(len(pred))
    if show_prediction == True:
        return acc, pred
    else:
        return acc
        
# parameter search over number of hidden states
hidden_state_range = range(100,101)
accuracy_results = []
for nstates in hidden_state_range:    
    # make new random split    
    train_pos, train_neg, val_data, val_labels = random_split(data=trainval_data, labels=trainval_labels, ratio=0.7)
    model_pos = hmm.GaussianHMM(nstates, covariance_type="full", n_iter=10)        
    model_pos.fit(train_pos)
    model_neg = hmm.GaussianHMM(nstates, covariance_type="full", n_iter=10)
    model_neg.fit(train_neg)   
    # validation
    acc = accuracy(val_data, val_labels, model_pos, model_neg)
    print nstates, acc
    accuracy_results.append(acc)
   
best_state_number = hidden_state_range[np.argmax(accuracy_results)]
print "The best accuracy of %f achived with number of states %d" % (np.max(accuracy_results), best_state_number)

# Now use real test data
# model_pos = hmm.GaussianHMM(best_state_number, covariance_type="full", n_iter=1000)
# trainval_pos, trainval_neg, _, _ = random_split(trainval_data, trainval_labels, ratio=1.0)
# model_pos.fit(trainval_pos)
# model_neg = hmm.GaussianHMM(best_state_number, covariance_type="full", n_iter=1000)
# model_neg.fit(trainval_neg)

