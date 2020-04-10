# Databricks notebook source
# MAGIC %md # Using scikit-learn with Spark on Databricks
# MAGIC 
# MAGIC This notebook demonstrates how to take advantage of Spark and Databricks to use [scikit-learn](http://scikit-learn.org/), the popular Python library for doing Machine Learning on a single compute node.
# MAGIC 
# MAGIC Even though the algorithms in scikit-learn are not distributed, we can still take advantage of distributed computation for certain ML tasks.  This can help with the transition from single-node workflows to fully distributed workflows: One can start by porting an existing workflow to Spark, begin to distribute certain tasks, and eventually move to fully distributed training via MLlib algorithms.
# MAGIC 
# MAGIC **Contents**
# MAGIC 1. Running scikit-learn on the driver
# MAGIC 2. Distributing scikit-learn jobs
# MAGIC 3. Converting between scikit-learn and MLlib models

# COMMAND ----------

# MAGIC %md ## 1. Running scikit-learn on the driver
# MAGIC 
# MAGIC The simplest way to use scikit-learn with Spark and Databricks is to run scikit-learn jobs as usual.  However, this will run scikit-learn jobs on the driver, so **be careful** not to run large jobs, especially if other users are working on the same cluster as you.  Nevertheless, a reasonable way to port existing scikit-learn workflows to Spark and start benefiting from distributed computing is to: (a) copy the workflow into Databricks and (b) start parallelizing the workflow piece-by-piece.  We discuss parallelization in the next section.
# MAGIC 
# MAGIC In this section, we will do the following:
# MAGIC * Load data into a Pandas dataframe
# MAGIC * Explore the data
# MAGIC * Transform features
# MAGIC * Hold out a random test dataset
# MAGIC * Learn an initial model
# MAGIC * Evaluate the initial model

# COMMAND ----------

# MAGIC %md ### Load data into a Pandas dataframe
# MAGIC 
# MAGIC We will use the R "diamonds" dataset from the "ggplot2" package.  This is a dataset hosted on Databricks.
# MAGIC 
# MAGIC Our task will be to predict the price of a diamond from its properties.

# COMMAND ----------

displayHTML(sc.wholeTextFiles("/databricks-datasets/Rdatasets/data-001/doc/ggplot2/diamonds.html").take(1)[0][1])

# COMMAND ----------

# Load data into a Pandas dataframe
import pandas
pandasData = pandas.read_csv("/dbfs/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv").iloc[:,1:] # remove line number

# COMMAND ----------

# MAGIC %md ### Explore the data
# MAGIC 
# MAGIC We quickly demonstrate how to start exploring the data.  For a longer tutorial, see the [Visualizations](https://docs.databricks.com/user-guide/visualizations/index.html).

# COMMAND ----------

# We can view the Pandas dataframe using Pandas' native display
pandasData

# COMMAND ----------

# MAGIC %md We can make plots using Python tools like matplotlib.

# COMMAND ----------

import matplotlib.pyplot as plt
plt.clf()
plt.plot(pandasData['carat'], pandasData['price'], '.')
plt.xlabel('carat')
plt.ylabel('price')
display()

# COMMAND ----------

# MAGIC %md We can also convert the Pandas dataframe into a Spark DataFrame and use Databricks display methods.

# COMMAND ----------

sparkDataframe = spark.createDataFrame(pandasData)
display(sparkDataframe)

# COMMAND ----------

# MAGIC %md ### Transform features
# MAGIC 
# MAGIC Some of our features are text, and we want them to be numerical so we can train a linear model.  We use the Pandas and scikit-learn APIs for these transformations.

# COMMAND ----------

# MAGIC %md First, we convert the features to numerical values, in the correct order based on the feature meanings.  Higher indices are "better."  This ordering will help us interpret model weights later on.

# COMMAND ----------

pandasData['cut'] = pandasData['cut'].replace({'Fair':0, 'Good':1, 'Very Good':2, 'Premium':3, 'Ideal':4})
pandasData['color'] = pandasData['color'].replace({'J':0, 'I':1, 'H':2, 'G':3, 'F':4, 'E':5, 'D':6})
pandasData['clarity'] = pandasData['clarity'].replace({'I1':0, 'SI1':1, 'SI2':2, 'VS1':3, 'VS2':4, 'VVS1':5, 'VVS2':6, 'IF':7})
pandasData

