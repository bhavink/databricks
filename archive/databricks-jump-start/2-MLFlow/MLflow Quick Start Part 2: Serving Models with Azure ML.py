# Databricks notebook source
# MAGIC %md ##MLflow Quick Start Part 2: Serving Models with Microsoft Azure ML
# MAGIC 
# MAGIC This notebook is part of a Quick Start guide based on the [MLflow tutorial](https://www.mlflow.org/docs/latest/tutorial.html).
# MAGIC The [first part of the guide](https://docs.azuredatabricks.net/applications/mlflow/mlflow-training.html), **MLflow Quick Start: Model Training and Logging**, focuses on training a model and logging the training metrics, parameters, and model to the MLflow tracking server. 
# MAGIC 
# MAGIC ##### NOTE: We do not recommend using *Run All* because it takes several minutes to deploy and update models; models cannot be queried until they are active.
# MAGIC 
# MAGIC This part of the guide consists of the following sections:
# MAGIC 
# MAGIC #### Setup
# MAGIC * Launch an Azure Databricks cluster
# MAGIC * Install MLflow
# MAGIC * Install the Azure ML SDK
# MAGIC * Create or load an Azure ML Workspace
# MAGIC 
# MAGIC #### Building an Azure Container Image for model deployment
# MAGIC * Use MLflow to build a Container Image for the trained model
# MAGIC 
# MAGIC #### Deploying the model to "dev" using Azure Container Instances (ACI)
# MAGIC * Create an ACI webservice deployment using the model's Container Image
# MAGIC 
# MAGIC #### Querying the deployed model in "dev"
# MAGIC * Load a sample input vector from the diabetes dataset
# MAGIC * Evaluate the sample input vector by sending an HTTP request
# MAGIC 
# MAGIC #### Deploying the model to production using Azure Kubernetes Service (AKS)
# MAGIC * Option 1: Create a new AKS cluster
# MAGIC * Option 2: Connect to an existing AKS cluster
# MAGIC * Deploy to the model's image to the specified AKS cluster
# MAGIC 
# MAGIC #### Querying the deployed model in production
# MAGIC * Load a sample input vector from the wine dataset
# MAGIC * Evaluate the sample input vector by sending an HTTP request
# MAGIC 
# MAGIC #### Updating the production deployment
# MAGIC * Build an Azure Container Image for another model
# MAGIC * Deploy the new model's image to the AKS cluster
# MAGIC * Query the updated model
# MAGIC 
# MAGIC #### Cleaning up the deployments
# MAGIC * Terminate the "dev" ACI webservice
# MAGIC * Terminate the production AKS webservice
# MAGIC * Remove the AKS cluster from the Azure ML Workspace
# MAGIC 
# MAGIC As in the first part of the Quick Start tutorial, this notebook uses ElasticNet models trained on the `diabetes` dataset in scikit-learn.

# COMMAND ----------

# MAGIC %md 
# MAGIC **Note:** This notebook expects that you use an Azure Databricks hosted MLflow tracking server. To set up your own tracking server, see the instructions in [MLflow Tracking Servers](https://www.mlflow.org/docs/latest/tracking.html#mlflow-tracking-servers) and configure your connection to your tracking server by running [mlflow.set_tracking_uri](https://www.mlflow.org/docs/latest/python_api/mlflow.html#mlflow.set_tracking_uri).

# COMMAND ----------

# MAGIC %md ## Prerequisites
# MAGIC ElasticNet models from the MLflow Quick Start notebook in [part 1 of the Quick Start guide](https://docs.azuredatabricks.net/applications/mlflow/mlflow-training.html).

# COMMAND ----------

# MAGIC %md ## Setup

# COMMAND ----------

# MAGIC %md
# MAGIC 1. Ensure you are using or create a cluster specifying 
# MAGIC   * **Databricks Runtime Version:** Databricks Runtime 5.0 or above
# MAGIC   * **Python Version:** Python 3
# MAGIC 1. Install required libraries or if using Databricks Runtime 5.1 or above (but not Databricks Runtime for ML), run Cmd 6.
# MAGIC    1. Create required libraries.
# MAGIC       * Source **PyPI** and enter `mlflow[extras]`. This installs `mlflow` and all its dependencies.
# MAGIC       * Source **PyPI** and enter `azureml-sdk[databricks]`.
# MAGIC    1. Install the libraries into the cluster.
# MAGIC 1. Attach this notebook to the cluster.

