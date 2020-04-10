***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED******REMOVED***Building Dashboards with the MLflow Search API
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This notebook demonstrates how to use the [mlflow.search_runs](https://www.mlflow.org/docs/latest/search-syntax.html***REMOVED***programmatically-searching-runs) API to generate custom dashboards.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC The notebook contains the following sections:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Setup
***REMOVED*** MAGIC * Launch a Python 3 cluster running Databricks Runtime ML
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Mock Data Setup
***REMOVED*** MAGIC * Generate a mock MLflow experiment
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can skip this section if you'd like to generate dashboards from existing experiments.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Dashboards
***REMOVED*** MAGIC * Visualize changes in evaluation metrics over time
***REMOVED*** MAGIC * Track the number of runs kicked off by a particular user
***REMOVED*** MAGIC * Measure the total number of runs across all users

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Setup

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC 1. Ensure you are using or create a cluster specifying 
***REMOVED*** MAGIC   * **Databricks Runtime Version:** Any version of Databricks Runtime ML (e.g. Databricks Runtime 6.3 ML)
***REMOVED*** MAGIC   * **Python Version:** Python 3
***REMOVED*** MAGIC 1. Attach this notebook to the cluster.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED***Experiment Data

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md To plot summaries of existing experiment data, enter the ID of an existing experiment in the **Experiment ID** widget. Otherwise, the following cells generate and plot mock data.

***REMOVED*** COMMAND ----------

dbutils.widgets.text("Experiment ID", "")
dbutils.widgets.text("User", "")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Mock Data Setup

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC This section creates a mock experiment. To analyze your own experiment data rather than these mocks, change the value in the **Experiment ID** widget at the top of this notebook.

***REMOVED*** COMMAND ----------

from mlflow.tracking.client import MlflowClient

from datetime import datetime, timedelta
import math
import random

random.seed(42)
client = MlflowClient()

mock_experiment_file = f'/tmp/mock_experiment'
***REMOVED*** Delete experiment if it already exists
if client.get_experiment_by_name(mock_experiment_file):
  client.delete_experiment(client.get_experiment_by_name(mock_experiment_file).experiment_id)  
mock_experiment_id = client.create_experiment(mock_experiment_file)

def simulate_runs(dt, eid, mae, num_runs=1):
  '''
  Simulates a run(s) with a specified datetime, experiment, and mae.
  
  :param dt: Timestamp used for both run start_time and log_metric time.
  :param eid: Experiment id to log this run under.
  :param mae: Mean absolute error metric to log.
  :param num_runs: Number of runs to store.
  
  '''
  ts = int(dt.timestamp()*1000)
  for _ in range(num_runs):
    run = client.create_run(experiment_id=eid, start_time=ts)
    run_id = run.info.run_id
    client.log_metric(run_id, 'mae', mae, ts)
    client.set_terminated(run_id)    

***REMOVED*** Simulate runs from 2 weeks, showing steady improvements in MAE
num_days = 14
start_date = datetime.now() - timedelta(days=14)
dates = [start_date + timedelta(days=i) for i in range(num_days)]
maes = [num_days - i + random.random() * 10 for i in range(num_days-5)]
maes.extend([5 + random.random() * 3 for _ in range(5)])
num_runs = [int(random.random() * 10) for _ in range(num_days)]
                
                
***REMOVED*** Run simulate_runs in parallel using a Spark job
_ = sc.parallelize(zip(dates, maes, num_runs)).map(
  lambda zipped: simulate_runs(
    dt=zipped[0], 
    eid=mock_experiment_id, 
    mae=zipped[1], 
    num_runs=zipped[2]
  )
).collect()

***REMOVED*** Simulate runs for 1 year
start_date = datetime.strptime('2019-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
num_days = 365
dates = [start_date + timedelta(days=i) for i in range(num_days)]
runs_per_day = [int(5*(math.cos(x / 30)+1)) for x in range(num_days)]
_ = sc.parallelize(zip(dates, runs_per_day)).map(
  lambda zipped: simulate_runs(
    dt=zipped[0], 
    eid=mock_experiment_id, 
    mae=0, 
    num_runs=zipped[1]
  )
).collect()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Construct Graphs for the Dashboard

***REMOVED*** COMMAND ----------

import mlflow
from mlflow.tracking.client import MlflowClient
import pandas as pd

client = MlflowClient()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Visualize changes in evaluation metrics over time
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This example tracks progress towards optimizing Mean Absolute Error (MAE) over recent days of experiment runs.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can run this on your own experiment by modifying the **Experiment ID** widget at the top of this notebook. You may wish to modify `earliest_start_time`, which restricts which runs are displayed.

***REMOVED*** COMMAND ----------

experiment_id = dbutils.widgets.get("Experiment ID") or mock_experiment_id
runs = mlflow.search_runs(experiment_ids=experiment_id)

earliest_start_time = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
recent_runs = runs[runs.start_time >= earliest_start_time]
pd.options.mode.chained_assignment = None  ***REMOVED*** Suppress pandas warning
recent_runs['Run Date'] = recent_runs.start_time.dt.floor(freq='D')
best_runs_per_day_idx = recent_runs.groupby(['Run Date'])['metrics.mae'].idxmin()
best_runs = recent_runs.loc[best_runs_per_day_idx]

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Best Performing Run for the Past 2 Weeks
display(best_runs[['Run Date', 'metrics.mae']])

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC You can add this chart to a dashboard by clicking the Dashboard icon at the top right and selecting **Add to New Dashboard**.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Track the number of runs started by a specific user
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This example calculates the number of runs started by a specific user each day.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can run this on your own experiment by modifying the **Experiment ID** widget at the top of this notebook. You may also wish to change:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC * `filter_string`: Defaults to selecting runs started by you
***REMOVED*** MAGIC * `earliest_start_time`: Restricts which runs are displayed

***REMOVED*** COMMAND ----------

user = dbutils.widgets.get("User")

if user == '':
  print('Enter a user in the widget at the top of this page (for example, "username@example.com"). Defaults to all users.')
  filter_string = None
else:
  filter_string=f'tags.mlflow.user = "{user}"'
  
runs = mlflow.search_runs(
  experiment_ids=experiment_id,
  filter_string=filter_string
)
earliest_start_time = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
***REMOVED*** If there are no runs, the 'start_time' column will have type float64. Cast it to a datetime64
***REMOVED*** before comparing with earliest_start_time.
runs['start_time'] = runs['start_time'].astype('datetime64[ns]')
recent_runs = runs[runs.start_time >= earliest_start_time]

recent_runs['Run Date'] = recent_runs.start_time.dt.floor(freq='D')

runs_per_day = recent_runs.groupby(['Run Date']).count()[['run_id']].reset_index()
runs_per_day['Run Date'] = runs_per_day['Run Date'].dt.strftime('%Y-%m-%d')
runs_per_day.rename({ 'run_id': 'Number of Runs' }, axis='columns', inplace=True)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Number of Recent Runs Started by a User
if runs_per_day.shape[0] > 0:
  display(runs_per_day)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Measure the total number of runs across all users
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This example calculates the total number of experiment runs created during each month of 2019.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can run this on your own experiment by modifying the **Experiment ID** widget at the top of this notebook.

***REMOVED*** COMMAND ----------

runs = mlflow.search_runs(experiment_ids=experiment_id)

***REMOVED*** COMMAND ----------

runs_2019 = runs[(runs.start_time < '2020-01-01') & (runs.start_time >= '2019-01-01')]
runs_2019['month'] = runs_2019.start_time.dt.month_name()
runs_2019['month_i'] = runs_2019.start_time.dt.month

runs_per_month = runs_2019.groupby(['month_i', 'month']).count()[['run_id']].reset_index('month')
runs_per_month.rename({ 'run_id': 'Number of Runs' }, axis='columns', inplace=True)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Total Number of Runs in 2019
if runs_per_month.shape[0] > 0:
  display(runs_per_month)