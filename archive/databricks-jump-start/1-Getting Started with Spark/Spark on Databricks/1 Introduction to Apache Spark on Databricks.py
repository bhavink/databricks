# Databricks notebook source
# MAGIC %md
# MAGIC 
# MAGIC # A Gentle Introduction to Apache Spark on Databricks
# MAGIC 
# MAGIC ** Welcome to Databricks! **
# MAGIC 
# MAGIC This notebook is intended to be the first step in your process to learn more about how to best use Apache Spark on Databricks together. We'll be walking through the core concepts, the fundamental abstractions, and the tools at your disposal. This notebook will teach the fundamental concepts and best practices directly from those that have written Apache Spark and know it best.
# MAGIC 
# MAGIC First, it's worth defining Databricks. Databricks is a managed platform for running Apache Spark - that means that you do not have to learn complex cluster management concepts nor perform tedious maintenance tasks to take advantage of Spark. Databricks also provides a host of features to help its users be more productive with Spark. It's a point and click platform for those that prefer a user interface like data scientists or data analysts. However, this UI is accompanied by a sophisticated API for those that want to automate aspects of their data workloads with automated jobs. To meet the needs of enterprises, Databricks also includes features such as role-based access control and other intelligent optimizations that not only improve usability for users but also reduce costs and complexity for administrators.
# MAGIC 
# MAGIC ** The Gentle Introduction Series **
# MAGIC 
# MAGIC This notebook is a part of a series of notebooks aimed to get you up to speed with the basics of Apache Spark quickly. This notebook is best suited for those that have very little or no experience with Spark. The series also serves as a strong review for those that have some experience with Spark but aren't as familiar with some of the more sophisticated tools like UDF creation and machine learning pipelines. The other notebooks in this series are:
# MAGIC 
# MAGIC - [A Gentle Introduction to Apache Spark on Databricks](https://docs.azuredatabricks.net/_static/notebooks/gentle-introduction-to-apache-spark.html)
# MAGIC - [Apache Spark on Databricks for Data Scientists](https://docs.azuredatabricks.net/_static/notebooks/databricks-for-data-scientists.html)
# MAGIC - [Apache Spark on Databricks for Data Engineers](https://docs.azuredatabricks.net/_static/notebooks/databricks-for-data-engineers.html)
# MAGIC 
# MAGIC ## Databricks Terminology
# MAGIC 
# MAGIC Databricks has key concepts that are worth understanding. You'll notice that many of these line up with the links and icons that you'll see on the left side. These together define the fundamental tools that Databricks provides to you as an end user. They are available both in the web application UI as well as the REST API.
# MAGIC 
# MAGIC -   ****Workspaces****
# MAGIC     -   Workspaces allow you to organize all the work that you are doing on Databricks. Like a folder structure in your computer, it allows you to save ****notebooks**** and ****libraries**** and share them with other users. Workspaces are not connected to data and should not be used to store data. They're simply for you to store the ****notebooks**** and ****libraries**** that you use to operate on and manipulate your data with.
# MAGIC -   ****Notebooks****
# MAGIC     -   Notebooks are a set of any number of cells that allow you to execute commands. Cells hold code in any of the following languages: `Scala`, `Python`, `R`, `SQL`, or `Markdown`. Notebooks have a default language, but each cell can have a language override to another language. This is done by including `%[language name]` at the top of the cell. For instance `%python`. We'll see this feature shortly.
# MAGIC     -   Notebooks need to be connected to a ****cluster**** in order to be able to execute commands however they are not permanently tied to a cluster. This allows notebooks to be shared via the web or downloaded onto your local machine.
# MAGIC     -   Here is a demonstration video of [Notebooks](http://www.youtube.com/embed/MXI0F8zfKGI).
# MAGIC     -   ****Dashboards****
# MAGIC         -   ****Dashboards**** can be created from ****notebooks**** as a way of displaying the output of cells without the code that generates them. 
# MAGIC     - ****Notebooks**** can also be scheduled as ****jobs**** in one click either to run a data pipeline, update a machine learning model, or update a dashboard.
# MAGIC -   ****Libraries****
# MAGIC     -   Libraries are packages or modules that provide additional functionality that you need to solve your business problems. These may be custom written Scala or Java jars; python eggs or custom written packages. You can write and upload these manually or you may install them directly via package management utilities like pypi or maven.
# MAGIC -   ****Tables****
# MAGIC     -   Tables are structured data that you and your team will use for analysis. Tables can exist in several places. Tables can be stored in cloud storage, they can be stored on the cluster that you're currently using, or they can be cached in memory. [For more about tables see the documentation](https://docs.cloud.databricks.com/docs/latest/databricks_guide/index.html#02%20Product%20Overview/07%20Tables.html).
# MAGIC -   ****Clusters****
# MAGIC     -   Clusters are groups of computers that you treat as a single computer. In Databricks, this means that you can effectively treat 20 computers as you might treat one computer. Clusters allow you to execute code from ****notebooks**** or ****libraries**** on set of data. That data may be raw data located on cloud storage or structured data that you uploaded as a ****table**** to the cluster you are working on. 
# MAGIC     - It is important to note that clusters have access controls to control who has access to each cluster.
# MAGIC     -   Here is a demonstration video of [Clusters](http://www.youtube.com/embed/2-imke2vDs8).
# MAGIC -   ****Jobs****
# MAGIC     -   Jobs are the tool by which you can schedule execution to occur either on an already existing ****cluster**** or a cluster of its own. These can be ****notebooks**** as well as jars or python scripts. They can be created either manually or via the REST API.
# MAGIC     -   Here is a demonstration video of [Jobs](<http://www.youtube.com/embed/srI9yNOAbU0).
# MAGIC -   ****Apps****
# MAGIC     -   Apps are third party integrations with the Databricks platform. These include applications like Tableau.
# MAGIC 
# MAGIC ## Databricks and Apache Spark Help Resources
# MAGIC 
# MAGIC Databricks comes with a variety of tools to help you learn how to use Databricks and Apache Spark effectively. Databricks holds the greatest collection of Apache Spark documentation available anywhere on the web. There are two fundamental sets of resources that we make available: resources to help you learn how to use Apache Spark and Databricks and resources that you can refer to if you already know the basics.
# MAGIC 
# MAGIC To access these resources at any time, click the question mark button at the top right-hand corner. This search menu will search all of the below sections of the documentation.
# MAGIC 
# MAGIC ![img](https://training.databricks.com/databricks_guide/gentle_introduction/help_menu.png)
# MAGIC 
# MAGIC -   ****The Databricks Guide****
# MAGIC     -   The Databricks Guide is the definitive reference for you and your team once you've become accustomed to using and leveraging Apache Spark. It allows for quick reference of common Databricks and Spark APIs with snippets of sample code.
# MAGIC     -   The Guide also includes a series of tutorials (including this one!) that provide a more guided introduction to a given topic.
# MAGIC -   ****The Spark APIs****
# MAGIC     -   Databricks makes it easy to search the Apache Spark APIs directly. Simply use the search that is available at the top right and it will automatically display API results as well.
# MAGIC -   ****The Apache Spark Documentation****
# MAGIC     -   The Apache Spark open source documentation is also made available for quick and simple search if you need to dive deeper into some of the internals of Apache Spark.
# MAGIC -   ****Databricks Forums****
# MAGIC     -   [The Databricks Forums](https://forums.databricks.com/) are a community resource for those that have specific use case questions or questions that they cannot see answered in the guide or the documentation.
# MAGIC     
# MAGIC [Databricks also provides professional and enterprise level technical support](http://go.databricks.com/contact-databricks) for companies and enterprises looking to take their Apache Spark deployments to the next level.
# MAGIC 
# MAGIC ## Databricks and Apache Spark Abstractions
# MAGIC 
# MAGIC Now that we've defined the terminology and more learning resources - let's go through a basic introduction of Apache Spark and Databricks. While you're likely familiar with the concept of Spark, let's take a moment to ensure that we all share the same definitions and give you the opportunity to learn a bit about Spark's history.
# MAGIC 
# MAGIC ### The Apache Spark project's History
# MAGIC 
# MAGIC Spark was originally written by the founders of Databricks during their time at UC Berkeley. The Spark project started in 2009, was open sourced in 2010, and in 2013 its code was donated to Apache, becoming Apache Spark. The employees of Databricks have written over 75% of the code in Apache Spark and have contributed more than 10 times more code than any other organization. Apache Spark is a sophisticated distributed computation framework for executing code in parallel across many different machines. While the abstractions and interfaces are simple, managing clusters of computers and ensuring production-level stability is not. Databricks makes big data simple by providing Apache Spark as a hosted solution.
# MAGIC 
# MAGIC ### The Contexts/Environments
# MAGIC 
# MAGIC Let's now tour the core abstractions in Apache Spark to ensure that you'll be comfortable with all the pieces that you're going to need to understand in order to understand how to use Databricks and Spark effectively.
# MAGIC 
# MAGIC Historically, Apache Spark has had two core contexts that are available to the user. The `sparkContext` made available as `sc` and the `SQLContext` made available as `sqlContext`, these contexts make a variety of functions and information available to the user. The `sqlContext` makes a lot of DataFrame functionality available while the `sparkContext` focuses more on the Apache Spark engine itself.
# MAGIC 
# MAGIC However in Apache Spark 2.X, there is just one context - the `SparkSession`.
# MAGIC 
# MAGIC ### The Data Interfaces
# MAGIC 
# MAGIC There are several key interfaces that you should understand when you go to use Spark.
# MAGIC 
# MAGIC -   ****The Dataset****
# MAGIC     -   The Dataset is Apache Spark's newest distributed collection and can be considered a combination of DataFrames and RDDs. It provides the typed interface that is available in RDDs while providing a lot of conveniences of DataFrames. It will be the core abstraction going forward.
# MAGIC -   ****The DataFrame****
# MAGIC     -   The DataFrame is collection of distributed `Row` types. These provide a flexible interface and are similar in concept to the DataFrames you may be familiar with in python (pandas) as well as in the R language.
# MAGIC -   ****The RDD (Resilient Distributed Dataset)****
# MAGIC     -   Apache Spark's first abstraction was the RDD or Resilient Distributed Dataset. Essentially it is an interface to a sequence of data objects that consist of one or more types that are located across a variety of machines in a cluster. RDD's can be created in a variety of ways and are the "lowest level" API available to the user. While this is the original data structure made available, new users should focus on Datasets as those will be supersets of the current RDD functionality.
# MAGIC 
# MAGIC 
# MAGIC # Getting Started with Some Code!
# MAGIC 
# MAGIC Whew, that's a lot to cover thus far! But we've made it to the demonstration so we can see the power of Apache Spark and Databricks together. To do this you can do one of several things. First, and probably simplest, is that you can copy this notebook into your own environment via the `Import Notebook` button that is available at the top right or top left of this page. If you'd rather type all of the commands yourself, you can create a new notebook and type the commands as we proceed.
# MAGIC 
# MAGIC ## Creating a Cluster
# MAGIC 
# MAGIC Click the Clusters button that you'll notice on the left side of the page. On the Clusters page, click on ![img](https://training.databricks.com/databricks_guide/create_cluster.png) in the upper left corner.
# MAGIC 
# MAGIC Then, on the Create Cluster dialog, enter the configuration for the new cluster.
# MAGIC 
# MAGIC Finally, 
# MAGIC 
# MAGIC -   Select a unique name for the cluster.
# MAGIC -   Select the Runtime Version.
# MAGIC -   Enter the number of workers to bring up - at least 1 is required to run Spark commands.

