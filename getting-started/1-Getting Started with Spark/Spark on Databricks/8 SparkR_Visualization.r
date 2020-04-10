# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="text-align: center; line-height: 0; padding-top: 9px;">
# MAGIC   <img src="https://cdn2.hubspot.net/hubfs/438089/docs/training/dblearning-banner.png" alt="Databricks Learning" width="555" height="64">
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC <img src="http://curriculum-release.s3-website-us-west-2.amazonaws.com/images/Apache-Spark-Logo_TM_200px.png" width=80 height=40> <br>
# MAGIC 
# MAGIC # Visualization
# MAGIC 
# MAGIC * Time Estimate: 30 minutes
# MAGIC * Learning Objective:  Understand what data visualization options are supported and what are not supported 
# MAGIC * Main Topic: Illustrations of various visualization techniques
# MAGIC   1.  R base plot
# MAGIC   2.  Lattice
# MAGIC   3.  ggplot 
# MAGIC   4.  Other R libraries
# MAGIC   5.  Databricks built-in visualization
# MAGIC   6.  Databricks Widgets
# MAGIC 
# MAGIC 
# MAGIC 
# MAGIC ## Additional Resources
# MAGIC * **Plot.ly on Databricks**:        https://docs.azuredatabricks.net/user-guide/visualizations/plotly.html

# COMMAND ----------

library(SparkR)

# COMMAND ----------

# MAGIC %md
# MAGIC # Introduction
# MAGIC 
# MAGIC 
# MAGIC Data visualization in SparkR is fundamentally the same as R.   Users can apply any visualization techniques that are compatible with R graphics system. These includes the base R plots and packages such as `graphics`, `grid`, `lattice`, and `ggplots`.  When using Databricks Notebook, users are provided additional visualization capabilities such as `display()` that visualizes the first 1,000 observations, and `widgets` such as textbox, dropdown lists etc.
# MAGIC 
# MAGIC Keep in mind however, SparkR is interface to Spark and by design it facilitates distributed computation on large quantity of data.   Due to the distributed nature of the data and computation,  SparkR does not provide any special functionalities for visulizing entire large dataset . When the data size is large (which often motivates the use of SparkR), users will need to either select a subset of data or compute summary statistics in order to effectively render the visualzation. 
# MAGIC 
# MAGIC You can run RStudio on Spark clusters and you can launch Shiny application from within RStudio.

# COMMAND ----------

# MAGIC %md
# MAGIC # R Base Plots

# COMMAND ----------

options(repr.plot.width = 1000)

# COMMAND ----------

require(stats)
set.seed(14)
x <- rchisq(100, df = 4)

## Comparing data with a model distribution should be done with qqplot()!
qqplot(x, qchisq(ppoints(x), df = 4)); abline(0, 1, col = 2, lty = 2)

## if you really insist on using hist() ... :
hist(x, freq = FALSE, ylim = c(0, 0.2), font=2, main="Histogram of Chi-sq Random Variable", las=1)
curve(dchisq(x, df = 4), col = 2, lty = 2, lwd = 2, add = TRUE)

# COMMAND ----------

# MAGIC %md
# MAGIC # lattice

# COMMAND ----------

head(iris)

# COMMAND ----------

options(repr.plot.height = 500)
# Lattice Examples 
library(lattice) 
attach(iris)
bin.Sepal.Length <- cut(Sepal.Length, breaks=4)
bwplot (~ Sepal.Width | Species * bin.Sepal.Length, main="Sepal Width Distribution by Species and Sepal Length Quartiles")


# COMMAND ----------

attach(mtcars)

# kernel density plots by factor level 
densityplot(~mpg|cyl, 
  	main="Density Plot by Number of Cylinders",
    xlab="Miles per Gallon")

# COMMAND ----------

# MAGIC %md
# MAGIC # ggplot

# COMMAND ----------

library(ggplot2)

# COMMAND ----------

options(repr.plot.height = 600)

# COMMAND ----------

ggplot(as.data.frame(diamonds), aes(x = carat, y = price, color = color)) + geom_point(alpha = 0.2) + facet_grid(.~cut) + theme_bw()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Other R Visualization Libraries

# COMMAND ----------

install.packages("DandEFA", repos = "http://cran.us.r-project.org")
library(DandEFA)
data(timss2011)
timss2011 <- na.omit(timss2011)
dandpal <- rev(rainbow(100, start = 0, end = 0.2))
facl <- factload(timss2011,nfac=5,method="prax",cormeth="spearman")
dandelion(facl,bound=0,mcex=c(1,1.2),palet=dandpal)
facl <- factload(timss2011,nfac=8,method="mle",cormeth="pearson")
dandelion(facl,bound=0,mcex=c(1,1.2),palet=dandpal)

# COMMAND ----------

# MAGIC %md ## Databirkcs built-in visualizations

# COMMAND ----------

library(ggplot2)

# COMMAND ----------

display(diamonds)

# COMMAND ----------

display(iris)

# COMMAND ----------

# MAGIC %md ## Databricks widgets

# COMMAND ----------

require(SparkR)
require(magrittr)
iris.df <- createDataFrame(iris)

# COMMAND ----------

dbutils.widgets.help() # See list of supported widgets

# COMMAND ----------

dbutils.widgets.combobox("species2", "setosa", as.list(as.character(unique(iris$Species))))

# COMMAND ----------

dbutils.widgets.dropdown("species", "setosa", as.list(as.character(unique(iris$Species))))

# COMMAND ----------

iris.df %>% where(.$Species == dbutils.widgets.get("species2")) %>% display

# COMMAND ----------

# MAGIC %md Modify the widget on the top and notce that the cell re-runs and produces new results