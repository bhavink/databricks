***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED*** Using sparklyr in Databricks R Notebooks
***REMOVED*** MAGIC 
***REMOVED*** MAGIC In this notebook we show how you can use sparklyr in Databricks notebooks.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC __NOTE__: You need a cluster running Apache Spark 2.2+ and Scala 2.11 to use sparklyr in Databricks.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Installing sparklyr
***REMOVED*** MAGIC 
***REMOVED*** MAGIC We will be installing the latest version of sparklyr from [CRAN](https://cran.r-project.org/web/packages/sparklyr/index.html).
***REMOVED*** MAGIC This might take couple minutes because it downloads and installs +10 dependencies.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You only need to do installation once on a cluster.
***REMOVED*** MAGIC After installation, all other notebooks attached to that cluster can import and use sparklyr.

***REMOVED*** COMMAND ----------

install.packages("sparklyr")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Load sparklyr package

***REMOVED*** COMMAND ----------

library(sparklyr)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Creating a sparklyr connection
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can use ``"databricks"`` as the connection method in ``spark_connect()`` to establish a sparklyr connection.
***REMOVED*** MAGIC No additional parameters to ``spark_connect()`` are needed,
***REMOVED*** MAGIC nor calling ``spark_install()`` is needed because Spark is already installed on a Databricks cluster.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Note that `sc` is a special name for sparklyr connection.
***REMOVED*** MAGIC Using that variable name you will see Spark progress bars and built-in Spark UI viewers.

***REMOVED*** COMMAND ----------

sc <- spark_connect(method = "databricks")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Using sparklyr and dplyr API
***REMOVED*** MAGIC 
***REMOVED*** MAGIC After setting up the sparklyr connection you can use all the sparklyr API.
***REMOVED*** MAGIC You can import and combine sparklyr with dplyr or MLlib.
***REMOVED*** MAGIC Note that if extension packages include third-party JARs you may need to install those JARs as libraries in your workspace. 

***REMOVED*** COMMAND ----------

library(dplyr)

***REMOVED*** COMMAND ----------

iris_tbl <- copy_to(sc, iris, overwrite = TRUE)

***REMOVED*** COMMAND ----------

src_tbls(sc)

***REMOVED*** COMMAND ----------

iris_tbl %>% count

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** More complex aggregation and visualization

***REMOVED*** COMMAND ----------

***REMOVED*** Changing default plot height 
options(repr.plot.height = 600)

***REMOVED*** COMMAND ----------

iris_summary <- iris_tbl %>% 
  mutate(Sepal_Width = ROUND(Sepal_Width * 2) / 2) %>% ***REMOVED*** Bucketizing Sepal_Width
  group_by(Species, Sepal_Width) %>% 
  summarize(count = n(), Sepal_Length = mean(Sepal_Length), stdev = sd(Sepal_Length)) %>% collect

***REMOVED*** COMMAND ----------

library(ggplot2)

ggplot(iris_summary, aes(Sepal_Width, Sepal_Length, color = Species)) + 
  geom_line(size = 1.2) +
  geom_errorbar(aes(ymin = Sepal_Length - stdev, ymax = Sepal_Length + stdev), width = 0.05) +
  geom_text(aes(label = count), vjust = -0.2, hjust = 1.2, color = "black") +
  theme(legend.position="top")

***REMOVED*** COMMAND ----------

