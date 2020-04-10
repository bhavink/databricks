# Databricks notebook source
# MAGIC %md # Using sparklyr in Databricks R Notebooks
# MAGIC 
# MAGIC In this notebook we show how you can use sparklyr in Databricks notebooks.
# MAGIC 
# MAGIC __NOTE__: You need a cluster running Apache Spark 2.2+ and Scala 2.11 to use sparklyr in Databricks.

# COMMAND ----------

# MAGIC %md ## Installing sparklyr
# MAGIC 
# MAGIC We will be installing the latest version of sparklyr from [CRAN](https://cran.r-project.org/web/packages/sparklyr/index.html).
# MAGIC This might take couple minutes because it downloads and installs +10 dependencies.
# MAGIC 
# MAGIC You only need to do installation once on a cluster.
# MAGIC After installation, all other notebooks attached to that cluster can import and use sparklyr.

# COMMAND ----------

# Installing latest version of Rcpp
install.packages("Rcpp") 

if (!require("sparklyr")) {
  install.packages("sparklyr")  
}

# COMMAND ----------

# MAGIC %md ## Load sparklyr package

# COMMAND ----------

library(sparklyr)

# COMMAND ----------

# MAGIC %md ## Creating a sparklyr connection
# MAGIC 
# MAGIC You can use ``"databricks"`` as the connection method in ``spark_connect()`` to establish a sparklyr connection.
# MAGIC No additional parameters to ``spark_connect()`` are needed,
# MAGIC nor calling ``spark_install()`` is needed because Spark is already installed on a Databricks cluster.
# MAGIC 
# MAGIC Note that `sc` is a special name for sparklyr connection.
# MAGIC Using that variable name you will see Spark progress bars and built-in Spark UI viewers.

# COMMAND ----------

sc <- spark_connect(method = "databricks")

# COMMAND ----------

# MAGIC %md ## Using sparklyr and dplyr API
# MAGIC 
# MAGIC After setting up the sparklyr connection you can use all the sparklyr API.
# MAGIC You can import and combine sparklyr with dplyr or MLlib.
# MAGIC Note that if extension packages include third-party JARs you may need to install those JARs as libraries in your workspace. 

# COMMAND ----------

library(dplyr)

# COMMAND ----------

iris_tbl <- copy_to(sc, iris)

# COMMAND ----------

src_tbls(sc)

# COMMAND ----------

iris_tbl %>% count

# COMMAND ----------

# MAGIC %md ### More complex aggregation and visualization

# COMMAND ----------

# Changing default plot height 
options(repr.plot.height = 600)

# COMMAND ----------

iris_summary <- iris_tbl %>% 
  mutate(Sepal_Width = ROUND(Sepal_Width * 2) / 2) %>% # Bucketizing Sepal_Width
  group_by(Species, Sepal_Width) %>% 
  summarize(count = n(), Sepal_Length_Mean = mean(Sepal_Length), stdev = sd(Sepal_Length)) %>% collect

# COMMAND ----------

library(ggplot2)

ggplot(iris_summary, aes(Sepal_Width, Sepal_Length_Mean, color = Species)) + 
  geom_line(size = 1.2) +
  geom_errorbar(aes(ymin = Sepal_Length_Mean - stdev, ymax = Sepal_Length_Mean + stdev), width = 0.05) +
  geom_text(aes(label = count), vjust = -0.2, hjust = 1.2, color = "black") +
  theme(legend.position="top")