# COMMAND ----------

# MAGIC %md Now, we normalize each feature (column) to have unit variance.  (This normalization or standardization often improves performance. See [Wikipedia](http://en.wikipedia.org/wiki/Feature_scaling#Standardization) for more info.)

# COMMAND ----------

# Split data into a labels dataframe and a features dataframe
labels = pandasData['price'].values
featureNames = ['carat', 'cut', 'color', 'clarity', 'depth', 'table', 'x', 'y', 'z']
features = pandasData[featureNames].values

# COMMAND ----------

# Normalize features (columns) to have unit variance
from sklearn.preprocessing import normalize
features = normalize(features, axis=0)
features

# COMMAND ----------

# MAGIC %md ### Hold out a random test set
# MAGIC 
# MAGIC We hold out a random sample of the data for testing.  Note that this randomness can cause this notebook to produce different results each time it is run.

# COMMAND ----------

# Hold out 30% of the data for testing.  We will use the rest for training.
from sklearn.model_selection import train_test_split
trainingLabels, testLabels, trainingFeatures, testFeatures = train_test_split(labels, features, test_size=0.3)
ntrain, ntest = len(trainingLabels), len(testLabels)
print('Split data randomly into 2 sets: %d training and %d test instances.' % (ntrain, ntest))

# COMMAND ----------

# MAGIC %md ### Learn an initial model
# MAGIC 
# MAGIC Here, we train a single model using fixed hyperparameters on the driver.  Later, we will do model tuning by training models in a distributed fashion.

# COMMAND ----------

# Train a model with fixed hyperparameters, and print out the intercept and coefficients.
from sklearn import linear_model
origAlpha = 0.5 # "alpha" is the regularization hyperparameter
origClf = linear_model.Ridge(alpha=origAlpha)
origClf.fit(features, labels)
print('Trained model with fixed alpha = %g' % origAlpha)
print('  Model intercept: %g' % origClf.intercept_)
print('  Model coefficients:')
for i in range(len(featureNames)):
  print ('    %g\t%s' % (origClf.coef_[i], featureNames[i]))

# COMMAND ----------

# MAGIC %md One can draw conclusions about the model coefficients and the affect of features.  However, be wary of several issues:
# MAGIC * Feature meaning: Especially if you index or transform features, be careful about how those transformations can change the meaning.  E.g., reversing an index order or negating a numerical feature can "flip" the meaning.
# MAGIC * Model assumptions: The model may not fit the data, in which case interpreting coefficients may be difficult.  E.g., if the data do not correspond to a linear model, the model may learn non-intuitive weights for some features (in its attempt to fit the data as well as possible).

# COMMAND ----------

# MAGIC %md ### Evaluate the initial model
# MAGIC 
# MAGIC We will evaluate this and other models using [scikit-learn's score function](http://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html#sklearn.linear_model.Ridge.score), which computes a value indicating the quality of the model's predictions on data.  A value closer to `1` is better.

# COMMAND ----------

# Score the initial model.  It does not do that well.
origScore = origClf.score(trainingFeatures, trainingLabels)
origScore

# COMMAND ----------

# MAGIC %md ## 2. Distributing scikit-learn jobs
# MAGIC 
# MAGIC Now that we have a basic scikit-learn workflow in Databricks, we can start distributing tasks.  There are several types of tasks one might distribute, such as ETL, parameter tuning, and evaluation.  We demonstrate using Spark to distribute *parameter tuning* below.

# COMMAND ----------

