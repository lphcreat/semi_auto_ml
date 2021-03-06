# add a unsupervise model for check the outlier
from sklearn.svm import OneClassSVM
import pandas as pd
import numpy as np
from semi_auto_ml.utils.extract_funcs import get_IQR,string_index
from sklearn.base import BaseEstimator, ClassifierMixin,TransformerMixin

class OutlineCheck():
    '''
    check outline rows by sk outliner model
    '''

    def __init__(self,clf=None,**kwargs):
        '''
        default use OneClassSVM,or you can use sk outliner model(IsolationForest/LocalOutlierFactor)
        '''
        if clf is None:
            self.clf = OneClassSVM(**kwargs)
        else:
            self.clf = clf(**kwargs)
    
    def get_detail(self,X:pd.DataFrame):
        pre_result = self.clf.fit_predict(X)
        inliers = X[pre_result==1]
        return self.clf,inliers
    
    @staticmethod
    def get_predict_detail(clf,X):
        '''
        Params:
        clf:the model by get_detail return
        X:the input data for check
        '''
        pre = clf.predict(X)
        if X.shape[0]>1:
            return X[pre==1]
        else:
            return pre[0]

class IQRCheck(BaseEstimator, ClassifierMixin):
    '''
    check outline rows by IQR
    Returns -1 for outliers and 1 for inliers.
    you can use it by OutlineCheck.
    Notes:
    -------
    the data type is dataframe 
    '''

    def __init__(self,k=2):
        self.k = k
        self.iqr = None
    
    def fit(self,X:pd.DataFrame,iqr=None):
        '''
        you can fit by train data and self define some cols boundary:
           lower_bound  upper_bound  
        col1  -1.9  2.0  
        col2  -2.1  1.8  
        col3  trained  trained    
        Params
        -----------
        X:train data
        iqr:self define boundary
        '''
        if iqr is None:
            self.iqr=get_IQR(X,self.k)
        else:
            self.iqr = pd.concat([self.iqr,iqr])
            self.iqr = self.iqr[~self.iqr.index.duplicated(keep='last')]
        return self

    def predict(self,X:pd.DataFrame):
        outlie_label = (X < self.iqr['lower_bound']).any(axis=1)|(X > self.iqr['upper_bound']).any(axis=1)
        pre_label = (~outlie_label).map({True:1,False:-1})
        return pre_label

    def fit_predict(self,X:pd.DataFrame,iqr=None):
        if iqr is None:
            return self.fit(X).predict(X)
        else:
            return self.fit(X,iqr=iqr).predict(X)

class TransCat(BaseEstimator, TransformerMixin):
    '''
    transforme category to num by frequency,if the category percentage is small than threshold will join with a new one
    in predicate processing you can check category.if you want you can add one-hot in next preprocessing.
    '''
    def __init__(self,threshold=0.05,cols = None):
        '''
        threshold : the joined categories percentage
        cols : need convert cols by list
        '''
        self.threshold = threshold
        self.map_dict = {}
        self.cols = cols

    def fit(self,X:pd.DataFrame):
        if self.cols is None:
            self.cols = X.columns
        self.map_dict = {k:string_index(X[k],self.threshold) for k in self.cols}
        return self

    def transform(self,X:pd.DataFrame):
        '''
        if the category not in train data will convert to nan
        '''
        for item in self.cols:
            X[item] = X[item].map(self.map_dict[item])
        return X

    def fit_transform(self,X:pd.DataFrame):
        return self.fit(X).transform(X)

class PackageRules(BaseEstimator, TransformerMixin):
    '''
    Returns -1 for forbidden and 1 for normal.
    combine rules as a sklearn model,only map on num/category features,you can define the forbidden rules.
    RULES EXAMPLE：
    --------------
    {'f1':{'ftype':'num','fb_rule':[num1,num2]},'f2':{'ftype':'num','fb_rule':[num1,float('inf')]},
    'f3':{'ftype':'cat','fb_rule':['c1','c2']},'f4':{'ftype':'num','fb_rule':[float('-inf'),num1]}}
    '''
    def __init__(self,rules_dict):
        self.rules_dict=rules_dict

    @staticmethod
    def parse_rule(rule_dict,value):
        '''
        1.to num features: check the feature not in the forbidden num.
        2.to category features: check the feature not in the forbidden categories.
        '''
        rule_type=rule_dict.get('ftype','unkown')
        rule = rule_dict.get('fb_rule',None)
        if rule is not None:
            if rule_type=='num':
                min_data,max_data=min(rule),max(rule)
                return (min_data<=value<=max_data)
            elif rule_type=='cat':
                return ~(value in rule)
            else:
                raise ValueError("you must define the feature type with num/cat")
        else:
            raise ValueError("you must define the rule")

    def fit(self,new_rules_dict):
        '''
        update rules_dict
        '''
        self.rules_dict.update(new_rules_dict)
        return self

    def predict(self,X:pd.DataFrame):
        result = []
        for k,rule_dict in self.rules_dict.items():
            x_check = X[k].apply(lambda x:PackageRules.parse_rule(rule_dict,x))
            result.append(x_check)
        predict_label = pd.concat(result,axis=1).all(axis=1).map({True:1,False:-1})
        return predict_label
    
    def fit_predict(self,X,rules):
        return self.fit(rules).predict(X)
