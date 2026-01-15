***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED*** XGBoost Classification in Python

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 1. Ensure you are using or create a cluster specifying Databricks Runtime Version as **Databricks Runtime 5.4 ML or above**. In Databricks Runtime, you need to install XGBoost by running **Cmd 3**.
***REMOVED*** MAGIC 2. Attach this notebook to the cluster.

***REMOVED*** COMMAND ----------

dbutils.library.installPyPI("xgboost", version="0.90" )

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Prepare data

***REMOVED*** COMMAND ----------

import pandas as pd
import xgboost as xgb

***REMOVED*** COMMAND ----------

raw_input = pd.read_csv("/dbfs/databricks-datasets/Rdatasets/data-001/csv/datasets/iris.csv",
                        header = 0,
                       names=["item","sepal length","sepal width", "petal length", "petal width","class"])
new_input = raw_input.drop(columns=["item"])
new_input["class"] = new_input["class"].astype('category')
new_input["classIndex"] = new_input["class"].cat.codes
print(new_input)

***REMOVED*** COMMAND ----------

from sklearn.model_selection import train_test_split
***REMOVED*** Split to train/test
training_df, test_df = train_test_split(new_input)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Train XGBoost Model with Pandas DataFrames

***REMOVED*** COMMAND ----------

dtrain = xgb.DMatrix(training_df[["sepal length","sepal width", "petal length", "petal width"]], label=training_df["classIndex"])

***REMOVED*** COMMAND ----------

param = {'max_depth': 2, 'eta': 1, 'silent': 1, 'objective': 'multi:softmax'}
param['nthread'] = 4
param['eval_metric'] = 'auc'
param['num_class'] = 6

***REMOVED*** COMMAND ----------

num_round = 10
bst = xgb.train(param, dtrain, num_round)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Prediction

***REMOVED*** COMMAND ----------

dtest = xgb.DMatrix(test_df[["sepal length","sepal width", "petal length", "petal width"]])
ypred = bst.predict(dtest)

***REMOVED*** COMMAND ----------

from sklearn.metrics import precision_score

pre_score = precision_score(test_df["classIndex"],ypred, average='micro')

print("xgb_pre_score:",pre_score)