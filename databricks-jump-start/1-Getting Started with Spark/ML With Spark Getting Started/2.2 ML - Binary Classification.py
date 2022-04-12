***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED*** Binary Classification Example

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC The Pipelines API provides higher-level API built on top of DataFrames for constructing ML pipelines.
***REMOVED*** MAGIC You can read more about the Pipelines API in the [programming guide](https://spark.apache.org/docs/latest/ml-guide.html).
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Binary Classification** is the task of predicting a binary label.
***REMOVED*** MAGIC E.g., is an email spam or not spam? Should I show this ad to this user or not? Will it rain tomorrow or not?
***REMOVED*** MAGIC This section demonstrates algorithms for making these types of predictions.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Dataset Review

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC The Adult dataset we are going to use is publicly available at the [UCI Machine Learning Repository](https://archive.ics.uci.edu/ml/datasets/Adult).
***REMOVED*** MAGIC This data derives from census data, and consists of information about 48842 individuals and their annual income.
***REMOVED*** MAGIC We will use this information to predict if an individual earns **<=50K or >50k** a year.
***REMOVED*** MAGIC The dataset is rather clean, and consists of both numeric and categorical variables.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Attribute Information:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC - age: continuous
***REMOVED*** MAGIC - workclass: Private,Self-emp-not-inc, Self-emp-inc, Federal-gov, Local-gov, State-gov, Without-pay, Never-worked
***REMOVED*** MAGIC - fnlwgt: continuous
***REMOVED*** MAGIC - education: Bachelors, Some-college, 11th, HS-grad, Prof-school, Assoc-acdm, Assoc-voc...
***REMOVED*** MAGIC - education-num: continuous
***REMOVED*** MAGIC - marital-status: Married-civ-spouse, Divorced, Never-married, Separated, Widowed, Married-spouse-absent...
***REMOVED*** MAGIC - occupation: Tech-support, Craft-repair, Other-service, Sales, Exec-managerial, Prof-specialty, Handlers-cleaners...
***REMOVED*** MAGIC - relationship: Wife, Own-child, Husband, Not-in-family, Other-relative, Unmarried
***REMOVED*** MAGIC - race: White, Asian-Pac-Islander, Amer-Indian-Eskimo, Other, Black
***REMOVED*** MAGIC - sex: Female, Male
***REMOVED*** MAGIC - capital-gain: continuous
***REMOVED*** MAGIC - capital-loss: continuous
***REMOVED*** MAGIC - hours-per-week: continuous
***REMOVED*** MAGIC - native-country: United-States, Cambodia, England, Puerto-Rico, Canada, Germany...
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Target/Label: - <=50K, >50K

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Load Data

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC In this example, we will read in the Adult dataset from databricks-datasets.
***REMOVED*** MAGIC We'll read in the data in SQL using the CSV data source for Spark and rename the columns appropriately.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %fs ls databricks-datasets/adult/adult.data

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %fs head databricks-datasets/adult/adult.data

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %sql DROP TABLE IF EXISTS adult

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %sql
***REMOVED*** MAGIC CREATE TABLE adult (
***REMOVED*** MAGIC   age DOUBLE,
***REMOVED*** MAGIC   workclass STRING,
***REMOVED*** MAGIC   fnlwgt DOUBLE,
***REMOVED*** MAGIC   education STRING,
***REMOVED*** MAGIC   education_num DOUBLE,
***REMOVED*** MAGIC   marital_status STRING,
***REMOVED*** MAGIC   occupation STRING,
***REMOVED*** MAGIC   relationship STRING,
***REMOVED*** MAGIC   race STRING,
***REMOVED*** MAGIC   sex STRING,
***REMOVED*** MAGIC   capital_gain DOUBLE,
***REMOVED*** MAGIC   capital_loss DOUBLE,
***REMOVED*** MAGIC   hours_per_week DOUBLE,
***REMOVED*** MAGIC   native_country STRING,
***REMOVED*** MAGIC   income STRING)
***REMOVED*** MAGIC USING CSV
***REMOVED*** MAGIC OPTIONS (path "/databricks-datasets/adult/adult.data", header "true")

***REMOVED*** COMMAND ----------

dataset = spark.table("adult")
cols = dataset.columns

***REMOVED*** COMMAND ----------

display(dataset)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Preprocess Data
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Since we are going to try algorithms like Logistic Regression, we will have to convert the categorical variables in the dataset into numeric variables.
***REMOVED*** MAGIC There are 2 ways we can do this.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC * Category Indexing
***REMOVED*** MAGIC 
***REMOVED*** MAGIC   This is basically assigning a numeric value to each category from {0, 1, 2, ...numCategories-1}.
***REMOVED*** MAGIC   This introduces an implicit ordering among your categories, and is more suitable for ordinal variables (eg: Poor: 0, Average: 1, Good: 2)
***REMOVED*** MAGIC 
***REMOVED*** MAGIC * One-Hot Encoding
***REMOVED*** MAGIC 
***REMOVED*** MAGIC   This converts categories into binary vectors with at most one nonzero value (eg: (Blue: [1, 0]), (Green: [0, 1]), (Red: [0, 0]))
***REMOVED*** MAGIC 
***REMOVED*** MAGIC In this dataset, we have ordinal variables like education (Preschool - Doctorate), and also nominal variables like relationship (Wife, Husband, Own-child, etc).
***REMOVED*** MAGIC For simplicity's sake, we will use One-Hot Encoding to convert all categorical variables into binary vectors.
***REMOVED*** MAGIC It is possible here to improve prediction accuracy by converting each categorical column with an appropriate method.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Here, we will use a combination of [StringIndexer] and [OneHotEncoderEstimator] to convert the categorical variables.
***REMOVED*** MAGIC The `OneHotEncoderEstimator` will return a [SparseVector].
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Since we will have more than 1 stage of feature transformations, we use a [Pipeline] to tie the stages together.
***REMOVED*** MAGIC This simplifies our code.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC [StringIndexer]: http://spark.apache.org/docs/latest/ml-features.html***REMOVED***stringindexer
***REMOVED*** MAGIC [OneHotEncoderEstimator]: https://spark.apache.org/docs/latest/ml-features.html***REMOVED***onehotencoderestimator
***REMOVED*** MAGIC [SparseVector]: https://spark.apache.org/docs/latest/api/python/pyspark.ml.html***REMOVED***pyspark.ml.linalg.SparseVector
***REMOVED*** MAGIC [Pipeline]: http://spark.apache.org/docs/latest/api/python/pyspark.ml.html***REMOVED***pyspark.ml.Pipeline

***REMOVED*** COMMAND ----------

from pyspark.ml import Pipeline
from pyspark.ml.feature import OneHotEncoderEstimator, StringIndexer, VectorAssembler
categoricalColumns = ["workclass", "education", "marital_status", "occupation", "relationship", "race", "sex", "native_country"]
stages = [] ***REMOVED*** stages in our Pipeline
for categoricalCol in categoricalColumns:
    ***REMOVED*** Category Indexing with StringIndexer
    stringIndexer = StringIndexer(inputCol=categoricalCol, outputCol=categoricalCol + "Index")
    ***REMOVED*** Use OneHotEncoder to convert categorical variables into binary SparseVectors
    ***REMOVED*** encoder = OneHotEncoderEstimator(inputCol=categoricalCol + "Index", outputCol=categoricalCol + "classVec")
    encoder = OneHotEncoderEstimator(inputCols=[stringIndexer.getOutputCol()], outputCols=[categoricalCol + "classVec"])
    ***REMOVED*** Add stages.  These are not run here, but will run all at once later on.
    stages += [stringIndexer, encoder]

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC The above code basically indexes each categorical column using the `StringIndexer`,
***REMOVED*** MAGIC and then converts the indexed categories into one-hot encoded variables.
***REMOVED*** MAGIC The resulting output has the binary vectors appended to the end of each row.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC We use the `StringIndexer` again to encode our labels to label indices.

***REMOVED*** COMMAND ----------

***REMOVED*** Convert label into label indices using the StringIndexer
label_stringIdx = StringIndexer(inputCol="income", outputCol="label")
stages += [label_stringIdx]

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC Use a `VectorAssembler` to combine all the feature columns into a single vector column.
***REMOVED*** MAGIC This includes both the numeric columns and the one-hot encoded binary vector columns in our dataset.

***REMOVED*** COMMAND ----------

***REMOVED*** Transform all features into a vector using VectorAssembler
numericCols = ["age", "fnlwgt", "education_num", "capital_gain", "capital_loss", "hours_per_week"]
assemblerInputs = [c + "classVec" for c in categoricalColumns] + numericCols
assembler = VectorAssembler(inputCols=assemblerInputs, outputCol="features")
stages += [assembler]

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC Run the stages as a Pipeline. This puts the data through all of the feature transformations we described in a single call.

***REMOVED*** COMMAND ----------

from pyspark.ml.classification import LogisticRegression
  
partialPipeline = Pipeline().setStages(stages)
pipelineModel = partialPipeline.fit(dataset)
preppedDataDF = pipelineModel.transform(dataset)

***REMOVED*** COMMAND ----------

***REMOVED*** Fit model to prepped data
lrModel = LogisticRegression().fit(preppedDataDF)

***REMOVED*** ROC for training data
display(lrModel, preppedDataDF, "ROC")

***REMOVED*** COMMAND ----------

display(lrModel, preppedDataDF)

***REMOVED*** COMMAND ----------

***REMOVED*** Keep relevant columns
selectedcols = ["label", "features"] + cols
dataset = preppedDataDF.select(selectedcols)
display(dataset)

***REMOVED*** COMMAND ----------

***REMOVED******REMOVED******REMOVED*** Randomly split data into training and test sets. set seed for reproducibility
(trainingData, testData) = dataset.randomSplit([0.7, 0.3], seed=100)
print(trainingData.count())
print(testData.count())

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Fit and Evaluate Models
***REMOVED*** MAGIC 
***REMOVED*** MAGIC We are now ready to try out some of the Binary Classification algorithms available in the Pipelines API.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Out of these algorithms, the below are also capable of supporting multiclass classification with the Python API:
***REMOVED*** MAGIC - Decision Tree Classifier
***REMOVED*** MAGIC - Random Forest Classifier
***REMOVED*** MAGIC 
***REMOVED*** MAGIC These are the general steps we will take to build our models:
***REMOVED*** MAGIC - Create initial model using the training set
***REMOVED*** MAGIC - Tune parameters with a `ParamGrid` and 5-fold Cross Validation
***REMOVED*** MAGIC - Evaluate the best model obtained from the Cross Validation using the test set
***REMOVED*** MAGIC 
***REMOVED*** MAGIC We use the `BinaryClassificationEvaluator` to evaluate our models, which uses [areaUnderROC] as the default metric.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC [areaUnderROC]: https://en.wikipedia.org/wiki/Receiver_operating_characteristic***REMOVED***Area_under_the_curve

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Logistic Regression
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can read more about [Logistic Regression] from the [classification and regression] section of MLlib Programming Guide.
***REMOVED*** MAGIC In the Pipelines API, we are now able to perform Elastic-Net Regularization with Logistic Regression, as well as other linear methods.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC [classification and regression]: https://spark.apache.org/docs/latest/ml-classification-regression.html
***REMOVED*** MAGIC [Logistic Regression]: https://spark.apache.org/docs/latest/ml-classification-regression.html***REMOVED***logistic-regression

***REMOVED*** COMMAND ----------

from pyspark.ml.classification import LogisticRegression

***REMOVED*** Create initial LogisticRegression model
lr = LogisticRegression(labelCol="label", featuresCol="features", maxIter=10)

***REMOVED*** Train model with Training Data
lrModel = lr.fit(trainingData)

***REMOVED*** COMMAND ----------

***REMOVED*** Make predictions on test data using the transform() method.
***REMOVED*** LogisticRegression.transform() will only use the 'features' column.
predictions = lrModel.transform(testData)

***REMOVED*** COMMAND ----------

***REMOVED*** View model's predictions and probabilities of each prediction class
***REMOVED*** You can select any columns in the above schema to view as well. For example's sake we will choose age & occupation
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC We can use ``BinaryClassificationEvaluator`` to evaluate our model. We can set the required column names in `rawPredictionCol` and `labelCol` Param and the metric in `metricName` Param.

***REMOVED*** COMMAND ----------

from pyspark.ml.evaluation import BinaryClassificationEvaluator

***REMOVED*** Evaluate model
evaluator = BinaryClassificationEvaluator(rawPredictionCol="rawPrediction")
evaluator.evaluate(predictions)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC Note that the default metric for the ``BinaryClassificationEvaluator`` is ``areaUnderROC``

***REMOVED*** COMMAND ----------

evaluator.getMetricName()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC The evaluator currently accepts 2 kinds of metrics - areaUnderROC and areaUnderPR.
***REMOVED*** MAGIC We can set it to areaUnderPR by using evaluator.setMetricName("areaUnderPR").
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Now we will try tuning the model with the ``ParamGridBuilder`` and the ``CrossValidator``.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC If you are unsure what params are available for tuning, you can use ``explainParams()`` to print a list of all params and their definitions.

***REMOVED*** COMMAND ----------

print(lr.explainParams())

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC As we indicate 3 values for regParam, 3 values for maxIter, and 2 values for elasticNetParam,
***REMOVED*** MAGIC this grid will have 3 x 3 x 3 = 27 parameter settings for CrossValidator to choose from.
***REMOVED*** MAGIC We will create a 5-fold cross validator.

***REMOVED*** COMMAND ----------

from pyspark.ml.tuning import ParamGridBuilder, CrossValidator

***REMOVED*** Create ParamGrid for Cross Validation
paramGrid = (ParamGridBuilder()
             .addGrid(lr.regParam, [0.01, 0.5, 2.0])
             .addGrid(lr.elasticNetParam, [0.0, 0.5, 1.0])
             .addGrid(lr.maxIter, [1, 5, 10])
             .build())

***REMOVED*** COMMAND ----------

***REMOVED*** Create 5-fold CrossValidator
cv = CrossValidator(estimator=lr, estimatorParamMaps=paramGrid, evaluator=evaluator, numFolds=5)

***REMOVED*** Run cross validations
cvModel = cv.fit(trainingData)
***REMOVED*** this will likely take a fair amount of time because of the amount of models that we're creating and testing

***REMOVED*** COMMAND ----------

***REMOVED*** Use test set to measure the accuracy of our model on new data
predictions = cvModel.transform(testData)

***REMOVED*** COMMAND ----------

***REMOVED*** cvModel uses the best model found from the Cross Validation
***REMOVED*** Evaluate best model
evaluator.evaluate(predictions)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC We can also access the model's feature weights and intercepts easily

***REMOVED*** COMMAND ----------

print('Model Intercept: ', cvModel.bestModel.intercept)

***REMOVED*** COMMAND ----------

weights = cvModel.bestModel.coefficients
weights = [(float(w),) for w in weights]  ***REMOVED*** convert numpy type to float, and to tuple
weightsDF = sqlContext.createDataFrame(weights, ["Feature Weight"])
display(weightsDF)

***REMOVED*** COMMAND ----------

***REMOVED*** View best model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Decision Trees
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can read more about [Decision Trees](http://spark.apache.org/docs/latest/mllib-decision-tree.html) in the Spark MLLib Programming Guide.
***REMOVED*** MAGIC The Decision Trees algorithm is popular because it handles categorical
***REMOVED*** MAGIC data and works out of the box with multiclass classification tasks.

***REMOVED*** COMMAND ----------

from pyspark.ml.classification import DecisionTreeClassifier

***REMOVED*** Create initial Decision Tree Model
dt = DecisionTreeClassifier(labelCol="label", featuresCol="features", maxDepth=3)

***REMOVED*** Train model with Training Data
dtModel = dt.fit(trainingData)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC We can extract the number of nodes in our decision tree as well as the
***REMOVED*** MAGIC tree depth of our model.

***REMOVED*** COMMAND ----------

print("numNodes = ", dtModel.numNodes)
print("depth = ", dtModel.depth)

***REMOVED*** COMMAND ----------

display(dtModel)

***REMOVED*** COMMAND ----------

***REMOVED*** Make predictions on test data using the Transformer.transform() method.
predictions = dtModel.transform(testData)

***REMOVED*** COMMAND ----------

predictions.printSchema()

***REMOVED*** COMMAND ----------

***REMOVED*** View model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC We will evaluate our Decision Tree model with
***REMOVED*** MAGIC `BinaryClassificationEvaluator`.

***REMOVED*** COMMAND ----------

from pyspark.ml.evaluation import BinaryClassificationEvaluator
***REMOVED*** Evaluate model
evaluator = BinaryClassificationEvaluator()
evaluator.evaluate(predictions)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC Entropy and the Gini coefficient are the supported measures of impurity for Decision Trees. This is ``Gini`` by default. Changing this value is simple, ``model.setImpurity("Entropy")``.

***REMOVED*** COMMAND ----------

dt.getImpurity()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC Now we will try tuning the model with the ``ParamGridBuilder`` and the ``CrossValidator``.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC As we indicate 3 values for maxDepth and 3 values for maxBin, this grid will have 3 x 3 = 9 parameter settings for ``CrossValidator`` to choose from. We will create a 5-fold CrossValidator.

***REMOVED*** COMMAND ----------

***REMOVED*** Create ParamGrid for Cross Validation
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator
paramGrid = (ParamGridBuilder()
             .addGrid(dt.maxDepth, [1, 2, 6, 10])
             .addGrid(dt.maxBins, [20, 40, 80])
             .build())

***REMOVED*** COMMAND ----------

***REMOVED*** Create 5-fold CrossValidator
cv = CrossValidator(estimator=dt, estimatorParamMaps=paramGrid, evaluator=evaluator, numFolds=5)

***REMOVED*** Run cross validations
cvModel = cv.fit(trainingData)
***REMOVED*** Takes ~5 minutes

***REMOVED*** COMMAND ----------

print("numNodes = ", cvModel.bestModel.numNodes)
print("depth = ", cvModel.bestModel.depth)

***REMOVED*** COMMAND ----------

***REMOVED*** Use test set to measure the accuracy of our model on new data
predictions = cvModel.transform(testData)

***REMOVED*** COMMAND ----------

***REMOVED*** cvModel uses the best model found from the Cross Validation
***REMOVED*** Evaluate best model
evaluator.evaluate(predictions)

***REMOVED*** COMMAND ----------

***REMOVED*** View Best model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Random Forest
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Random Forests uses an ensemble of trees to improve model accuracy.
***REMOVED*** MAGIC You can read more about [Random Forest] from the [classification and regression] section of MLlib Programming Guide.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC [classification and regression]: https://spark.apache.org/docs/latest/ml-classification-regression.html
***REMOVED*** MAGIC [Random Forest]: https://spark.apache.org/docs/latest/ml-classification-regression.html***REMOVED***random-forests

***REMOVED*** COMMAND ----------

from pyspark.ml.classification import RandomForestClassifier

***REMOVED*** Create an initial RandomForest model.
rf = RandomForestClassifier(labelCol="label", featuresCol="features")

***REMOVED*** Train model with Training Data
rfModel = rf.fit(trainingData)

***REMOVED*** COMMAND ----------

***REMOVED*** Make predictions on test data using the Transformer.transform() method.
predictions = rfModel.transform(testData)

***REMOVED*** COMMAND ----------

predictions.printSchema()

***REMOVED*** COMMAND ----------

***REMOVED*** View model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC We will evaluate our Random Forest model with `BinaryClassificationEvaluator`.

***REMOVED*** COMMAND ----------

from pyspark.ml.evaluation import BinaryClassificationEvaluator

***REMOVED*** Evaluate model
evaluator = BinaryClassificationEvaluator()
evaluator.evaluate(predictions)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC Now we will try tuning the model with the ``ParamGridBuilder`` and the ``CrossValidator``.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC As we indicate 3 values for maxDepth, 2 values for maxBin, and 2 values for numTrees,
***REMOVED*** MAGIC this grid will have 3 x 2 x 2 = 12 parameter settings for ``CrossValidator`` to choose from.
***REMOVED*** MAGIC We will create a 5-fold ``CrossValidator``.

***REMOVED*** COMMAND ----------

***REMOVED*** Create ParamGrid for Cross Validation
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator

paramGrid = (ParamGridBuilder()
             .addGrid(rf.maxDepth, [2, 4, 6])
             .addGrid(rf.maxBins, [20, 60])
             .addGrid(rf.numTrees, [5, 20])
             .build())

***REMOVED*** COMMAND ----------

***REMOVED*** Create 5-fold CrossValidator
cv = CrossValidator(estimator=rf, estimatorParamMaps=paramGrid, evaluator=evaluator, numFolds=5)

***REMOVED*** Run cross validations.  This can take about 6 minutes since it is training over 20 trees!
cvModel = cv.fit(trainingData)

***REMOVED*** COMMAND ----------

***REMOVED*** Use test set here so we can measure the accuracy of our model on new data
predictions = cvModel.transform(testData)

***REMOVED*** COMMAND ----------

***REMOVED*** cvModel uses the best model found from the Cross Validation
***REMOVED*** Evaluate best model
evaluator.evaluate(predictions)

***REMOVED*** COMMAND ----------

***REMOVED*** View Best model's predictions and probabilities of each prediction class
selected = predictions.select("label", "prediction", "probability", "age", "occupation")
display(selected)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Make Predictions
***REMOVED*** MAGIC As Random Forest gives us the best areaUnderROC value, we will use the bestModel obtained from Random Forest for deployment,
***REMOVED*** MAGIC and use it to generate predictions on new data.
***REMOVED*** MAGIC In this example, we will simulate this by generating predictions on the entire dataset.

***REMOVED*** COMMAND ----------

bestModel = cvModel.bestModel

***REMOVED*** COMMAND ----------

***REMOVED*** Generate predictions for entire dataset
finalPredictions = bestModel.transform(dataset)

***REMOVED*** COMMAND ----------

***REMOVED*** Evaluate best model
evaluator.evaluate(finalPredictions)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC In this example, we will also look into predictions grouped by age and occupation.

***REMOVED*** COMMAND ----------

finalPredictions.createOrReplaceTempView("finalPredictions")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC In an operational environment, analysts may use a similar machine learning pipeline to obtain predictions on new data, organize it into a table and use it for analysis or lead targeting.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %sql
***REMOVED*** MAGIC SELECT occupation, prediction, count(*) AS count
***REMOVED*** MAGIC FROM finalPredictions
***REMOVED*** MAGIC GROUP BY occupation, prediction
***REMOVED*** MAGIC ORDER BY occupation

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %sql
***REMOVED*** MAGIC SELECT age, prediction, count(*) AS count
***REMOVED*** MAGIC FROM finalPredictions
***REMOVED*** MAGIC GROUP BY age, prediction
***REMOVED*** MAGIC ORDER BY age