"""

Train the whole set of test on the "lstm wins" synthetic dataset
 

"""

import numpy as np
from numpy import inf
from sklearn.ensemble import RandomForestClassifier
from HMM.hmm_classifier import HMMClassifier
from LSTM.lstm_classifier import LSTMClassifier 

# general parameters
nfolds = 5
nestimators = 300
nhmmstates = 3
nhmmiter = 10
hmmcovtype = "full"  # options: full, diag, spherical
lstmsize = 2000
lstmdropout = 0.5
lstmoptim = 'adagrad'
lstmnepochs = 20
lstmbatchsize = 64

#
# Load the dataset
#
print 'Loading the dataset..'
static_train = np.load('/storage/hpc_anna/GMiC/Data/BPIChallenge/f1/preprocessed/train_static.npy')
dynamic_train = np.load('/storage/hpc_anna/GMiC/Data/BPIChallenge/f1/preprocessed/train_dynamic.npy')
static_val = np.load('/storage/hpc_anna/GMiC/Data/BPIChallenge/f1/preprocessed/test_static.npy')
dynamic_val = np.load('/storage/hpc_anna/GMiC/Data/BPIChallenge/f1/preprocessed/test_dynamic.npy')
labels_train = np.load('/storage/hpc_anna/GMiC/Data/BPIChallenge/f1/preprocessed/train_labels.npy')
labels_val = np.load('/storage/hpc_anna/GMiC/Data/BPIChallenge/f1/preprocessed/test_labels.npy')


#
# Merge train and test
#
print "Combining data from train and test for CV predictions..."
static_all = np.concatenate((static_train, static_val), axis=0)
dynamic_all = np.concatenate((dynamic_train, dynamic_val), axis=0)
labels_all = np.concatenate((labels_train, labels_val), axis=0)
nsamples = static_all.shape[0]


#
# k-fold CV
#

# prepare where to store the predictions
predictions_all_rf = np.empty((len(labels_all), 2))
predictions_all_hmm = np.empty((len(labels_all), 2))
predictions_all_lstm = np.empty((len(labels_all), 2))

# prepare where to store the ratios
ratios_all_hmm = np.empty(len(labels_all))
ratios_all_lstm = np.empty(len(labels_all))

# split indices into folds
predict_idx_list = np.array_split(range(nsamples), nfolds)

# run CV
for fid, predict_idx in enumerate(predict_idx_list):
    print "Current fold is %d" % fid
    train_idx = list(set(range(nsamples)) - set(predict_idx))
    
    # extract predictions using RF on static
    print "    Extracting predictions on static data with RF..."
    rf = RandomForestClassifier(n_estimators=nestimators)
    rf.fit(static_all[train_idx], labels_all[train_idx])
    predictions_all_rf[predict_idx] = rf.predict_log_proba(static_all[predict_idx])
    predictions_all_rf[predictions_all_rf == -inf] = np.min(predictions_all_rf[predictions_all_rf != -inf])

    # extract predictions using HMM on dynamic
    print "    Extracting predictions on dynamic data with HMM..."
    hmmcl = HMMClassifier()
    model_pos, model_neg = hmmcl.train(nhmmstates, nhmmiter, hmmcovtype, 
                                       dynamic_all[train_idx], labels_all[train_idx])
    predictions_all_hmm[predict_idx] = hmmcl.predict_log_proba(model_pos, model_neg, dynamic_all[predict_idx])
    ratios_all_hmm[predict_idx] = hmmcl.pos_neg_ratios(model_pos, model_neg, dynamic_all[predict_idx])

    # extract predictions using LSTM on dynamic
    print "    Extracting predictions on dynamic data with LSTM..."
    lstmcl = LSTMClassifier(lstmsize, lstmdropout, lstmoptim, lstmnepochs, lstmbatchsize)
    model_pos, model_neg = lstmcl.train(dynamic_all[train_idx], labels_all[train_idx])
    mse_pos, mse_neg = lstmcl.predict_mse(model_pos, model_neg, dynamic_all[predict_idx]) 
    predictions_all_lstm[predict_idx] = np.vstack((mse_pos, mse_neg)).T
    ratios_all_lstm[predict_idx] = lstmcl.pos_neg_ratios(model_pos, model_neg, dynamic_all[predict_idx])


#
# Prepare combined datasets for the future experiments
#

# datasets for ensemble learning
predictions_combined_rf_hmm = np.concatenate((predictions_all_rf, predictions_all_hmm), axis=1)
predictions_combined_rf_lstm = np.concatenate((predictions_all_rf, predictions_all_lstm), axis=1)

# datasets for hybrid learning
enriched_by_hmm = np.concatenate((static_all, np.matrix(ratios_all_hmm).T), axis=1)
enriched_by_lstm = np.concatenate((static_all, np.matrix(ratios_all_lstm).T), axis=1)

# dataset to confirm that RF on dynamic is not better than generative models on dynamic data
dynamic_as_static = dynamic_all.reshape((dynamic_all.shape[0], dynamic_all.shape[1] * dynamic_all.shape[2]))