# COMMAND ----------



# COMMAND ----------

# MAGIC %md first let's explore the previously mentioned `SparkSession`. We can access it via the `spark` variable. As explained, the Spark Session is the core location for where Apache Spark related information is stored. For Spark 1.X the variables are `sqlContext` and `sc`.
# MAGIC 
# MAGIC Cells can be executed by hitting `shift+enter` while the cell is selected.

# COMMAND ----------

spark

# COMMAND ----------

# MAGIC %md We can use the Spark Context to access information but we can also use it to parallelize a collection as well. Here we'll parallelize a small python range that will provide a return type of `DataFrame`.

# COMMAND ----------

firstDataFrame = spark.range(1000000)

# The code for 2.X is
# spark.range(1000000)
# print(firstDataFrame)

# COMMAND ----------

# MAGIC %md Now one might think that this would actually print out the values of the `DataFrame` that we just parallelized, however that's not quite how Apache Spark works. Spark allows two distinct kinds of operations by the user. There are **transformations** and there are **actions**.
# MAGIC 
# MAGIC ### Transformations
# MAGIC 
# MAGIC Transformations are operations that will not be completed at the time you write and execute the code in a cell - they will only get executed once you have called a **action**. An example of a transformation might be to convert an integer into a float or to filter a set of values.
# MAGIC 
# MAGIC ### Actions
# MAGIC 
# MAGIC Actions are commands that are computed by Spark right at the time of their execution. They consist of running all of the previous transformations in order to get back an actual result. An action is composed of one or more jobs which consists of tasks that will be executed by the workers in parallel where possible
# MAGIC 
# MAGIC Here are some simple examples of transformations and actions. Remember, these **are not all** the transformations and actions - this is just a short sample of them. We'll get to why Apache Spark is designed this way shortly!
# MAGIC 
# MAGIC ![transformations and actions](https://training.databricks.com/databricks_guide/gentle_introduction/trans_and_actions.png)