# COMMAND ----------

#dbutils.library.installPyPI("mlflow", extras="extras")
#dbutils.library.installPyPI("azureml-sdk[databricks]")
#dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md ### Create or load an Azure ML Workspace

# COMMAND ----------

# MAGIC %md Before models can be deployed to Azure ML, you must create or obtain an Azure ML Workspace. The `azureml.core.Workspace.create()` function will load a workspace of a specified name or create one if it does not already exist. For more information about creating an Azure ML Workspace, see the [Azure ML Workspace management documentation](https://docs.microsoft.com/en-us/azure/machine-learning/service/how-to-manage-workspace).

# COMMAND ----------

import azureml
from azureml.core import Workspace

workspace_name = "<workspace-name>"
workspace_location="<workspace-location>"
resource_group = "<resource-group>"
subscription_id = "<subscription-id>"

workspace = Workspace.create(name = workspace_name,
                             location = workspace_location,
                             resource_group = resource_group,
                             subscription_id = subscription_id,
                             exist_ok=True)

# COMMAND ----------

# MAGIC %md ## Build an Azure Container Image for model deployment

# COMMAND ----------

# MAGIC %md ### Use MLflow to build a Container Image for the trained model
# MAGIC 
# MAGIC Use the `mlflow.azuereml.build_image` function to build an Azure Container Image for the trained MLflow model. This function also registers the MLflow model with a specified Azure ML workspace. The resulting image can be deployed to Azure Container Instances (ACI) or Azure Kubernetes Service (AKS) for real-time serving.

# COMMAND ----------

# MAGIC %md Specify the run ID associated with an ElasticNet training run from [part 1 of the Quick Start guide](https://docs.azuredatabricks.net/spark/latest/mllib/mlflow-tracking.html). You can find a run ID and model path from the experiment run, which can be found on the run details page:
# MAGIC 
# MAGIC ![image](https://docs.azuredatabricks.net/_static/images/mlflow/mlflow-deployment-example-run-info.png)

# COMMAND ----------

run_id1 = "<run-id1>"
model_uri = "runs:/" + run_id1 + "/model"

# COMMAND ----------

import mlflow.azureml

model_image, azure_model = mlflow.azureml.build_image(model_uri=model_uri, 
                                                      workspace=workspace,
                                                      model_name="model",
                                                      image_name="model",
                                                      description="Sklearn ElasticNet image for predicting diabetes progression",
                                                      synchronous=False)

# COMMAND ----------

model_image.wait_for_creation(show_output=True)

# COMMAND ----------

# MAGIC %md ## Deploy the model to "dev" using [Azure Container Instances (ACI)](https://docs.microsoft.com/en-us/azure/container-instances/)
# MAGIC 
# MAGIC The [ACI platform](https://docs.microsoft.com/en-us/azure/container-instances/) is the recommended environment for staging and developmental model deployments.

# COMMAND ----------

# MAGIC %md ### Create an ACI webservice deployment using the model's Container Image
# MAGIC 
# MAGIC Using the Azure ML SDK, deploy the Container Image for the trained MLflow model to ACI.

# COMMAND ----------

from azureml.core.webservice import AciWebservice, Webservice

dev_webservice_name = "diabetes-model"
dev_webservice_deployment_config = AciWebservice.deploy_configuration()
dev_webservice = Webservice.deploy_from_image(name=dev_webservice_name, image=model_image, deployment_config=dev_webservice_deployment_config, workspace=workspace)

# COMMAND ----------

dev_webservice.wait_for_deployment()

# COMMAND ----------

# MAGIC %md ## Query the deployed model in "dev"

# COMMAND ----------

# MAGIC %md ### Load diabetes dataset

# COMMAND ----------

from sklearn import datasets
diabetes = datasets.load_diabetes()

# COMMAND ----------

# MAGIC %md ## Create sample input vector