# MAGIC %md ### Parameter tuning using Spark
# MAGIC 
# MAGIC [Parameter tuning](http://en.wikipedia.org/wiki/Hyperparameter_optimization) is the task of tuning (hyper)parameters of a learning or prediction system in order to improve the results.  It is commonly done by training multiple models (each using different parameters) on one set of data and then testing those models on another held-out set of data (and maybe repeating).  By testing on a held-out set not seen during training, we can tune the parameters in a data-driven way while limiting the risk of [overfitting](http://en.wikipedia.org/wiki/Overfitting).
# MAGIC 
# MAGIC In this section, we will use [k-fold cross validation](http://en.wikipedia.org/wiki/Cross-validation_&#40;statistics&#41;), which works as follows:
# MAGIC * Randomly split the data into k equal-sized subsets ("folds").
# MAGIC * For ```i = 1, 2, ..., k```,
# MAGIC   * Hold out fold ```i``` as a validation set.
# MAGIC   * Create a training set by combining all folds except for ```i```.
# MAGIC   * For each set of parameters,
# MAGIC     * Train a model with that set of parameters.
# MAGIC     * Test the model on the validation set to compute a validation error.
# MAGIC * For each set of parameters,
# MAGIC   * Compute the average validation error (averaging over the ```k``` models for this set of parameters).
# MAGIC * Choose the best set of parameters, based on the average validation error.
# MAGIC * Re-train on the entire dataset, using this best set of parameters.
# MAGIC 
# MAGIC Note that for each (fold, parameter set) pair, the task of training a model can be done independently of other folds and parameter sets.  We will parallelize these tasks: scikit-learn will be used on each worker to do the training.  This parallelization is especially helpful since training is the most computationally costly part of this workflow.  If you use `k` folds of cross validation to test `P` different parameter settings, then distributing the task to train 1 model per worker can make it run close to `k*P` times faster!
# MAGIC 
# MAGIC We will also hold out some additional data for testing.  We will use it to demonstrate the worth of careful parameter tuning by comparing:
# MAGIC * Our initial model (with poorly chosen parameters)
# MAGIC * The final model (with carefully tuned parameters)

# COMMAND ----------

# MAGIC %md #### Split data and define tasks to distribute
# MAGIC 
# MAGIC Each distributed task will be a (fold, parameter set) pair.  It will correspond to 1 model we train.

# COMMAND ----------

# We use scikit-learn's model_selection module, which helps split our data randomly into k equal-size parts ("folds").
from sklearn import model_selection
numFolds = 3 # You may want to use more (10 or so) in practice
kf = model_selection.KFold(n_splits=numFolds)

# COMMAND ----------