# COMMAND ----------

# An example of a transformation
# select the ID column values and multiply them by 2
secondDataFrame = firstDataFrame.selectExpr("(id * 2) as value")

# COMMAND ----------

# an example of an action
# take the first 5 values that we have in our firstDataFrame
print(firstDataFrame.take(5))
# take the first 5 values that we have in our secondDataFrame
print(secondDataFrame.take(5))

# COMMAND ----------

# MAGIC %md 
# MAGIC 
# MAGIC Now we've seen that Spark consists of actions and transformations. Let's talk about why that's the case. The reason for this is that it gives a simple way to optimize the entire pipeline of computations as opposed to the individual pieces. This makes it exceptionally fast for certain types of computation because it can perform all relevant computations at once. Technically speaking, Spark `pipelines` this computation which we can see in the image below. This means that certain computations can all be performed at once (like a map and a filter) rather than having to do one operation for all pieces of data then the following operation.
# MAGIC 
# MAGIC ![transformations and actions](https://training.databricks.com/databricks_guide/gentle_introduction/pipeline.png)
# MAGIC 
# MAGIC Apache Spark can also keep results in memory as opposed to other frameworks that immediately write to disk after each task.
# MAGIC 
# MAGIC ## Apache Spark Architecture
# MAGIC 
# MAGIC Before proceeding with our example, let's see an overview of the Apache Spark architecture. As mentioned before, Apache Spark allows you to treat many machines as one machine and this is done via a master-worker type architecture where there is a `driver` or master node in the cluster, accompanied by `worker` nodes. The master sends work to the workers and either instructs them to pull to data from memory or from disk (or from another data source).
# MAGIC 
# MAGIC The diagram below shows an example Apache Spark cluster, basically there exists a Driver node that communicates with executor nodes. Each of these executor nodes have slots which are logically like execution cores. 
# MAGIC 
# MAGIC ![spark-architecture](https://training.databricks.com/databricks_guide/gentle_introduction/videoss_logo.png)
# MAGIC 
# MAGIC The Driver sends Tasks to the empty slots on the Executors when work has to be done:
# MAGIC 
# MAGIC ![spark-architecture](https://training.databricks.com/databricks_guide/gentle_introduction/spark_cluster_tasks.png)
# MAGIC 
# MAGIC You can view the details of your Apache Spark application in the Apache Spark web UI.  The web UI is accessible in Databricks by going to "Clusters" and then clicking on the "View Spark UI" link for your cluster, it is also available by clicking at the top left of this notebook where you would select the cluster to attach this notebook to. In this option will be a link to the Apache Spark Web UI.
# MAGIC 
# MAGIC At a high level, every Apache Spark application consists of a driver program that launches various parallel operations on executor Java Virtual Machines (JVMs) running either in a cluster or locally on the same machine. In Databricks, the notebook interface is the driver program.  This driver program contains the main loop for the program and creates distributed datasets on the cluster, then applies operations (transformations & actions) to those datasets.
# MAGIC Driver programs access Apache Spark through a `SparkSession` object regardless of deployment location.
# MAGIC 
# MAGIC ## A Worked Example of Transformations and Actions
# MAGIC 
# MAGIC To illustrate all of these architectural and most relevantly **transformations** and **actions** - let's go through a more thorough example, this time using `DataFrames` and a csv file. 
# MAGIC 
# MAGIC The DataFrame and SparkSQL work almost exactly as we have described above, we're going to build up a plan for how we're going to access the data and then finally execute that plan with an action. We'll see this process in the diagram below. We go through a process of analyzing the query, building up a plan, comparing them and then finally executing it.
# MAGIC 
# MAGIC ![Spark Query Plan](https://training.databricks.com/databricks_guide/gentle_introduction/query-plan-generation.png)
# MAGIC 
# MAGIC While we won't go too deep into the details for how this process works, you can read a lot more about this process on the [Databricks blog](https://databricks.com/blog/2015/04/13/deep-dive-into-spark-sqls-catalyst-optimizer.html). For those that want a more information about how Apache Spark goes through this process, I would definitely recommend that post!
# MAGIC 
# MAGIC Going forward, we're going to access a set of public datasets that Databricks makes available. Databricks datasets are a small curated group that we've pulled together from across the web. We make these available using the Databricks filesystem. Let's load the popular diamonds dataset in as a spark  `DataFrame`. Now let's go through the dataset that we'll be working with.

