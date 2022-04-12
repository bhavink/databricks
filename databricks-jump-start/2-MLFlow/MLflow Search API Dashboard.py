# Databricks notebook source
# MAGIC %md ##Building Dashboards with the MLflow Search API
# MAGIC 
# MAGIC This notebook demonstrates how to use the [mlflow.search_runs](https://www.mlflow.org/docs/latest/search-syntax.html#programmatically-searching-runs) API to generate custom dashboards.
# MAGIC 
# MAGIC The notebook contains the following sections:
# MAGIC 
# MAGIC #### Setup
# MAGIC * Launch a Python 3 cluster running Databricks Runtime ML
# MAGIC 
# MAGIC #### Mock Data Setup
# MAGIC * Generate a mock MLflow experiment
# MAGIC 
# MAGIC You can skip this section if you'd like to generate dashboards from existing experiments.
# MAGIC 
# MAGIC #### Dashboards
# MAGIC * Visualize changes in evaluation metrics over time
# MAGIC * Track the number of runs kicked off by a particular user
# MAGIC * Measure the total number of runs across all users

# COMMAND ----------

# MAGIC %md ## Setup

# COMMAND ----------

# MAGIC %md 
# MAGIC 1. Ensure you are using or create a cluster specifying 
# MAGIC   * **Databricks Runtime Version:** Any version of Databricks Runtime ML (e.g. Databricks Runtime 6.3 ML)
# MAGIC   * **Python Version:** Python 3
# MAGIC 1. Attach this notebook to the cluster.

# COMMAND ----------

# MAGIC %md ##Experiment Data

# COMMAND ----------

# MAGIC %md To plot summaries of existing experiment data, enter the ID of an existing experiment in the **Experiment ID** widget. Otherwise, the following cells generate and plot mock data.

# COMMAND ----------

dbutils.widgets.text("Experiment ID", "")
dbutils.widgets.text("User", "")

# COMMAND ----------

# MAGIC %md ## Mock Data Setup

# COMMAND ----------

# MAGIC %md
# MAGIC This section creates a mock experiment. To analyze your own experiment data rather than these mocks, change the value in the **Experiment ID** widget at the top of this notebook.

# COMMAND ----------

from mlflow.tracking.client import MlflowClient

from datetime import datetime, timedelta
import math
import random

random.seed(42)
client = MlflowClient()

mock_experiment_file = f'/tmp/mock_experiment'
# Delete experiment if it already exists
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

# Simulate runs from 2 weeks, showing steady improvements in MAE
num_days = 14
start_date = datetime.now() - timedelta(days=14)
dates = [start_date + timedelta(days=i) for i in range(num_days)]
maes = [num_days - i + random.random() * 10 for i in range(num_days-5)]
maes.extend([5 + random.random() * 3 for _ in range(5)])
num_runs = [int(random.random() * 10) for _ in range(num_days)]
                
                
# Run simulate_runs in parallel using a Spark job
_ = sc.parallelize(zip(dates, maes, num_runs)).map(
  lambda zipped: simulate_runs(
    dt=zipped[0], 
    eid=mock_experiment_id, 
    mae=zipped[1], 
    num_runs=zipped[2]
  )
).collect()

# Simulate runs for 1 year
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

# COMMAND ----------

# MAGIC %md ## Construct Graphs for the Dashboard

# COMMAND ----------

import mlflow
from mlflow.tracking.client import MlflowClient
import pandas as pd

client = MlflowClient()

# COMMAND ----------

# MAGIC %md ### Visualize changes in evaluation metrics over time
# MAGIC 
# MAGIC This example tracks progress towards optimizing Mean Absolute Error (MAE) over recent days of experiment runs.
# MAGIC 
# MAGIC You can run this on your own experiment by modifying the **Experiment ID** widget at the top of this notebook. You may wish to modify `earliest_start_time`, which restricts which runs are displayed.

# COMMAND ----------

experiment_id = dbutils.widgets.get("Experiment ID") or mock_experiment_id
runs = mlflow.search_runs(experiment_ids=experiment_id)

earliest_start_time = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
recent_runs = runs[runs.start_time >= earliest_start_time]
pd.options.mode.chained_assignment = None  # Suppress pandas warning
recent_runs['Run Date'] = recent_runs.start_time.dt.floor(freq='D')
best_runs_per_day_idx = recent_runs.groupby(['Run Date'])['metrics.mae'].idxmin()
best_runs = recent_runs.loc[best_runs_per_day_idx]

# COMMAND ----------

# DBTITLE 1,Best Performing Run for the Past 2 Weeks
display(best_runs[['Run Date', 'metrics.mae']])

# COMMAND ----------

# MAGIC %md
# MAGIC You can add this chart to a dashboard by clicking the Dashboard icon at the top right and selecting **Add to New Dashboard**.

# COMMAND ----------

# MAGIC %md ### Track the number of runs started by a specific user
# MAGIC 
# MAGIC This example calculates the number of runs started by a specific user each day.
# MAGIC 
# MAGIC You can run this on your own experiment by modifying the **Experiment ID** widget at the top of this notebook. You may also wish to change:
# MAGIC 
# MAGIC * `filter_string`: Defaults to selecting runs started by you
# MAGIC * `earliest_start_time`: Restricts which runs are displayed

# COMMAND ----------

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
# If there are no runs, the 'start_time' column will have type float64. Cast it to a datetime64
# before comparing with earliest_start_time.
runs['start_time'] = runs['start_time'].astype('datetime64[ns]')
recent_runs = runs[runs.start_time >= earliest_start_time]

recent_runs['Run Date'] = recent_runs.start_time.dt.floor(freq='D')

runs_per_day = recent_runs.groupby(['Run Date']).count()[['run_id']].reset_index()
runs_per_day['Run Date'] = runs_per_day['Run Date'].dt.strftime('%Y-%m-%d')
runs_per_day.rename({ 'run_id': 'Number of Runs' }, axis='columns', inplace=True)

# COMMAND ----------

# DBTITLE 1,Number of Recent Runs Started by a User
if runs_per_day.shape[0] > 0:
  display(runs_per_day)

# COMMAND ----------

# MAGIC %md ### Measure the total number of runs across all users
# MAGIC 
# MAGIC This example calculates the total number of experiment runs created during each month of 2019.
# MAGIC 
# MAGIC You can run this on your own experiment by modifying the **Experiment ID** widget at the top of this notebook.

# COMMAND ----------

runs = mlflow.search_runs(experiment_ids=experiment_id)

# COMMAND ----------

runs_2019 = runs[(runs.start_time < '2020-01-01') & (runs.start_time >= '2019-01-01')]
runs_2019['month'] = runs_2019.start_time.dt.month_name()
runs_2019['month_i'] = runs_2019.start_time.dt.month

runs_per_month = runs_2019.groupby(['month_i', 'month']).count()[['run_id']].reset_index('month')
runs_per_month.rename({ 'run_id': 'Number of Runs' }, axis='columns', inplace=True)

# COMMAND ----------

# DBTITLE 1,Total Number of Runs in 2019
if runs_per_month.shape[0] > 0:
  display(runs_per_month)