# COMMAND ----------

import pandas as pd
import numpy as np

X = diabetes.data
y = diabetes.target
Y = np.array([y]).transpose()
d = np.concatenate((X, Y), axis=1)
cols = ['age', 'sex', 'bmi', 'bp', 's1', 's2', 's3', 's4', 's5', 's6', 'progression']
data = pd.DataFrame(d, columns=cols)
sample = data.drop(["progression"], axis=1).iloc[[0]]
                                                 
query_input = sample.to_json(orient='split')
query_input = eval(query_input)
query_input.pop('index', None)

# COMMAND ----------

# MAGIC %md #### Evaluate the sample input vector by sending an HTTP request
# MAGIC Query the ACI webservice's scoring endpoint by sending an HTTP POST request that contains the input vector.

# COMMAND ----------

import requests
import json

def query_endpoint_example(scoring_uri, inputs, service_key=None):
  headers = {
    "Content-Type": "application/json",
  }
  if service_key is not None:
    headers["Authorization"] = "Bearer {service_key}".format(service_key=service_key)
    
  print("Sending batch prediction request with inputs: {}".format(inputs))
  response = requests.post(scoring_uri, data=json.dumps(inputs), headers=headers)
  preds = json.loads(response.text)
  print("Received response: {}".format(preds))
  return preds

# COMMAND ----------

dev_webservice.scoring_uri

# COMMAND ----------

dev_prediction = query_endpoint_example(scoring_uri=dev_webservice.scoring_uri, inputs=query_input)

# COMMAND ----------

# MAGIC %md ## Deploy the model to production using [Azure Kubernetes Service (AKS)](https://azure.microsoft.com/en-us/services/kubernetes-service/). Do Option 1 or Option 2.

# COMMAND ----------

# MAGIC %md ### Option 1: Create a new AKS cluster
# MAGIC 
# MAGIC If you do not have an active AKS cluster for model deployment, create one using the Azure ML SDK.

# COMMAND ----------

from azureml.core.compute import AksCompute, ComputeTarget

# Use the default configuration (you can also provide parameters to customize this)
prov_config = AksCompute.provisioning_configuration()

aks_cluster_name = "diabetes-cluster" 
# Create the cluster
aks_target = ComputeTarget.create(workspace = workspace, 
                                  name = aks_cluster_name, 
                                  provisioning_configuration = prov_config)

# Wait for the create process to complete
aks_target.wait_for_completion(show_output = True)
print(aks_target.provisioning_state)
print(aks_target.provisioning_errors)

# COMMAND ----------

# MAGIC %md ### Option 2: Connect to an existing AKS cluster
# MAGIC 
# MAGIC If you already have an active AKS cluster running, you can add it to your Workspace using the Azure ML SDK.

# COMMAND ----------

from azureml.core.compute import AksCompute, ComputeTarget

# Get the resource group from https://porta..azure.com -> Find your resource group
resource_group = "<resource-group>"

# Give the cluster a local name
aks_cluster_name = "diabetes-cluster"

# Attatch the cluster to your workgroup
attach_config = AksCompute.attach_configuration(resource_group=resource_group, cluster_name=aks_cluster_name)
aks_target = ComputeTarget.attach(workspace, name="diabetes-compute", attach_config)

# Wait for the operation to complete
aks_target.wait_for_completion(True)
print(aks_target.provisioning_state)
print(aks_target.provisioning_errors)

# COMMAND ----------

# MAGIC %md ### Deploy to the model's image to the specified AKS cluster

# COMMAND ----------

from azureml.core.webservice import Webservice, AksWebservice

# Set configuration and service name
prod_webservice_name = "diabetes-model-prod"
prod_webservice_deployment_config = AksWebservice.deploy_configuration()

# Deploy from image
prod_webservice = Webservice.deploy_from_image(workspace = workspace, 
                                               name = prod_webservice_name,
                                               image = model_image,
                                               deployment_config = prod_webservice_deployment_config,
                                               deployment_target = aks_target)

# COMMAND ----------

# Wait for the deployment to complete
prod_webservice.wait_for_deployment(show_output = True)

# COMMAND ----------