# COMMAND ----------

# MAGIC %fs ls /databricks-datasets/Rdatasets/data-001/datasets.csv

# COMMAND ----------

dataPath = "/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv"
diamonds = spark.read.format("com.databricks.spark.csv")\
  .option("header","true")\
  .option("inferSchema", "true")\
  .load(dataPath)
  
# inferSchema means we will automatically figure out column types 
# at a cost of reading the data more than once

# COMMAND ----------

# MAGIC %md Now that we've loaded in the data, we're going to perform computations on it. This provide us a convenient tour of some of the basic functionality and some of the nice features that makes running Spark on Databricks the simplest! In order to be able to perform our computations, we need to understand more about the data. We can do this with the `display` function.

# COMMAND ----------

display(diamonds)

# COMMAND ----------

# MAGIC %md what makes `display` exceptional is the fact that we can very easily create some more sophisticated graphs by clicking the graphing icon that you can see below. Here's a plot that allows us to compare price, color, and cut.

# COMMAND ----------

display(diamonds)

# COMMAND ----------

# MAGIC %md Now that we've explored the data, let's return to understanding **transformations** and **actions**. I'm going to create several transformations and then an action. After that we will inspect exactly what's happening under the hood.
# MAGIC 
# MAGIC These transformations are simple, first we group by two variables, cut and color and then compute the average price. Then we're going to inner join that to the original dataset on the column `color`. Then we'll select the average price as well as the carat from that new dataset.

