# Databricks notebook source
# MAGIC %md
# MAGIC # Binary Classification Example

# COMMAND ----------

# MAGIC %md
# MAGIC The Pipelines API provides higher-level API built on top of DataFrames for constructing ML pipelines.
# MAGIC You can read more about the Pipelines API in the [programming guide](https://spark.apache.org/docs/latest/ml-guide.html).
# MAGIC 
# MAGIC **Binary Classification** is the task of predicting a binary label.
# MAGIC E.g., is an email spam or not spam? Should I show this ad to this user or not? Will it rain tomorrow or not?
# MAGIC This section demonstrates algorithms for making these types of predictions.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dataset Review

# COMMAND ----------

# MAGIC %md
# MAGIC The Adult dataset we are going to use is publicly available at the [UCI Machine Learning Repository](https://archive.ics.uci.edu/ml/datasets/Adult).
# MAGIC This data derives from census data, and consists of information about 48842 individuals and their annual income.
# MAGIC We will use this information to predict if an individual earns **<=50K or >50k** a year.
# MAGIC The dataset is rather clean, and consists of both numeric and categorical variables.
# MAGIC 
# MAGIC Attribute Information:
# MAGIC 
# MAGIC - age: continuous
# MAGIC - workclass: Private,Self-emp-not-inc, Self-emp-inc, Federal-gov, Local-gov, State-gov, Without-pay, Never-worked
# MAGIC - fnlwgt: continuous
# MAGIC - education: Bachelors, Some-college, 11th, HS-grad, Prof-school, Assoc-acdm, Assoc-voc...
# MAGIC - education-num: continuous
# MAGIC - marital-status: Married-civ-spouse, Divorced, Never-married, Separated, Widowed, Married-spouse-absent...
# MAGIC - occupation: Tech-support, Craft-repair, Other-service, Sales, Exec-managerial, Prof-specialty, Handlers-cleaners...
# MAGIC - relationship: Wife, Own-child, Husband, Not-in-family, Other-relative, Unmarried
# MAGIC - race: White, Asian-Pac-Islander, Amer-Indian-Eskimo, Other, Black
# MAGIC - sex: Female, Male
# MAGIC - capital-gain: continuous
# MAGIC - capital-loss: continuous
# MAGIC - hours-per-week: continuous
# MAGIC - native-country: United-States, Cambodia, England, Puerto-Rico, Canada, Germany...
# MAGIC 
# MAGIC Target/Label: - <=50K, >50K

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Data

# COMMAND ----------

# MAGIC %md
# MAGIC In this example, we will read in the Adult dataset from databricks-datasets.
# MAGIC We'll read in the data in SQL using the CSV data source for Spark and rename the columns appropriately.

# COMMAND ----------

# MAGIC %fs ls databricks-datasets/adult/adult.data

# COMMAND ----------

# MAGIC %fs head databricks-datasets/adult/adult.data

# COMMAND ----------

