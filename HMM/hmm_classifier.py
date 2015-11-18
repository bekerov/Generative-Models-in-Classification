# -*- coding: utf-8 -*-
"""
handles functions required for hmm classification
"""

import numpy as np
from hmmlearn import hmm
from scipy.stats import mode
from DataNexus.datahandler import DataHandler

class HMMClassifier:
    
    # tensor to list (for HMM input)
    def tensor_to_list(self, tensor):
        """
        from [SUBJECTS, TIME, FEATURES] to   
        list[SUBJECT] = matrix[TIME, FEATURES]
        """
  
        lst = []
        for i in range(0, tensor.shape[0]):
            lst.append(tensor[i, :, :].T)
        return lst
        
    # building Maximum likelihood classifier
    def ispositive(self, instance, model_pos, model_neg):
        return model_pos.score(instance) >= model_neg.score(instance)

    def accuracy(self, data, labels, model_pos, model_neg, show_prediction=False):
        pred = []
        for i in range(len(data)):
            pred.append(int(self.ispositive(data[i], model_pos, model_neg)))
        acc = float(sum(pred == labels))/float(len(pred))
        if show_prediction == True:
            return acc, pred
        else:
            return acc
   
    def accuracy_per_feature(self, data, labels, models_pos, models_neg):
        
        # variables for convenience
        nsamples = data.shape[0]
        nseqfeatures = data.shape[1]
        seqlen = data.shape[2]

        # compute predictions for each model pair
        votes = np.zeros((nseqfeatures, nsamples))
        for fid in range(nseqfeatures):
            fdata = data[:, fid, :].reshape((nsamples, 1, seqlen))
            fdata = self.tensor_to_list(fdata)
            accuracy, predictions = self.accuracy(fdata, labels, models_pos[fid], models_neg[fid], True)
            print '  Accuracy with feature %d is %.4f' % (fid, accuracy)
            votes[fid, :] = predictions

        # for each sample take the majority vote
        preds = mode(votes, axis=0)[0][0]

        # compute accuracy of the majority voted predictions
        accuracy = np.sum(preds == labels) / float(len(labels))

        return accuracy
 
    def find_best_parameter(self, ratio, hdn_nstates_list, niter, nrepetitions, data, labels):
        """
        parameter search over number of hidden states
        @param hdn_nstates_list: list of number of hidden states to try, e.g. range(2,10)
        @param ratio: ratio of the dataset split for train, e.g. 0.7
        @param niter: number of iterations for hmm model to perform, e.g. 10
        @param nrepetitions: number of repeated runs for the same hidden state, but for the different split, e.g. 5
        """
        accuracy_results = {}
        for nstates in hdn_nstates_list:
            print 'state' + str(nstates)
            accuracy_results[nstates] = []
            for run in range(nrepetitions):
                print 'repetition' + ' ' + str(run) 
                
                # make new random split  
                train_data, train_labels, val_data, val_labels = DataHandler.split(ratio, data, labels)
                
                # train a model on this split
                model_pos, model_neg = self.train(nstates, niter, train_data, train_labels)
                
                # test the model and store the results
                acc = self.test(model_pos, model_neg, val_data, val_labels)
                print nstates, acc
                accuracy_results[nstates].append(acc)

        with open("../../Results/crossvalidated_accuracy.txt","w") as f:
            for nstates in hdn_nstates_list:
                print nstates, np.mean(accuracy_results[nstates]), np.std(accuracy_results[nstates])
                f.write("%d, %s\n" % (nstates, ", ".join([str(x) for x in accuracy_results[nstates]])))
    
    def train(self, nstates, niter, covtype, data, labels):
        train_pos = self.tensor_to_list(data[labels==1, :, :])
        train_neg = self.tensor_to_list(data[labels==0, :, :])
        print "Start training the positive model..."
        model_pos = hmm.GaussianHMM(nstates, covariance_type=covtype, n_iter=niter)
        model_pos.fit(train_pos)
        print "Start training the negative model..."
        model_neg = hmm.GaussianHMM(nstates, covariance_type=covtype, n_iter=niter)
        model_neg.fit(train_neg)
        return model_pos, model_neg

    def test(self, model_pos, model_neg, data, labels):
        test = self.tensor_to_list(data)
        return self.accuracy(test, labels, model_pos, model_neg)

    def pos_neg_ratios(self, model_pos, model_neg, data):
        data = self.tensor_to_list(data)
        # find log-likelihood of positive model for a new sequence and the same for a negative one, substract
        ratios = np.empty(len(data))
        for i in range(len(data)):
            ratios[i] = model_pos.score(data[i]) - model_neg.score(data[i])
        return ratios

    def predict_log_proba(self, model_pos, model_neg, data):
        """
        Return class log-probabilities of each sample in the data
        """
        data = self.tensor_to_list(data)
        probs = np.empty((len(data), 2))
        for i in range(len(data)):
            probs[i, :] = (model_pos.score(data[i]), model_neg.score(data[i]))
        return probs


    def train_per_feature(self, nstates, niter, data, labels):
        
        # variables for convenience
        nsamples = data.shape[0]
        nseqfeatures = data.shape[1]
        seqlen = data.shape[2]

        # train a pair of models for each sequential feature
        models_pos = [None] * nseqfeatures
        models_neg = [None] * nseqfeatures
        for fid in range(nseqfeatures):
            print 'Training pair of models for feature %d/%d...' % (fid, nseqfeatures)
            fdata = data[:, fid, :].reshape((nsamples, 1, seqlen))
            model_pos, model_neg = self.train(nstates, niter, fdata, labels)
            models_pos[fid] = model_pos
            models_neg[fid] = model_neg

        return models_pos, models_neg
 
    def test_per_feature(self, models_pos, models_neg, data, labels):
        return self.accuracy_per_feature(data, labels, models_pos, models_neg)

    def pos_neg_ratios_per_feature(models_pos, models_neg, data):
        
        # variables for convenience
        nsamples = data.shape[0]
        nseqfeatures = data.shape[1]
        seqlen = data.shape[2]

        # extract ratios for each feature
        ratios = np.zeros(nseqfeatures, nsamples)
        for fid in range(nseqfeatures):
            ratios[fid, :] = self.pos_neg_ratios(models_pos[fid], models_neg[fid], data[:, fid, :].reshape((nsamples, 1, seqlen)))

        return ratios