# COMMAND ----------

df1 = diamonds.groupBy("cut", "color").avg("price") # a simple grouping

df2 = df1\
  .join(diamonds, on='color', how='inner')\
  .select("`avg(price)`", "carat")
# a simple join and selecting some columns

# COMMAND ----------

# MAGIC %md These transformations are now complete in a sense but nothing has happened. As you'll see above we don't get any results back! 
# MAGIC 
# MAGIC The reason for that is these computations are *lazy* in order to build up the entire flow of data from start to finish required by the user. This is a intelligent optimization for two key reasons. Any calculation can be recomputed from the very source data allowing Apache Spark to handle any failures that occur along the way, successfully handle stragglers. Secondly, Apache Spark can optimize computation so that data and computation can be `pipelined` as we mentioned above. Therefore, with each transformation Apache Spark creates a plan for how it will perform this work.
# MAGIC 
# MAGIC To get a sense for what this plan consists of, we can use the `explain` method. Remember that none of our computations have been executed yet, so all this explain method does is tells us the lineage for how to compute this exact dataset.

# COMMAND ----------

df2.explain()

# COMMAND ----------

# MAGIC %md Now explaining the above results is outside of this introductory tutorial, but please feel free to read through it. What you should deduce from this is that Spark has generated a plan for how it hopes to execute the given query. Let's now run an action in order to execute the above plan.