# MAGIC %sql DROP TABLE IF EXISTS adult

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE TABLE adult (
# MAGIC   age DOUBLE,
# MAGIC   workclass STRING,
# MAGIC   fnlwgt DOUBLE,
# MAGIC   education STRING,
# MAGIC   education_num DOUBLE,
# MAGIC   marital_status STRING,
# MAGIC   occupation STRING,
# MAGIC   relationship STRING,
# MAGIC   race STRING,
# MAGIC   sex STRING,
# MAGIC   capital_gain DOUBLE,
# MAGIC   capital_loss DOUBLE,
# MAGIC   hours_per_week DOUBLE,
# MAGIC   native_country STRING,
# MAGIC   income STRING)
# MAGIC USING CSV
# MAGIC OPTIONS (path "/databricks-datasets/adult/adult.data", header "true")

# COMMAND ----------

dataset = spark.table("adult")
cols = dataset.columns

# COMMAND ----------

display(dataset)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preprocess Data
# MAGIC 
# MAGIC Since we are going to try algorithms like Logistic Regression, we will have to convert the categorical variables in the dataset into numeric variables.
# MAGIC There are 2 ways we can do this.
# MAGIC 
# MAGIC * Category Indexing
# MAGIC 
# MAGIC   This is basically assigning a numeric value to each category from {0, 1, 2, ...numCategories-1}.
# MAGIC   This introduces an implicit ordering among your categories, and is more suitable for ordinal variables (eg: Poor: 0, Average: 1, Good: 2)
# MAGIC 
# MAGIC * One-Hot Encoding
# MAGIC 
# MAGIC   This converts categories into binary vectors with at most one nonzero value (eg: (Blue: [1, 0]), (Green: [0, 1]), (Red: [0, 0]))
# MAGIC 
# MAGIC In this dataset, we have ordinal variables like education (Preschool - Doctorate), and also nominal variables like relationship (Wife, Husband, Own-child, etc).
# MAGIC For simplicity's sake, we will use One-Hot Encoding to convert all categorical variables into binary vectors.
# MAGIC It is possible here to improve prediction accuracy by converting each categorical column with an appropriate method.
# MAGIC 
# MAGIC Here, we will use a combination of [StringIndexer] and [OneHotEncoderEstimator] to convert the categorical variables.
# MAGIC The `OneHotEncoderEstimator` will return a [SparseVector].
# MAGIC 
# MAGIC Since we will have more than 1 stage of feature transformations, we use a [Pipeline] to tie the stages together.
# MAGIC This simplifies our code.
# MAGIC 
# MAGIC [StringIndexer]: http://spark.apache.org/docs/latest/ml-features.html#stringindexer
# MAGIC [OneHotEncoderEstimator]: https://spark.apache.org/docs/latest/ml-features.html#onehotencoderestimator
# MAGIC [SparseVector]: https://spark.apache.org/docs/latest/api/python/pyspark.ml.html#pyspark.ml.linalg.SparseVector
# MAGIC [Pipeline]: http://spark.apache.org/docs/latest/api/python/pyspark.ml.html#pyspark.ml.Pipeline

# COMMAND ----------

from pyspark.ml import Pipeline
from pyspark.ml.feature import OneHotEncoderEstimator, StringIndexer, VectorAssembler
categoricalColumns = ["workclass", "education", "marital_status", "occupation", "relationship", "race", "sex", "native_country"]
stages = [] # stages in our Pipeline
for categoricalCol in categoricalColumns:
    # Category Indexing with StringIndexer
    stringIndexer = StringIndexer(inputCol=categoricalCol, outputCol=categoricalCol + "Index")
    # Use OneHotEncoder to convert categorical variables into binary SparseVectors
    # encoder = OneHotEncoderEstimator(inputCol=categoricalCol + "Index", outputCol=categoricalCol + "classVec")
    encoder = OneHotEncoderEstimator(inputCols=[stringIndexer.getOutputCol()], outputCols=[categoricalCol + "classVec"])
    # Add stages.  These are not run here, but will run all at once later on.
    stages += [stringIndexer, encoder]

# COMMAND ----------

# MAGIC %md
# MAGIC The above code basically indexes each categorical column using the `StringIndexer`,
# MAGIC and then converts the indexed categories into one-hot encoded variables.
# MAGIC The resulting output has the binary vectors appended to the end of each row.
# MAGIC 
# MAGIC We use the `StringIndexer` again to encode our labels to label indices.

# COMMAND ----------

# Convert label into label indices using the StringIndexer
label_stringIdx = StringIndexer(inputCol="income", outputCol="label")
stages += [label_stringIdx]

# COMMAND ----------

# MAGIC %md
# MAGIC Use a `VectorAssembler` to combine all the feature columns into a single vector column.
# MAGIC This includes both the numeric columns and the one-hot encoded binary vector columns in our dataset.

# COMMAND ----------

# Transform all features into a vector using VectorAssembler
numericCols = ["age", "fnlwgt", "education_num", "capital_gain", "capital_loss", "hours_per_week"]
assemblerInputs = [c + "classVec" for c in categoricalColumns] + numericCols
assembler = VectorAssembler(inputCols=assemblerInputs, outputCol="features")
stages += [assembler]

# COMMAND ----------

# MAGIC %md
# MAGIC Run the stages as a Pipeline. This puts the data through all of the feature transformations we described in a single call.

# COMMAND ----------

from pyspark.ml.classification import LogisticRegression
  
partialPipeline = Pipeline().setStages(stages)
pipelineModel = partialPipeline.fit(dataset)
preppedDataDF = pipelineModel.transform(dataset)

# COMMAND ----------

# Fit model to prepped data
lrModel = LogisticRegression().fit(preppedDataDF)

# ROC for training data
display(lrModel, preppedDataDF, "ROC")

# COMMAND ----------

display(lrModel, preppedDataDF)

# COMMAND ----------

# Keep relevant columns
selectedcols = ["label", "features"] + cols
dataset = preppedDataDF.select(selectedcols)
display(dataset)

# COMMAND ----------

### Randomly split data into training and test sets. set seed for reproducibility
(trainingData, testData) = dataset.randomSplit([0.7, 0.3], seed=100)
print(trainingData.count())
print(testData.count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fit and Evaluate Models
# MAGIC 
# MAGIC We are now ready to try out some of the Binary Classification algorithms available in the Pipelines API.
# MAGIC 
# MAGIC Out of these algorithms, the below are also capable of supporting multiclass classification with the Python API:
# MAGIC - Decision Tree Classifier
# MAGIC - Random Forest Classifier
# MAGIC 
# MAGIC These are the general steps we will take to build our models:
# MAGIC - Create initial model using the training set
# MAGIC - Tune parameters with a `ParamGrid` and 5-fold Cross Validation
# MAGIC - Evaluate the best model obtained from the Cross Validation using the test set
# MAGIC 
# MAGIC We use the `BinaryClassificationEvaluator` to evaluate our models, which uses [areaUnderROC] as the default metric.
# MAGIC 
# MAGIC [areaUnderROC]: https://en.wikipedia.org/wiki/Receiver_operating_characteristic#Area_under_the_curve

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC ## Logistic Regression
# MAGIC 
# MAGIC You can read more about [Logistic Regression] from the [classification and regression] section of MLlib Programming Guide.
# MAGIC In the Pipelines API, we are now able to perform Elastic-Net Regularization with Logistic Regression, as well as other linear methods.
# MAGIC 
# MAGIC [classification and regression]: https://spark.apache.org/docs/latest/ml-classification-regression.html
# MAGIC [Logistic Regression]: https://spark.apache.org/docs/latest/ml-classification-regression.html#logistic-regression

# COMMAND ----------

from pyspark.ml.classification import LogisticRegression

# Create initial LogisticRegression model
lr = LogisticRegression(labelCol="label", featuresCol="features", maxIter=10)

# Train model with Training Data
lrModel = lr.fit(trainingData)

# COMMAND ----------

# Make predictions on test data using the transform() method.
# LogisticRegression.transform() will only use the 'features' column.
predictions = lrModel.transform(testData)

# COMMAND ----------

# View model's predictions and probabilities of each prediction class
# You can select any columns in the above schema to view as well. For example's sake we will choose age & occupation
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

# COMMAND ----------

# MAGIC %md
# MAGIC We can use ``BinaryClassificationEvaluator`` to evaluate our model. We can set the required column names in `rawPredictionCol` and `labelCol` Param and the metric in `metricName` Param.

# COMMAND ----------

from pyspark.ml.evaluation import BinaryClassificationEvaluator

# Evaluate model
evaluator = BinaryClassificationEvaluator(rawPredictionCol="rawPrediction")
evaluator.evaluate(predictions)

# COMMAND ----------

# MAGIC %md
# MAGIC Note that the default metric for the ``BinaryClassificationEvaluator`` is ``areaUnderROC``

# COMMAND ----------

evaluator.getMetricName()

# COMMAND ----------

# MAGIC %md
# MAGIC The evaluator currently accepts 2 kinds of metrics - areaUnderROC and areaUnderPR.
# MAGIC We can set it to areaUnderPR by using evaluator.setMetricName("areaUnderPR").
# MAGIC 
# MAGIC Now we will try tuning the model with the ``ParamGridBuilder`` and the ``CrossValidator``.
# MAGIC 
# MAGIC If you are unsure what params are available for tuning, you can use ``explainParams()`` to print a list of all params and their definitions.

# COMMAND ----------

print(lr.explainParams())

# COMMAND ----------

# MAGIC %md
# MAGIC As we indicate 3 values for regParam, 3 values for maxIter, and 2 values for elasticNetParam,
# MAGIC this grid will have 3 x 3 x 3 = 27 parameter settings for CrossValidator to choose from.
# MAGIC We will create a 5-fold cross validator.

# COMMAND ----------

from pyspark.ml.tuning import ParamGridBuilder, CrossValidator

# Create ParamGrid for Cross Validation
paramGrid = (ParamGridBuilder()
             .addGrid(lr.regParam, [0.01, 0.5, 2.0])
             .addGrid(lr.elasticNetParam, [0.0, 0.5, 1.0])
             .addGrid(lr.maxIter, [1, 5, 10])
             .build())

# COMMAND ----------

# Create 5-fold CrossValidator
cv = CrossValidator(estimator=lr, estimatorParamMaps=paramGrid, evaluator=evaluator, numFolds=5)

# Run cross validations
cvModel = cv.fit(trainingData)
# this will likely take a fair amount of time because of the amount of models that we're creating and testing

# COMMAND ----------

# Use test set to measure the accuracy of our model on new data
predictions = cvModel.transform(testData)

# COMMAND ----------

# cvModel uses the best model found from the Cross Validation
# Evaluate best model
evaluator.evaluate(predictions)

# COMMAND ----------

# MAGIC %md
# MAGIC We can also access the model's feature weights and intercepts easily

# COMMAND ----------

print('Model Intercept: ', cvModel.bestModel.intercept)

# COMMAND ----------

weights = cvModel.bestModel.coefficients
weights = [(float(w),) for w in weights]  # convert numpy type to float, and to tuple
weightsDF = sqlContext.createDataFrame(weights, ["Feature Weight"])
display(weightsDF)

# COMMAND ----------

# View best model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Decision Trees
# MAGIC 
# MAGIC You can read more about [Decision Trees](http://spark.apache.org/docs/latest/mllib-decision-tree.html) in the Spark MLLib Programming Guide.
# MAGIC The Decision Trees algorithm is popular because it handles categorical
# MAGIC data and works out of the box with multiclass classification tasks.

# COMMAND ----------

from pyspark.ml.classification import DecisionTreeClassifier

# Create initial Decision Tree Model
dt = DecisionTreeClassifier(labelCol="label", featuresCol="features", maxDepth=3)

# Train model with Training Data
dtModel = dt.fit(trainingData)

# COMMAND ----------

# MAGIC %md
# MAGIC We can extract the number of nodes in our decision tree as well as the
# MAGIC tree depth of our model.

# COMMAND ----------

print("numNodes = ", dtModel.numNodes)
print("depth = ", dtModel.depth)

# COMMAND ----------

display(dtModel)

# COMMAND ----------

# Make predictions on test data using the Transformer.transform() method.
predictions = dtModel.transform(testData)

# COMMAND ----------

predictions.printSchema()

# COMMAND ----------

# View model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

# COMMAND ----------

# MAGIC %md
# MAGIC We will evaluate our Decision Tree model with
# MAGIC `BinaryClassificationEvaluator`.

# COMMAND ----------

from pyspark.ml.evaluation import BinaryClassificationEvaluator
# Evaluate model
evaluator = BinaryClassificationEvaluator()
evaluator.evaluate(predictions)

# COMMAND ----------

# MAGIC %md
# MAGIC Entropy and the Gini coefficient are the supported measures of impurity for Decision Trees. This is ``Gini`` by default. Changing this value is simple, ``model.setImpurity("Entropy")``.

# COMMAND ----------

dt.getImpurity()

# COMMAND ----------

# MAGIC %md
# MAGIC Now we will try tuning the model with the ``ParamGridBuilder`` and the ``CrossValidator``.
# MAGIC 
# MAGIC As we indicate 3 values for maxDepth and 3 values for maxBin, this grid will have 3 x 3 = 9 parameter settings for ``CrossValidator`` to choose from. We will create a 5-fold CrossValidator.

# COMMAND ----------

# Create ParamGrid for Cross Validation
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator
paramGrid = (ParamGridBuilder()
             .addGrid(dt.maxDepth, [1, 2, 6, 10])
             .addGrid(dt.maxBins, [20, 40, 80])
             .build())

# COMMAND ----------

# Create 5-fold CrossValidator
cv = CrossValidator(estimator=dt, estimatorParamMaps=paramGrid, evaluator=evaluator, numFolds=5)

# Run cross validations
cvModel = cv.fit(trainingData)
# Takes ~5 minutes

# COMMAND ----------

print("numNodes = ", cvModel.bestModel.numNodes)
print("depth = ", cvModel.bestModel.depth)

# COMMAND ----------

# Use test set to measure the accuracy of our model on new data
predictions = cvModel.transform(testData)

# COMMAND ----------

# cvModel uses the best model found from the Cross Validation
# Evaluate best model
evaluator.evaluate(predictions)

# COMMAND ----------

# View Best model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Random Forest
# MAGIC 
# MAGIC Random Forests uses an ensemble of trees to improve model accuracy.
# MAGIC You can read more about [Random Forest] from the [classification and regression] section of MLlib Programming Guide.
# MAGIC 
# MAGIC [classification and regression]: https://spark.apache.org/docs/latest/ml-classification-regression.html
# MAGIC [Random Forest]: https://spark.apache.org/docs/latest/ml-classification-regression.html#random-forests

# COMMAND ----------

from pyspark.ml.classification import RandomForestClassifier

# Create an initial RandomForest model.
rf = RandomForestClassifier(labelCol="label", featuresCol="features")

# Train model with Training Data
rfModel = rf.fit(trainingData)

# COMMAND ----------

# Make predictions on test data using the Transformer.transform() method.
predictions = rfModel.transform(testData)

# COMMAND ----------

predictions.printSchema()

# COMMAND ----------

# View model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

# COMMAND ----------

# MAGIC %md
# MAGIC We will evaluate our Random Forest model with `BinaryClassificationEvaluator`.

# COMMAND ----------

from pyspark.ml.evaluation import BinaryClassificationEvaluator

# Evaluate model
evaluator = BinaryClassificationEvaluator()
evaluator.evaluate(predictions)

# COMMAND ----------

# MAGIC %md
# MAGIC Now we will try tuning the model with the ``ParamGridBuilder`` and the ``CrossValidator``.
# MAGIC 
# MAGIC As we indicate 3 values for maxDepth, 2 values for maxBin, and 2 values for numTrees,
# MAGIC this grid will have 3 x 2 x 2 = 12 parameter settings for ``CrossValidator`` to choose from.
# MAGIC We will create a 5-fold ``CrossValidator``.

# COMMAND ----------

# Create ParamGrid for Cross Validation
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator

paramGrid = (ParamGridBuilder()
             .addGrid(rf.maxDepth, [2, 4, 6])
             .addGrid(rf.maxBins, [20, 60])
             .addGrid(rf.numTrees, [5, 20])
             .build())

# COMMAND ----------

# Create 5-fold CrossValidator
cv = CrossValidator(estimator=rf, estimatorParamMaps=paramGrid, evaluator=evaluator, numFolds=5)

# Run cross validations.  This can take about 6 minutes since it is training over 20 trees!
cvModel = cv.fit(trainingData)

# COMMAND ----------

# Use test set here so we can measure the accuracy of our model on new data
predictions = cvModel.transform(testData)

# COMMAND ----------

# cvModel uses the best model found from the Cross Validation
# Evaluate best model
evaluator.evaluate(predictions)

# COMMAND ----------

# View Best model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Make Predictions
# MAGIC As Random Forest gives us the best areaUnderROC value, we will use the bestModel obtained from Random Forest for deployment,
# MAGIC and use it to generate predictions on new data.
# MAGIC In this example, we will simulate this by generating predictions on the entire dataset.

# COMMAND ----------

bestModel = cvModel.bestModel

# COMMAND ----------

# Generate predictions for entire dataset
finalPredictions = bestModel.transform(dataset)

# COMMAND ----------

# Evaluate best model
evaluator.evaluate(finalPredictions)

# COMMAND ----------

# MAGIC %md
# MAGIC In this example, we will also look into predictions grouped by age and occupation.

# COMMAND ----------

finalPredictions.createOrReplaceTempView("finalPredictions")

# COMMAND ----------

# MAGIC %md
# MAGIC In an operational environment, analysts may use a similar machine learning pipeline to obtain predictions on new data, organize it into a table and use it for analysis or lead targeting.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT occupation, prediction, count(*) AS count
# MAGIC FROM finalPredictions
# MAGIC GROUP BY occupation, prediction
# MAGIC ORDER BY occupation

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT age, prediction, count(*) AS count
# MAGIC FROM finalPredictions
# MAGIC GROUP BY age, prediction
# MAGIC ORDER BY age