if __name__ == '__main__':
    
    print("Reading data...")
    
    # Uncomment to train on the whole dataset
    train_data = np.load("/storage/hpc_anna/GMiC/Data/ECoG/preprocessed/train_data.npy")
    train_labels = np.load("/storage/hpc_anna/GMiC/Data/ECoG/preprocessed/train_labels.npy")
    test_data = np.load("/storage/hpc_anna/GMiC/Data/ECoG/preprocessed/test_data.npy")
    test_labels = np.load("/storage/hpc_anna/GMiC/Data/ECoG/preprocessed/test_labels.npy")
    
    # Uncomment to train on the second half and test on a second 
    #all_train_data = np.load("/storage/hpc_anna/GMiC/Data/ECoG/preprocessed/train_data.npy")
    #all_train_labels = np.load("/storage/hpc_anna/GMiC/Data/ECoG/preprocessed/train_labels.npy")
    #print("Splitting data into two halves...")
    #train_data, train_labels, test_data, test_labels = DataHandler.split(0.5, all_train_data, all_train_labels)    

    hmmcl = HMMClassifier()
    model_pos, model_neg = hmmcl.train(70, 5, train_data, train_labels)
    print hmmcl.test(model_pos, model_neg, test_data, test_labels)
    #hmmcl.find_best_parameter(0.7, range(20,31), 10, 5, train_data, train_labels)

