***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md-sandbox
***REMOVED*** MAGIC <div style="text-align: center; line-height: 0; padding-top: 9px;">
***REMOVED*** MAGIC   <img src="https://cdn2.hubspot.net/hubfs/438089/docs/training/dblearning-banner.png" alt="Databricks Learning" width="555" height="64">
***REMOVED*** MAGIC </div>

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC <img src="http://curriculum-release.s3-website-us-west-2.amazonaws.com/images/Apache-Spark-Logo_TM_200px.png" width=80 height=40> <br>
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED*** Visualization
***REMOVED*** MAGIC 
***REMOVED*** MAGIC * Time Estimate: 30 minutes
***REMOVED*** MAGIC * Learning Objective:  Understand what data visualization options are supported and what are not supported 
***REMOVED*** MAGIC * Main Topic: Illustrations of various visualization techniques
***REMOVED*** MAGIC   1.  R base plot
***REMOVED*** MAGIC   2.  Lattice
***REMOVED*** MAGIC   3.  ggplot 
***REMOVED*** MAGIC   4.  Other R libraries
***REMOVED*** MAGIC   5.  Databricks built-in visualization
***REMOVED*** MAGIC   6.  Databricks Widgets
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Additional Resources
***REMOVED*** MAGIC * **Plot.ly on Databricks**:        https://docs.azuredatabricks.net/user-guide/visualizations/plotly.html

***REMOVED*** COMMAND ----------

library(SparkR)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED*** Introduction
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Data visualization in SparkR is fundamentally the same as R.   Users can apply any visualization techniques that are compatible with R graphics system. These includes the base R plots and packages such as `graphics`, `grid`, `lattice`, and `ggplots`.  When using Databricks Notebook, users are provided additional visualization capabilities such as `display()` that visualizes the first 1,000 observations, and `widgets` such as textbox, dropdown lists etc.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Keep in mind however, SparkR is interface to Spark and by design it facilitates distributed computation on large quantity of data.   Due to the distributed nature of the data and computation,  SparkR does not provide any special functionalities for visulizing entire large dataset . When the data size is large (which often motivates the use of SparkR), users will need to either select a subset of data or compute summary statistics in order to effectively render the visualzation. 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can run RStudio on Spark clusters and you can launch Shiny application from within RStudio.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED*** R Base Plots

***REMOVED*** COMMAND ----------

options(repr.plot.width = 1000)

***REMOVED*** COMMAND ----------

require(stats)
set.seed(14)
x <- rchisq(100, df = 4)

***REMOVED******REMOVED*** Comparing data with a model distribution should be done with qqplot()!
qqplot(x, qchisq(ppoints(x), df = 4)); abline(0, 1, col = 2, lty = 2)

***REMOVED******REMOVED*** if you really insist on using hist() ... :
hist(x, freq = FALSE, ylim = c(0, 0.2), font=2, main="Histogram of Chi-sq Random Variable", las=1)
curve(dchisq(x, df = 4), col = 2, lty = 2, lwd = 2, add = TRUE)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED*** lattice

***REMOVED*** COMMAND ----------

head(iris)

***REMOVED*** COMMAND ----------

options(repr.plot.height = 500)
***REMOVED*** Lattice Examples 
library(lattice) 
attach(iris)
bin.Sepal.Length <- cut(Sepal.Length, breaks=4)
bwplot (~ Sepal.Width | Species * bin.Sepal.Length, main="Sepal Width Distribution by Species and Sepal Length Quartiles")


***REMOVED*** COMMAND ----------

attach(mtcars)

***REMOVED*** kernel density plots by factor level 
densityplot(~mpg|cyl, 
  	main="Density Plot by Number of Cylinders",
    xlab="Miles per Gallon")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED*** ggplot

***REMOVED*** COMMAND ----------

library(ggplot2)

***REMOVED*** COMMAND ----------

options(repr.plot.height = 600)

***REMOVED*** COMMAND ----------

ggplot(as.data.frame(diamonds), aes(x = carat, y = price, color = color)) + geom_point(alpha = 0.2) + facet_grid(.~cut) + theme_bw()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED*** Other R Visualization Libraries

***REMOVED*** COMMAND ----------

install.packages("DandEFA", repos = "http://cran.us.r-project.org")
library(DandEFA)
data(timss2011)
timss2011 <- na.omit(timss2011)
dandpal <- rev(rainbow(100, start = 0, end = 0.2))
facl <- factload(timss2011,nfac=5,method="prax",cormeth="spearman")
dandelion(facl,bound=0,mcex=c(1,1.2),palet=dandpal)
facl <- factload(timss2011,nfac=8,method="mle",cormeth="pearson")
dandelion(facl,bound=0,mcex=c(1,1.2),palet=dandpal)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Databirkcs built-in visualizations

***REMOVED*** COMMAND ----------

library(ggplot2)

***REMOVED*** COMMAND ----------

display(diamonds)

***REMOVED*** COMMAND ----------

display(iris)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Databricks widgets

***REMOVED*** COMMAND ----------

require(SparkR)
require(magrittr)
iris.df <- createDataFrame(iris)

***REMOVED*** COMMAND ----------

dbutils.widgets.help() ***REMOVED*** See list of supported widgets

***REMOVED*** COMMAND ----------

dbutils.widgets.combobox("species2", "setosa", as.list(as.character(unique(iris$Species))))

***REMOVED*** COMMAND ----------

dbutils.widgets.dropdown("species", "setosa", as.list(as.character(unique(iris$Species))))

***REMOVED*** COMMAND ----------

iris.df %>% where(.$Species == dbutils.widgets.get("species2")) %>% display

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Modify the widget on the top and notce that the cell re-runs and produces new results