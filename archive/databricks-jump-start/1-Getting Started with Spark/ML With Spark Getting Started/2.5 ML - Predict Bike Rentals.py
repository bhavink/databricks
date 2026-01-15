***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED*** Machine Learning (ML) Pipelines
***REMOVED*** MAGIC  

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Analyzing a bike sharing dataset
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This Python notebook demonstrates creating an ML Pipeline to preprocess a dataset, train a Machine Learning model, and make predictions.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Data**: The dataset contains bike rental info from 2011 and 2012 in the Capital bikeshare system, plus additional relevant information such as weather.  This dataset is from Fanaee-T and Gama (2013) and is hosted by the [UCI Machine Learning Repository](http://archive.ics.uci.edu/ml/datasets/Bike+Sharing+Dataset).
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Goal**: We want to learn to predict bike rental counts (per hour) from information such as day of the week, weather, season, etc.  Having good predictions of customer demand allows a business or service to prepare and increase supply as needed.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Approach**: We will use Spark ML Pipelines, which help users piece together parts of a workflow such as feature processing and model training.  We will also demonstrate [model selection (a.k.a. hyperparameter tuning)](https://en.wikipedia.org/wiki/Model_selection) using [Cross Validation](https://en.wikipedia.org/wiki/Cross-validation_&***REMOVED***40;statistics&***REMOVED***41;) in order to fine-tune and improve our ML model.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Load and understand the data
***REMOVED*** MAGIC 
***REMOVED*** MAGIC We begin by loading our data, which is stored in [comma-separated value (CSV) format](https://en.wikipedia.org/wiki/Comma-separated_values).  For that, we use the CSV datasource for Spark, which creates a [Spark DataFrame](http://spark.apache.org/docs/latest/sql-programming-guide.html) containing the dataset.  We also cache the data so that we only read it from disk once.

***REMOVED*** COMMAND ----------

from __future__ import print_function

***REMOVED*** COMMAND ----------

***REMOVED*** We use the sqlContext.read method to read the data and set a few options:
***REMOVED***  'format': specifies the Spark CSV data source
***REMOVED***  'header': set to true to indicate that the first line of the CSV data file is a header
***REMOVED*** The file is called 'hour.csv'.
df = spark.read.csv("/databricks-datasets/bikeSharing/data-001/hour.csv", header="true", inferSchema="true")
***REMOVED*** Calling cache on the DataFrame will make sure we persist it in memory the first time it is used.
***REMOVED*** The following uses will be able to read from memory, instead of re-reading the data from disk.
df.cache()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Data description
***REMOVED*** MAGIC 
***REMOVED*** MAGIC From the [UCI ML Repository description](http://archive.ics.uci.edu/ml/datasets/Bike+Sharing+Dataset), we know that the columns have the following meanings.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Feature columns**:
***REMOVED*** MAGIC * dteday: date
***REMOVED*** MAGIC * season: season (1:spring, 2:summer, 3:fall, 4:winter)
***REMOVED*** MAGIC * yr: year (0:2011, 1:2012)
***REMOVED*** MAGIC * mnth: month (1 to 12)
***REMOVED*** MAGIC * hr: hour (0 to 23)
***REMOVED*** MAGIC * holiday: whether day is holiday or not
***REMOVED*** MAGIC * weekday: day of the week
***REMOVED*** MAGIC * workingday: if day is neither weekend nor holiday is 1, otherwise is 0.
***REMOVED*** MAGIC * weathersit: 
***REMOVED*** MAGIC   * 1: Clear, Few clouds, Partly cloudy, Partly cloudy
***REMOVED*** MAGIC   * 2: Mist + Cloudy, Mist + Broken clouds, Mist + Few clouds, Mist
***REMOVED*** MAGIC   * 3: Light Snow, Light Rain + Thunderstorm + Scattered clouds, Light Rain + Scattered clouds
***REMOVED*** MAGIC   * 4: Heavy Rain + Ice Pallets + Thunderstorm + Mist, Snow + Fog
***REMOVED*** MAGIC * temp: Normalized temperature in Celsius. The values are derived via `(t-t_min)/(t_max-t_min)`, `t_min=-8`, `t_max=+39` (only in hourly scale)
***REMOVED*** MAGIC * atemp: Normalized feeling temperature in Celsius. The values are derived via `(t-t_min)/(t_max-t_min)`, `t_min=-16`, `t_max=+50` (only in hourly scale)
***REMOVED*** MAGIC * hum: Normalized humidity. The values are divided to 100 (max)
***REMOVED*** MAGIC * windspeed: Normalized wind speed. The values are divided to 67 (max)
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Label columns**:
***REMOVED*** MAGIC * casual: count of casual users
***REMOVED*** MAGIC * registered: count of registered users
***REMOVED*** MAGIC * cnt: count of total rental bikes including both casual and registered
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Extraneous columns**:
***REMOVED*** MAGIC * instant: record index
***REMOVED*** MAGIC 
***REMOVED*** MAGIC For example, the first row is a record of hour 0 on January 1, 2011---and apparently 16 people rented bikes around midnight!

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md We can call `display()` on a DataFrame in Databricks to see a sample of the data.

***REMOVED*** COMMAND ----------

display(df)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md This dataset is nicely prepared for Machine Learning: values such as weekday are already indexed, and all of the columns except for the date (`dteday`) are numeric.

***REMOVED*** COMMAND ----------

print("Our dataset has %d rows." % df.count())

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Preprocess data
***REMOVED*** MAGIC 
***REMOVED*** MAGIC So what do we need to do to get our data ready for Machine Learning?
***REMOVED*** MAGIC 
***REMOVED*** MAGIC *Recall our goal*: We want to learn to predict the count of bike rentals (the `cnt` column).  We refer to the count as our target "label".
***REMOVED*** MAGIC 
***REMOVED*** MAGIC *Features*: What can we use as features (info describing each row) to predict the `cnt` label?  We can use the rest of the columns, with a few exceptions:
***REMOVED*** MAGIC * Some of the columns contain duplicate information.  For example, the `cnt` column we want to predict equals the sum of the `casual` + `registered` columns.  We will remove the `casual` and `registered` columns from the data to make sure we do not use them to predict `cnt`.  (*Warning: This is a danger in careless Machine Learning.  Make sure you do not "cheat" by using information you will not have when making predictions.  In this prediction task, we will not have `casual` or `registered` info available when we want to make predictions about the future.*)
***REMOVED*** MAGIC * date column `dteday`: We could keep it, but it is well-represented by the other date-related columns `season`, `yr`, `mnth`, and `weekday`.  We will discard it.
***REMOVED*** MAGIC * row index column `instant`: This is a useless column to us.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Terminology: *Examples* are rows of our dataset.  Each example contains the label to predict, plus features describing it.

***REMOVED*** COMMAND ----------

df = df.drop("instant").drop("dteday").drop("casual").drop("registered")
display(df)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Now that we have the columns we care about, let's print the schema of our dataset to see the type of each column.

***REMOVED*** COMMAND ----------

df.printSchema()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md The DataFrame is currently using strings, but we know all columns are numeric.  Let's cast them.

***REMOVED*** COMMAND ----------

***REMOVED*** The following call takes all columns (df.columns) and casts them using Spark SQL to a numeric type (DoubleType).
from pyspark.sql.functions import col  ***REMOVED*** for indicating a column using a string in the line below
df = df.select([col(c).cast("double").alias(c) for c in df.columns])
df.printSchema()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Split data into training and test sets
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Our final data preparation step will split our dataset into separate training and test sets.  We can train and tune our model as much as we like on the training set, as long as we do not look at the test set.  After we have a good model (based on the training set), we can validate it on the held-out test set in order to know with high confidence our well our model will make predictions on future (unseen) data.

***REMOVED*** COMMAND ----------

***REMOVED*** Split the dataset randomly into 70% for training and 30% for testing.
train, test = df.randomSplit([0.7, 0.3])
print("We have %d training examples and %d test examples." % (train.count(), test.count()))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Visualize our data
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Now that we have preprocessed our features and prepared a training dataset, we can quickly visualize our data to get a sense of whether the features are meaningful.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Calling `display()` on a DataFrame in Databricks and clicking the plot icon below the table will let you draw and pivot various plots.  See the [Visualizations section of the Databricks Guide](https://docs.databricks.com/user-guide/visualizations/index.html) for more ideas.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC In the below plot, we compare bike rental counts versus hour of the day.  As one might expect, rentals are low during the night, and they peak in the morning (8am) and in the early evening (6pm).  This indicates the `hr` feature is useful and can help us predict our label `cnt`.  On your own, you can try visualizing other features to get a sense of how useful they are in this task.

***REMOVED*** COMMAND ----------

display(train.select("hr", "cnt"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Train a Machine Learning Pipeline
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Now that we have understood our data and prepared it as a DataFrame with numeric values, let's learn an ML model to predict bike sharing rentals in the future.  Most ML algorithms expect to predict a single "label" column (`cnt` for our dataset) using a single "features" column of feature vectors.  For each row in our data, the feature vector should describe what we know: weather, day of the week, etc., and the label should be what we want to predict (`cnt`).
***REMOVED*** MAGIC 
***REMOVED*** MAGIC We will put together a simple Pipeline with the following stages:
***REMOVED*** MAGIC * `VectorAssembler`: Assemble the feature columns into a feature vector.
***REMOVED*** MAGIC * `VectorIndexer`: Identify columns which should be treated as categorical.  This is done heuristically, identifying any column with a small number of distinct values as being categorical.  For us, this will be the `yr` (2 values), `season` (4 values), `holiday` (2 values), `workingday` (2 values), and `weathersit` (4 values).
***REMOVED*** MAGIC * `GBTRegressor`: This will use the [Gradient-Boosted Trees (GBT)](https://en.wikipedia.org/wiki/Gradient_boosting) algorithm to learn how to predict rental counts from the feature vectors.
***REMOVED*** MAGIC * `CrossValidator`: The GBT algorithm has several [hyperparameters](https://en.wikipedia.org/wiki/Hyperparameter_optimization), and tuning them to our data can improve accuracy.  We will do this tuning using Spark's [Cross Validation](https://en.wikipedia.org/wiki/Cross-validation_&***REMOVED***40;statistics&***REMOVED***41;) framework, which automatically tests a grid of hyperparameters and chooses the best.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![Image of Pipeline](http://training.databricks.com/databricks_guide/1-init.png)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md First, we define the feature processing stages of the Pipeline:
***REMOVED*** MAGIC * Assemble feature columns into a feature vector.
***REMOVED*** MAGIC * Identify categorical features, and index them.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![Image of feature processing](http://training.databricks.com/databricks_guide/2-features.png)

***REMOVED*** COMMAND ----------

from pyspark.ml.feature import VectorAssembler, VectorIndexer
featuresCols = df.columns
featuresCols.remove('cnt')
***REMOVED*** This concatenates all feature columns into a single feature vector in a new column "rawFeatures".
vectorAssembler = VectorAssembler(inputCols=featuresCols, outputCol="rawFeatures")
***REMOVED*** This identifies categorical features and indexes them.
vectorIndexer = VectorIndexer(inputCol="rawFeatures", outputCol="features", maxCategories=4)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Second, we define the model training stage of the Pipeline. `GBTRegressor` takes feature vectors and labels as input and learns to predict labels of new examples.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![RF image](http://training.databricks.com/databricks_guide/3-gbt.png)

***REMOVED*** COMMAND ----------

from pyspark.ml.regression import GBTRegressor
***REMOVED*** Takes the "features" column and learns to predict "cnt"
gbt = GBTRegressor(labelCol="cnt")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Third, we wrap the model training stage within a `CrossValidator` stage.  `CrossValidator` knows how to call the GBT algorithm with different hyperparameter settings.  It will train multiple models and choose the best one, based on minimizing some metric.  In this example, our metric is [Root Mean Squared Error (RMSE)](https://en.wikipedia.org/wiki/Root-mean-square_deviation).
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![Image of CV](http://training.databricks.com/databricks_guide/4-cv.png)

***REMOVED*** COMMAND ----------

from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.ml.evaluation import RegressionEvaluator
***REMOVED*** Define a grid of hyperparameters to test:
***REMOVED***  - maxDepth: max depth of each decision tree in the GBT ensemble
***REMOVED***  - maxIter: iterations, i.e., number of trees in each GBT ensemble
***REMOVED*** In this example notebook, we keep these values small.  In practice, to get the highest accuracy, you would likely want to try deeper trees (10 or higher) and more trees in the ensemble (>100).
paramGrid = ParamGridBuilder()\
  .addGrid(gbt.maxDepth, [2, 5])\
  .addGrid(gbt.maxIter, [10, 100])\
  .build()
***REMOVED*** We define an evaluation metric.  This tells CrossValidator how well we are doing by comparing the true labels with predictions.
evaluator = RegressionEvaluator(metricName="rmse", labelCol=gbt.getLabelCol(), predictionCol=gbt.getPredictionCol())
***REMOVED*** Declare the CrossValidator, which runs model tuning for us.
cv = CrossValidator(estimator=gbt, evaluator=evaluator, estimatorParamMaps=paramGrid)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Finally, we can tie our feature processing and model training stages together into a single `Pipeline`.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![Image of Pipeline](http://training.databricks.com/databricks_guide/5-pipeline.png)

***REMOVED*** COMMAND ----------

from pyspark.ml import Pipeline
pipeline = Pipeline(stages=[vectorAssembler, vectorIndexer, cv])

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Train the Pipeline!
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Now that we have set up our workflow, we can train the Pipeline in a single call.  Calling `fit()` will run feature processing, model tuning, and training in a single call.  We get back a fitted Pipeline with the best model found.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***Note***: This next cell can take up to **10 minutes**.  This is because it is training *a lot* of trees:
***REMOVED*** MAGIC * For each random sample of data in Cross Validation,
***REMOVED*** MAGIC   * For each setting of the hyperparameters,
***REMOVED*** MAGIC     * `CrossValidator` is training a separate GBT ensemble which contains many Decision Trees.

***REMOVED*** COMMAND ----------

pipelineModel = pipeline.fit(train)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Make predictions, and evaluate results
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Our final step will be to use our fitted model to make predictions on new data.  We will use our held-out test set, but you could also use this model to make predictions on completely new data.  For example, if we created some features data based on weather predictions for the next week, we could predict bike rentals expected during the next week!
***REMOVED*** MAGIC 
***REMOVED*** MAGIC We will also evaluate our predictions.  Computing evaluation metrics is important for understanding the quality of predictions, as well as for comparing models and tuning parameters.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Calling `transform()` on a new dataset passes that data through feature processing and uses the fitted model to make predictions.  We get back a DataFrame with a new column `predictions` (as well as intermediate results such as our `rawFeatures` column from feature processing).

***REMOVED*** COMMAND ----------

predictions = pipelineModel.transform(test)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md It is easier to view the results when we limit the columns displayed to:
***REMOVED*** MAGIC * `cnt`: the true count of bike rentals
***REMOVED*** MAGIC * `prediction`: our predicted count of bike rentals
***REMOVED*** MAGIC * feature columns: our original (human-readable) feature columns

***REMOVED*** COMMAND ----------

display(predictions.select("cnt", "prediction", *featuresCols))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Are these good results?  They are not perfect, but you can see correlation between the counts and predictions.  And there is room to improve---see the next section for ideas to take you further!
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Before we continue, we give two tips on understanding results:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **(1) Metrics**: Manually viewing the predictions gives intuition about accuracy, but it can be useful to have a more concrete metric.  Below, we compute an evaluation metric which tells us how well our model makes predictions on all of our data.  In this case (for [RMSE](https://en.wikipedia.org/wiki/Root-mean-square_deviation)), lower is better.  This metric does not mean much on its own, but it can be used to compare different models.  (This is what `CrossValidator` does internally.)

***REMOVED*** COMMAND ----------

rmse = evaluator.evaluate(predictions)
print("RMSE on our test set: %g" % rmse)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md **(2) Visualization**: Plotting predictions vs. features can help us make sure that the model "understands" the input features and is using them properly to make predictions.  Below, we can see that the model predictions are correlated with the hour of the day, just like the true labels were.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC *Note: For more expert ML usage, check out other Databricks guides on plotting residuals, which compare predictions vs. true labels.*

***REMOVED*** COMMAND ----------

display(predictions.select("hr", "prediction"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Improving our model
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You are not done yet!  This section describes how to take this notebook and improve the results even more.  Try copying this notebook into your Databricks account and extending it, and see how much you can improve the predictions.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC There are several ways we could further improve our model:
***REMOVED*** MAGIC * **Expert knowledge**: We may not be experts on bike sharing programs, but we know a few things we can use:
***REMOVED*** MAGIC   * The count of rentals cannot be negative.  `GBTRegressor` does not know that, but we could threshold the predictions to be `>= 0` post-hoc.
***REMOVED*** MAGIC   * The count of rentals is the sum of `registered` and `casual` rentals.  These two counts may have different behavior.  (Frequent cyclists and casual cyclists probably rent bikes for different reasons.)  The best models for this dataset take this into account.  Try training one GBT model for `registered` and one for `casual`, and then add their predictions together to get the full prediction.
***REMOVED*** MAGIC * **Better tuning**: To make this notebook run quickly, we only tried a few hyperparameter settings.  To get the most out of our data, we should test more settings.  Start by increasing the number of trees in our GBT model by setting `maxIter=200`; it will take longer to train but can be more accurate.
***REMOVED*** MAGIC * **Feature engineering**: We used the basic set of features given to us, but we could potentially improve them.  For example, we may guess that weather is more or less important depending on whether or not it is a workday vs. weekend.  To take advantage of that, we could build a few feature by combining those two base features.  MLlib provides a suite of feature transformers; find out more in the [ML guide](http://spark.apache.org/docs/latest/ml-features.html).
***REMOVED*** MAGIC 
***REMOVED*** MAGIC *Good luck!*

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Learning more
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Check out the other example notebooks in this guide for more ideas about Pipelines, working with datasets, and more.