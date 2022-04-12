***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED******REMOVED***MLflow Quick Start Part 2: Serving Models with Microsoft Azure ML
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This notebook is part of a Quick Start guide based on the [MLflow tutorial](https://www.mlflow.org/docs/latest/tutorial.html).
***REMOVED*** MAGIC The [first part of the guide](https://docs.azuredatabricks.net/applications/mlflow/mlflow-training.html), **MLflow Quick Start: Model Training and Logging**, focuses on training a model and logging the training metrics, parameters, and model to the MLflow tracking server. 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED*** NOTE: We do not recommend using *Run All* because it takes several minutes to deploy and update models; models cannot be queried until they are active.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This part of the guide consists of the following sections:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Setup
***REMOVED*** MAGIC * Launch an Azure Databricks cluster
***REMOVED*** MAGIC * Install MLflow
***REMOVED*** MAGIC * Install the Azure ML SDK
***REMOVED*** MAGIC * Create or load an Azure ML Workspace
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Building an Azure Container Image for model deployment
***REMOVED*** MAGIC * Use MLflow to build a Container Image for the trained model
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Deploying the model to "dev" using Azure Container Instances (ACI)
***REMOVED*** MAGIC * Create an ACI webservice deployment using the model's Container Image
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Querying the deployed model in "dev"
***REMOVED*** MAGIC * Load a sample input vector from the diabetes dataset
***REMOVED*** MAGIC * Evaluate the sample input vector by sending an HTTP request
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Deploying the model to production using Azure Kubernetes Service (AKS)
***REMOVED*** MAGIC * Option 1: Create a new AKS cluster
***REMOVED*** MAGIC * Option 2: Connect to an existing AKS cluster
***REMOVED*** MAGIC * Deploy to the model's image to the specified AKS cluster
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Querying the deployed model in production
***REMOVED*** MAGIC * Load a sample input vector from the wine dataset
***REMOVED*** MAGIC * Evaluate the sample input vector by sending an HTTP request
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Updating the production deployment
***REMOVED*** MAGIC * Build an Azure Container Image for another model
***REMOVED*** MAGIC * Deploy the new model's image to the AKS cluster
***REMOVED*** MAGIC * Query the updated model
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Cleaning up the deployments
***REMOVED*** MAGIC * Terminate the "dev" ACI webservice
***REMOVED*** MAGIC * Terminate the production AKS webservice
***REMOVED*** MAGIC * Remove the AKS cluster from the Azure ML Workspace
***REMOVED*** MAGIC 
***REMOVED*** MAGIC As in the first part of the Quick Start tutorial, this notebook uses ElasticNet models trained on the `diabetes` dataset in scikit-learn.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC **Note:** This notebook expects that you use an Azure Databricks hosted MLflow tracking server. To set up your own tracking server, see the instructions in [MLflow Tracking Servers](https://www.mlflow.org/docs/latest/tracking.html***REMOVED***mlflow-tracking-servers) and configure your connection to your tracking server by running [mlflow.set_tracking_uri](https://www.mlflow.org/docs/latest/python_api/mlflow.html***REMOVED***mlflow.set_tracking_uri).

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Prerequisites
***REMOVED*** MAGIC ElasticNet models from the MLflow Quick Start notebook in [part 1 of the Quick Start guide](https://docs.azuredatabricks.net/applications/mlflow/mlflow-training.html).

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Setup

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 1. Ensure you are using or create a cluster specifying 
***REMOVED*** MAGIC   * **Databricks Runtime Version:** Databricks Runtime 5.0 or above
***REMOVED*** MAGIC   * **Python Version:** Python 3
***REMOVED*** MAGIC 1. Install required libraries or if using Databricks Runtime 5.1 or above (but not Databricks Runtime for ML), run Cmd 6.
***REMOVED*** MAGIC    1. Create required libraries.
***REMOVED*** MAGIC       * Source **PyPI** and enter `mlflow[extras]`. This installs `mlflow` and all its dependencies.
***REMOVED*** MAGIC       * Source **PyPI** and enter `azureml-sdk[databricks]`.
***REMOVED*** MAGIC    1. Install the libraries into the cluster.
***REMOVED*** MAGIC 1. Attach this notebook to the cluster.

***REMOVED*** COMMAND ----------

***REMOVED***dbutils.library.installPyPI("mlflow", extras="extras")
***REMOVED***dbutils.library.installPyPI("azureml-sdk[databricks]")
***REMOVED***dbutils.library.restartPython()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Create or load an Azure ML Workspace

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Before models can be deployed to Azure ML, you must create or obtain an Azure ML Workspace. The `azureml.core.Workspace.create()` function will load a workspace of a specified name or create one if it does not already exist. For more information about creating an Azure ML Workspace, see the [Azure ML Workspace management documentation](https://docs.microsoft.com/en-us/azure/machine-learning/service/how-to-manage-workspace).

***REMOVED*** COMMAND ----------

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

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Build an Azure Container Image for model deployment

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Use MLflow to build a Container Image for the trained model
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Use the `mlflow.azuereml.build_image` function to build an Azure Container Image for the trained MLflow model. This function also registers the MLflow model with a specified Azure ML workspace. The resulting image can be deployed to Azure Container Instances (ACI) or Azure Kubernetes Service (AKS) for real-time serving.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Specify the run ID associated with an ElasticNet training run from [part 1 of the Quick Start guide](https://docs.azuredatabricks.net/spark/latest/mllib/mlflow-tracking.html). You can find a run ID and model path from the experiment run, which can be found on the run details page:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![image](https://docs.azuredatabricks.net/_static/images/mlflow/mlflow-deployment-example-run-info.png)

***REMOVED*** COMMAND ----------

run_id1 = "<run-id1>"
model_uri = "runs:/" + run_id1 + "/model"

***REMOVED*** COMMAND ----------

import mlflow.azureml

model_image, azure_model = mlflow.azureml.build_image(model_uri=model_uri, 
                                                      workspace=workspace,
                                                      model_name="model",
                                                      image_name="model",
                                                      description="Sklearn ElasticNet image for predicting diabetes progression",
                                                      synchronous=False)

***REMOVED*** COMMAND ----------

model_image.wait_for_creation(show_output=True)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Deploy the model to "dev" using [Azure Container Instances (ACI)](https://docs.microsoft.com/en-us/azure/container-instances/)
***REMOVED*** MAGIC 
***REMOVED*** MAGIC The [ACI platform](https://docs.microsoft.com/en-us/azure/container-instances/) is the recommended environment for staging and developmental model deployments.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Create an ACI webservice deployment using the model's Container Image
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Using the Azure ML SDK, deploy the Container Image for the trained MLflow model to ACI.

***REMOVED*** COMMAND ----------

from azureml.core.webservice import AciWebservice, Webservice

dev_webservice_name = "diabetes-model"
dev_webservice_deployment_config = AciWebservice.deploy_configuration()
dev_webservice = Webservice.deploy_from_image(name=dev_webservice_name, image=model_image, deployment_config=dev_webservice_deployment_config, workspace=workspace)

***REMOVED*** COMMAND ----------

dev_webservice.wait_for_deployment()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Query the deployed model in "dev"

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Load diabetes dataset

***REMOVED*** COMMAND ----------

from sklearn import datasets
diabetes = datasets.load_diabetes()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Create sample input vector

***REMOVED*** COMMAND ----------

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

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Evaluate the sample input vector by sending an HTTP request
***REMOVED*** MAGIC Query the ACI webservice's scoring endpoint by sending an HTTP POST request that contains the input vector.

***REMOVED*** COMMAND ----------

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

***REMOVED*** COMMAND ----------

dev_webservice.scoring_uri

***REMOVED*** COMMAND ----------

dev_prediction = query_endpoint_example(scoring_uri=dev_webservice.scoring_uri, inputs=query_input)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Deploy the model to production using [Azure Kubernetes Service (AKS)](https://azure.microsoft.com/en-us/services/kubernetes-service/). Do Option 1 or Option 2.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Option 1: Create a new AKS cluster
***REMOVED*** MAGIC 
***REMOVED*** MAGIC If you do not have an active AKS cluster for model deployment, create one using the Azure ML SDK.

***REMOVED*** COMMAND ----------

from azureml.core.compute import AksCompute, ComputeTarget

***REMOVED*** Use the default configuration (you can also provide parameters to customize this)
prov_config = AksCompute.provisioning_configuration()

aks_cluster_name = "diabetes-cluster" 
***REMOVED*** Create the cluster
aks_target = ComputeTarget.create(workspace = workspace, 
                                  name = aks_cluster_name, 
                                  provisioning_configuration = prov_config)

***REMOVED*** Wait for the create process to complete
aks_target.wait_for_completion(show_output = True)
print(aks_target.provisioning_state)
print(aks_target.provisioning_errors)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Option 2: Connect to an existing AKS cluster
***REMOVED*** MAGIC 
***REMOVED*** MAGIC If you already have an active AKS cluster running, you can add it to your Workspace using the Azure ML SDK.

***REMOVED*** COMMAND ----------

from azureml.core.compute import AksCompute, ComputeTarget

***REMOVED*** Get the resource group from https://porta..azure.com -> Find your resource group
resource_group = "<resource-group>"

***REMOVED*** Give the cluster a local name
aks_cluster_name = "diabetes-cluster"

***REMOVED*** Attatch the cluster to your workgroup
attach_config = AksCompute.attach_configuration(resource_group=resource_group, cluster_name=aks_cluster_name)
aks_target = ComputeTarget.attach(workspace, name="diabetes-compute", attach_config)

***REMOVED*** Wait for the operation to complete
aks_target.wait_for_completion(True)
print(aks_target.provisioning_state)
print(aks_target.provisioning_errors)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Deploy to the model's image to the specified AKS cluster

***REMOVED*** COMMAND ----------

from azureml.core.webservice import Webservice, AksWebservice

***REMOVED*** Set configuration and service name
prod_webservice_name = "diabetes-model-prod"
prod_webservice_deployment_config = AksWebservice.deploy_configuration()

***REMOVED*** Deploy from image
prod_webservice = Webservice.deploy_from_image(workspace = workspace, 
                                               name = prod_webservice_name,
                                               image = model_image,
                                               deployment_config = prod_webservice_deployment_config,
                                               deployment_target = aks_target)

***REMOVED*** COMMAND ----------

***REMOVED*** Wait for the deployment to complete
prod_webservice.wait_for_deployment(show_output = True)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Query the deployed model in production

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Evaluate the sample input vector by sending an HTTP request
***REMOVED*** MAGIC Query the AKS webservice's scoring endpoint by sending an HTTP POST request that includes the input vector. The production AKS deployment may require an authorization token (service key) for queries. Include this key in the HTTP request header.

***REMOVED*** COMMAND ----------

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

***REMOVED*** COMMAND ----------

prod_scoring_uri = prod_webservice.scoring_uri
prod_service_key = prod_webservice.get_keys()[0] if len(prod_webservice.get_keys()) > 0 else None

***REMOVED*** COMMAND ----------

prod_prediction1 = query_endpoint_example(scoring_uri=prod_scoring_uri, service_key=prod_service_key, inputs=query_input)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Update the production deployment

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Build an Azure Container Image for the new model

***REMOVED*** COMMAND ----------

run_id2 = "<run-id2>"
model_uri = "runs:/" + run_id2 + "/model"

***REMOVED*** COMMAND ----------

import mlflow.azureml

model_image_updated, azure_model_updated = mlflow.azureml.build_image(model_uri=model_uri, 
                                                                      workspace=workspace,
                                                                      model_name="model-updated",
                                                                      image_name="model-updated",
                                                                      description="Sklearn ElasticNet image for predicting diabetes progression",
                                                                      synchronous=False)

***REMOVED*** COMMAND ----------

model_image_updated.wait_for_creation(show_output=True)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Deploy the new model's image to the AKS cluster
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Using the [`azureml.core.webservice.AksWebservice.update()`](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.webservice.akswebservice?view=azure-ml-py***REMOVED***update) function, replace the deployment's existing model image with the new model image.

***REMOVED*** COMMAND ----------

prod_webservice.update(image=model_image_updated)

***REMOVED*** COMMAND ----------

prod_webservice.wait_for_deployment(show_output = True)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Query the updated model

***REMOVED*** COMMAND ----------

prod_prediction2 = query_endpoint_example(scoring_uri=prod_scoring_uri, service_key=prod_service_key, inputs=query_input)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Compare the predictions

***REMOVED*** COMMAND ----------

print("Run ID: {} Prediction: {}".format(run_id1, prod_prediction1)) 
print("Run ID: {} Prediction: {}".format(run_id2, prod_prediction2))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Clean up the deployments

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Terminate the "dev" ACI webservice
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Because ACI manages compute resources on your behalf, deleting the "dev" ACI webservice will remove all resources associated with the "dev" model deployment

***REMOVED*** COMMAND ----------

dev_webservice.delete()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Terminate the production AKS webservice
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This terminates the real-time serving webservice running on the specified AKS cluster. It **does not** terminate the AKS cluster.

***REMOVED*** COMMAND ----------

prod_webservice.delete()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Remove the AKS cluster from the Azure ML Workspace
***REMOVED*** MAGIC 
***REMOVED*** MAGIC If the cluster was created using the Azure ML SDK (see **Option 1: Create a new AKS cluster**), remove it from the Azure ML Workspace will terminate the cluster, including all of its compute resources and deployments.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC If the cluster was created independently (see **Option 2: Connect to an existing AKS cluster**), it will remain active after removal from the Azure ML Workspace.

***REMOVED*** COMMAND ----------

aks_target.delete()