# "alphas" is a list of hyperparameter values to test
alphas = [0.0, 0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
# Create a list of tasks to distribute
tasks = []
for alpha in alphas:
  for fold in range(numFolds):
    tasks = tasks + [(alpha, fold)]

# COMMAND ----------

# Create an RDD of tasks.  We set the number of partitions equal to the number of tasks to ensure maximum parallelism.
tasksRDD = sc.parallelize(tasks, numSlices = len(tasks))

# COMMAND ----------

# MAGIC %md #### Broadcast dataset
# MAGIC 
# MAGIC If we use a variable in a function (a "closure") run on each worker, Spark will automatically send the dataset to the workers.  This is fine for variables with small values, but for our dataset, we can send it to workers more efficiently by *broadcasting* it.  We now create a *broadcast variable* for our data, which we will use later when running tasks on workers.  For more info on broadcast variables, see the [Spark programming guide](https://spark.apache.org/docs/latest/programming-guide.html#broadcast-variables).

# COMMAND ----------

trainingFeaturesBroadcast = sc.broadcast(trainingFeatures)
trainingLabelsBroadcast = sc.broadcast(trainingLabels)

# COMMAND ----------

# MAGIC %md #### Run cross-validation in parallel
# MAGIC 
# MAGIC We define a function which will run on each worker.  This function takes 1 task (1 hyperparameter alpha value + 1 fold index) and trains the corresponding model.  We then use `RDD.map` to run these tasks in parallel.

# COMMAND ----------

def trainOneModel(alpha, fold):
  """
  Given 1 task (1 hyperparameter alpha value + 1 fold index), train the corresponding model.
  Return: model, score on the fold's test data, task info.
  """
  # Extract indices for this fold
  trainIndex, valIndex = [], []
  fold_ = 0 # index into folds 'kf'

  # Get training data from the broadcast variables
  localTrainingFeatures = trainingFeaturesBroadcast.value
  localTrainingLabels = trainingLabelsBroadcast.value
  
  for trainIndex_, valIndex_ in kf.split(localTrainingFeatures):
    if fold_ == fold:
      trainIndex, valIndex = trainIndex_, valIndex_
      break
    fold_ += 1

  X_train, X_val = localTrainingFeatures[trainIndex], localTrainingFeatures[valIndex]
  Y_train, Y_val = localTrainingLabels[trainIndex], localTrainingLabels[valIndex]
  # Train the model, and score it
  clf = linear_model.Ridge(alpha=alpha)
  clf.fit(X_train, Y_train)
  score = clf.score(X_val, Y_val)
  return clf, score, alpha, fold

# COMMAND ----------

# LEARN!  We now map our tasks RDD and apply the training function to each task.
# After we call an action ("count") on the results, the actual training is executed.
trainedModelAndScores = tasksRDD.map(lambda alpha_fold: trainOneModel(alpha_fold[0], alpha_fold[1]))
trainedModelAndScores.cache()
trainedModelAndScores.count()

# COMMAND ----------

# Since we are done with our broadcast variables, we can clean them up.
# (This will happen automatically, but we can make it happen earlier by explicitly unpersisting the broadcast variables.
trainingFeaturesBroadcast.unpersist()
trainingLabelsBroadcast.unpersist()

# COMMAND ----------

# MAGIC %md #### Collect results to get the best hyperparameter alpha

# COMMAND ----------

# Collect the results.
allScores = trainedModelAndScores.map(lambda x: (x[1], x[2], x[3])).collect()
# Average scores over folds
avgScores = dict(map(lambda alpha: (alpha, 0.0), alphas))
for score, alpha, fold in allScores:
  avgScores[alpha] += score
for alpha in alphas:
  avgScores[alpha] /= numFolds
avgScores

# COMMAND ----------

# MAGIC %md We now have a list of alpha values paired with the corresponding average scores (averaged over the k folds).  Let's identify the best score to discover the best value for alpha.

# COMMAND ----------

# Find best score
bestAlpha = -1
bestScore = -1
for alpha in alphas:
  if avgScores[alpha] > bestScore:
    bestAlpha = alpha
    bestScore = avgScores[alpha]
print('Found best alpha: %g, which gives score: %g' % (bestAlpha, bestScore))

# COMMAND ----------

# MAGIC %md We can also use plotting to examine how the hyperparameter affects performance.

# COMMAND ----------

# Use Databricks' display() function to plot the scores vs. alpha.  We use a namedtuple to tell Databricks names for the columns (alpha and the score).
import numpy
from collections import namedtuple
Score = namedtuple('Score', 'log_alpha score')
df = spark.createDataFrame(map(lambda alpha: Score(float(numpy.log(alpha + 0.00000001)), float(avgScores[alpha])), avgScores)).toDF('log_alpha score','Score')
display(df)

# COMMAND ----------

# MAGIC %md For this dataset, the best alpha is generally small but not the smallest value.  (Remember that the results of this notebook can vary because of randomness in splitting the data.)
# MAGIC 
# MAGIC This demonstrates how parameter tuning can help *a lot*; our score can vary from 0 (terrible) to 0.9 (quite good).

# COMMAND ----------

# MAGIC %md #### Train a final model using the best hyperparameter
# MAGIC 
# MAGIC We use our chosen value of alpha to train a model on the entire training dataset.  Since this is a single training task, we execute it on the driver.

# COMMAND ----------

# Use bestAlpha, and train a final model.
tunedClf = linear_model.Ridge(alpha=bestAlpha)
tunedClf.fit(trainingFeatures, trainingLabels)

# COMMAND ----------

# MAGIC %md Let's compare our original model vs. the final model with tuned hyperparameters.

# COMMAND ----------

origTrainingScore, origTestScore = origClf.score(trainingFeatures, trainingLabels), origClf.score(testFeatures, testLabels)
tunedTrainingScore, tunedTestScore = tunedClf.score(trainingFeatures, trainingLabels), tunedClf.score(testFeatures, testLabels)
print('Compare original model (without hyperparameter tuning) and final model (with tuning) on test data\n')
print('Model   \tAlpha\tTraining   \tTest')
print('Original\t%g\t%g\t%g' % (origAlpha, origTrainingScore, origTestScore))
print('Tuned   \t%g\t%g\t%g' % (bestAlpha, tunedTrainingScore, tunedTestScore))

# COMMAND ----------

# MAGIC %md The tuned model does better! (Note: Performance can vary because of randomness, but it should be better.)

# COMMAND ----------

print('Tuned model with best alpha = %g' % bestAlpha)
print('  Model intercept: %g' % tunedClf.intercept_)
print('  Model coefficients:')
for i in range(len(featureNames)):
  print('    %g\t%s' % (tunedClf.coef_[i], featureNames[i]))