# COMMAND ----------

df2.count()

# COMMAND ----------

# MAGIC %md This will execute the plan that Apache Spark built up previously. Click the little arrow next to where it says `(2) Spark Jobs` after that cell finishes executing and then click the `View` link. This brings up the Apache Spark Web UI right inside of your notebook. This can also be accessed from the cluster attach button at the top of this notebook. In the Spark UI, you should see something that includes a diagram something like this.
# MAGIC 
# MAGIC ![img](https://training.databricks.com/databricks_guide/gentle_introduction/spark-dag-ui-before-2-0.png)
# MAGIC 
# MAGIC or
# MAGIC 
# MAGIC ![img](https://training.databricks.com/databricks_guide/gentle_introduction/spark-dag-ui.png)
# MAGIC 
# MAGIC These are significant visualizations. The top one is using Apache Spark 1.6 while the lower one is using Apache Spark 2.0, we'll be focusing on the 2.0 version. These are Directed Acyclic Graphs (DAG)s of all the computations that have to be performed in order to get to that result. It's easy to see that the second DAG visualization is much cleaner than the one before but both visualizations show us all the steps that Spark has to get our data into the final form. 
# MAGIC 
# MAGIC Again, this DAG is generated because transformations are *lazy* - while generating this series of steps Spark will optimize lots of things along the way and will even generate code to do so. This is one of the core reasons that users should be focusing on using DataFrames and Datasets instead of the legacy RDD API. With DataFrames and Datasets, Apache Spark will work under the hood to optimize the entire query plan and pipeline entire steps together. You'll see instances of `WholeStageCodeGen` as well as `tungsten` in the plans and these are apart of the improvements [in SparkSQL which you can read more about on the Databricks blog.](https://databricks.com/blog/2015/04/28/project-tungsten-bringing-spark-closer-to-bare-metal.html)
# MAGIC 
# MAGIC In this diagram you can see that we start with a CSV all the way on the left side, perform some changes, merge it with another CSV file (that we created from the original DataFrame), then join those together and finally perform some aggregations until we get our final result!

# COMMAND ----------

# MAGIC %md ### Caching
# MAGIC 
# MAGIC One of the significant parts of Apache Spark is its ability to store things in memory during computation. This is a neat trick that you can use as a way to speed up access to commonly queried tables or pieces of data. This is also great for iterative algorithms that work over and over again on the same data. While many see this as a panacea for all speed issues, think of it much more like a tool that you can use. Other important concepts like data partitioning, clustering and bucketing can end up having a much greater effect on the execution of your job than caching however remember - these are all tools in your tool kit!
# MAGIC 
# MAGIC To cache a DataFrame or RDD, simply use the cache method.

# COMMAND ----------

df2.cache()

# COMMAND ----------

# MAGIC %md Caching, like a transformation, is performed lazily. That means that it won't store the data in memory until you call an action on that dataset. 
# MAGIC 
# MAGIC Here's a simple example. We've created our df2 DataFrame which is essentially a logical plan that tells us how to compute that exact DataFrame. We've told Apache Spark to cache that data after we compute it for the first time. So let's call a full scan of the data with a count twice. The first time, this will create the DataFrame, cache it in memory, then return the result. The second time, rather than recomputing that whole DataFrame, it will just hit the version that it has in memory.
# MAGIC 
# MAGIC Let's take a look at how we can discover this.

# COMMAND ----------

df2.count()

# COMMAND ----------

# MAGIC %md However after we've now counted the data. We'll see that the explain ends up being quite different.

# COMMAND ----------

df2.count()

# COMMAND ----------

# MAGIC %md In the above example, we can see that this cuts down on the time needed to generate this data immensely - often by at least an order of magnitude. With much larger and more complex data analysis, the gains that we get from caching can be even greater!

# COMMAND ----------

# MAGIC %md ## Conclusion
# MAGIC 
# MAGIC In this notebook we've covered a ton of material! But you're now well on your way to understanding Spark and Databricks! Now that you've completed this notebook, you should hopefully be more familiar with the core concepts of Spark on Databricks. Be sure to subscribe to our blog to get the latest updates about Apache Spark 2.0 and the next notebooks in this series!