# dataset to confirm that RF on naive combination of features is not better than our fancy models
static_and_dynamic_as_static = np.concatenate((static_all, dynamic_as_static), axis=1)

# dataset to check how generative models perform if provided with static features along with dynamic
static_as_dynamic = np.zeros((static_all.shape[0], static_all.shape[1], dynamic_all.shape[2]))
for i in range(static_all.shape[0]):
    static_as_dynamic[i, :, :] = np.tile(static_all[i, :], (dynamic_all.shape[2], 1)).T
dynamic_and_static_as_dynamic = np.concatenate((dynamic_all, static_as_dynamic + np.random.uniform(-0.0001, 0.0001, static_as_dynamic.shape)), axis=1)


#
# Split the data into training and test
#
train_idx = np.random.choice(range(0, nsamples), size=np.round(nsamples * 0.7, 0), replace=False)
test_idx = list(set(range(0, nsamples)) - set(train_idx))


#
# Train the models and report their performance
#

# Ensemble on predictions by RF and HMM (1)
rf = RandomForestClassifier(n_estimators=nestimators)
rf.fit(predictions_combined_rf_hmm[train_idx], labels_all[train_idx])
print "===> (1) Ensemble (RF) on predictions by RF and HMM: %.4f" % rf.score(predictions_combined_rf_hmm[test_idx], labels_all[test_idx])

# Ensemble on predictions by RF and LSTM (2)
rf = RandomForestClassifier(n_estimators=nestimators)
rf.fit(predictions_combined_rf_lstm[train_idx], labels_all[train_idx])
print "===> (2) Ensemble (RF) on predictions by RF and LSTM: %.4f" % rf.score(predictions_combined_rf_lstm[test_idx], labels_all[test_idx])

# Hybrid on features enriched by HMM (3)
rf = RandomForestClassifier(n_estimators=nestimators)
rf.fit(enriched_by_hmm[train_idx], labels_all[train_idx])
print "===> (3) Hybrid (RF) on features enriched by HMM: %.4f" % rf.score(enriched_by_hmm[test_idx], labels_all[test_idx])

# Hybrid on features enriched by LSTM (4)
rf = RandomForestClassifier(n_estimators=nestimators)
rf.fit(enriched_by_lstm[train_idx], labels_all[train_idx])
print "===> (4) Hybrid (RF) on features enriched by LSTM: %.4f" % rf.score(enriched_by_lstm[test_idx], labels_all[test_idx])

# RF on static features (5)
rf = RandomForestClassifier(n_estimators=nestimators)
rf.fit(static_all[train_idx], labels_all[train_idx])
print "===> (5) RF on static features: %.4f" % rf.score(static_all[test_idx], labels_all[test_idx])

# RF on dynamic features (6)
rf = RandomForestClassifier(n_estimators=nestimators)
rf.fit(dynamic_as_static[train_idx], labels_all[train_idx])
print "===> (6) RF on dynamic (spatialized) features: %.4f" % rf.score(dynamic_as_static[test_idx], labels_all[test_idx])

# HMM on dynamic features (7)
hmmcl = HMMClassifier()
model_pos, model_neg = hmmcl.train(nhmmstates, nhmmiter, hmmcovtype, dynamic_all[train_idx], labels_all[train_idx])
print "===> (7) HMM on dynamic features: %.4f" % hmmcl.test(model_pos, model_neg, dynamic_all[test_idx], labels_all[test_idx])

# LSTM on dynamic features (8)
lstmcl = LSTMClassifier(lstmsize, lstmdropout, lstmoptim, lstmnepochs, lstmbatchsize)
model_pos, model_neg = lstmcl.train(dynamic_all[train_idx], labels_all[train_idx])
print "===> (8) LSTM on dynamic features: %.4f" % lstmcl.test(model_pos, model_neg, dynamic_all[test_idx], labels_all[test_idx])

# HMM on dynamic and static (turned into fake sequences) (9)
hmmcl = HMMClassifier()
model_pos, model_neg = hmmcl.train(nhmmstates, nhmmiter, hmmcovtype, dynamic_and_static_as_dynamic[train_idx], labels_all[train_idx])
print "===> (9) HMM on dynamic and static features: %.4f" % hmmcl.test(model_pos, model_neg, dynamic_and_static_as_dynamic[test_idx], labels_all[test_idx])

# LSTM on dynamic and static (turned into fake sequences) (10)
lstmcl = LSTMClassifier(lstmsize, lstmdropout, lstmoptim, lstmnepochs, lstmbatchsize)
model_pos, model_neg = lstmcl.train(dynamic_and_static_as_dynamic[train_idx], labels_all[train_idx])
print "===> (10) LSTM on dynamic features: %.4f" % lstmcl.test(model_pos, model_neg, dynamic_and_static_as_dynamic[test_idx], labels_all[test_idx])

# RF on static and dynamic (spatialized) features (11)
rf = RandomForestClassifier(n_estimators=nestimators)
rf.fit(static_and_dynamic_as_static[train_idx], labels_all[train_idx])
print "===> (11) RF on dynamic (spatialized) features: %.4f" % rf.score(static_and_dynamic_as_static[test_idx], labels_all[test_idx])