# MAGIC %md ## Query the deployed model in production

# COMMAND ----------

# MAGIC %md #### Evaluate the sample input vector by sending an HTTP request
# MAGIC Query the AKS webservice's scoring endpoint by sending an HTTP POST request that includes the input vector. The production AKS deployment may require an authorization token (service key) for queries. Include this key in the HTTP request header.

# COMMAND ----------

import requests
import json

def query_endpoint_example(scoring_uri, inputs, service_key=None):
  headers = {
    "Content-Type": "application/json",
  }
  if service_key is not None:
    headers["Authorization"] = "Bearer {service_key}".format(service_key=service_key)
    
  print("Sending batch prediction request with inputs: {}".format(inputs))
  response = requests.post(scoring_uri, data=json.dumps(inputs), headers=headers)
  preds = json.loads(response.text)
  print("Received response: {}".format(preds))
  return preds

# COMMAND ----------

prod_scoring_uri = prod_webservice.scoring_uri
prod_service_key = prod_webservice.get_keys()[0] if len(prod_webservice.get_keys()) > 0 else None

# COMMAND ----------

prod_prediction1 = query_endpoint_example(scoring_uri=prod_scoring_uri, service_key=prod_service_key, inputs=query_input)

# COMMAND ----------

# MAGIC %md ## Update the production deployment

# COMMAND ----------

# MAGIC %md ### Build an Azure Container Image for the new model

# COMMAND ----------

run_id2 = "<run-id2>"
model_uri = "runs:/" + run_id2 + "/model"

# COMMAND ----------

import mlflow.azureml

model_image_updated, azure_model_updated = mlflow.azureml.build_image(model_uri=model_uri, 
                                                                      workspace=workspace,
                                                                      model_name="model-updated",
                                                                      image_name="model-updated",
                                                                      description="Sklearn ElasticNet image for predicting diabetes progression",
                                                                      synchronous=False)

# COMMAND ----------

model_image_updated.wait_for_creation(show_output=True)

# COMMAND ----------

# MAGIC %md ### Deploy the new model's image to the AKS cluster
# MAGIC 
# MAGIC Using the [`azureml.core.webservice.AksWebservice.update()`](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.webservice.akswebservice?view=azure-ml-py#update) function, replace the deployment's existing model image with the new model image.

# COMMAND ----------

prod_webservice.update(image=model_image_updated)

# COMMAND ----------

prod_webservice.wait_for_deployment(show_output = True)

# COMMAND ----------

# MAGIC %md ### Query the updated model

# COMMAND ----------

prod_prediction2 = query_endpoint_example(scoring_uri=prod_scoring_uri, service_key=prod_service_key, inputs=query_input)

# COMMAND ----------

# MAGIC %md ## Compare the predictions

# COMMAND ----------

print("Run ID: {} Prediction: {}".format(run_id1, prod_prediction1)) 
print("Run ID: {} Prediction: {}".format(run_id2, prod_prediction2))

# COMMAND ----------

# MAGIC %md ## Clean up the deployments

# COMMAND ----------

# MAGIC %md ### Terminate the "dev" ACI webservice
# MAGIC 
# MAGIC Because ACI manages compute resources on your behalf, deleting the "dev" ACI webservice will remove all resources associated with the "dev" model deployment

# COMMAND ----------

dev_webservice.delete()

# COMMAND ----------

# MAGIC %md ### Terminate the production AKS webservice
# MAGIC 
# MAGIC This terminates the real-time serving webservice running on the specified AKS cluster. It **does not** terminate the AKS cluster.

# COMMAND ----------

prod_webservice.delete()

# COMMAND ----------

# MAGIC %md ### Remove the AKS cluster from the Azure ML Workspace
# MAGIC 
# MAGIC If the cluster was created using the Azure ML SDK (see **Option 1: Create a new AKS cluster**), remove it from the Azure ML Workspace will terminate the cluster, including all of its compute resources and deployments.
# MAGIC 
# MAGIC If the cluster was created independently (see **Option 2: Connect to an existing AKS cluster**), it will remain active after removal from the Azure ML Workspace.

# COMMAND ----------

aks_target.delete()