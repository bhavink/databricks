***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED*** **Chart and Graph Types with Python**
***REMOVED*** MAGIC This notebook covers the various charts and graphs that are built into Databricks.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC While Python is used to generate the test data displayed in the visualizations in this notebook, all the information about how to configure these charts & graphs applies to all notebooks.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md  ***REMOVED******REMOVED******REMOVED*** A **Table View** is the most basic way to view data.
***REMOVED*** MAGIC * Only the first 1000 rows will be displayed in the table view.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row

array = map(lambda x: Row(key="k_%04d" % x, value = x), range(1, 5001))
largeDataFrame = sqlContext.createDataFrame(sc.parallelize(array))
largeDataFrame.registerTempTable("largeTable")
display(sqlContext.sql("select * from largeTable"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Tables in Databricks Cloud are configured with **Plot Options...**.
***REMOVED*** MAGIC * The **Keys** section is for specifying the control variable which is typically displayed as the X-Axis on many of the graph types.  Most graphs can plot about 1000 values for the keys, but again - it varies for different graphs.
***REMOVED*** MAGIC * The **Values** section is for specifying the observed variable and is typically displayed on the Y-Axis.  This also tends to be an observed numerical value on most graph types.
***REMOVED*** MAGIC * The **Series groupings** section is for specifying ways to break out the data - for a bar graph - each series grouping has a different color for the bars with a legend to denote that value of each series grouping.  Many of the graph types can only handle series groupings that has 10 or less unique values. 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Some graph types also allow specifying even more options - and those will be discussed as applicable.**

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md  ***REMOVED******REMOVED******REMOVED*** A **Pivot Table** is another way to view data in a table format.
***REMOVED*** MAGIC Instead of just returning the raw results of the table - it can automatically sort, count total or give the average of the data stored in the table.
***REMOVED*** MAGIC * Read more about Pivot Tables here: http://en.wikipedia.org/wiki/Pivot_table
***REMOVED*** MAGIC * For a Pivot Table, key, series grouping and value fields can be specified.   
***REMOVED*** MAGIC * The **Key** is the first column, and there will be one row per key in the Pivot Table.
***REMOVED*** MAGIC * There will be additional column for each unique value for the **Series Grouping**.
***REMOVED*** MAGIC * The table will contain the **Values** field in the cells.  Value must be a numerical field that can be combined using aggregation functions.
***REMOVED*** MAGIC * Cell in the Pivot Table are calculated from multiple rows of the original table.
***REMOVED*** MAGIC   * Select **SUM**, **AVG**, **MIN**, **MAX**, or **COUNT** as the way to combine the original rows into that cell.
***REMOVED*** MAGIC * Pivoting is done on the server side of Databricks Cloud to calculate the cell values.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC To create a Pivot Table, click on the Graph Icon below a result and select **Pivot**:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![Pivot Table](http://training.databricks.com/databricks_guide/pivot.png)

***REMOVED*** COMMAND ----------

***REMOVED*** Click on the Plot Options Button...to see how this pivot table was configured.
from pyspark.sql import Row

largePivotSeries = map(lambda x: Row(key="k_%03d" % (x % 200), series_grouping = "group_%d" % (x % 3), value = x), range(1, 5001))
largePivotDataFrame = sqlContext.createDataFrame(sc.parallelize(largePivotSeries))
largePivotDataFrame.registerTempTable("table_to_be_pivoted")
display(sqlContext.sql("select * from table_to_be_pivoted"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Another way to think of a pivot table is that it does a group by on your original table by the key & series grouping, but instead of outputting (key, series_grouping, aggregation_function(value)) tuples, it outputs a table where the schema is the key and every unique value for the series grouping.
***REMOVED*** MAGIC * See the results of group_by statement below, which contains all the data that is in the pivot table above, but the schema of the results is different.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %sql select key, series_grouping, sum(value) from table_to_be_pivoted group by key, series_grouping order by key, series_grouping

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** A **Bar Chart** is a type of visual pivot table graph and a great basic way to visualize data.
***REMOVED*** MAGIC * **Plot Options...** was used to configure the graph below.
***REMOVED*** MAGIC * The **Key** is *Year* and appears on the X-Axis.
***REMOVED*** MAGIC * The **Series groupings** is *Product* and there is a different color to denote each of those.
***REMOVED*** MAGIC * The **Values** is *salesAmount* and appears on the Y-Axis.
***REMOVED*** MAGIC * **Sum** was selected as the aggregation method, which means rows will be summed for pivoting.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row
salesEntryDataFrame = sqlContext.createDataFrame(sc.parallelize([
  Row(category="fruits_and_vegetables", product="apples", year=2012, salesAmount=100.50),
  Row(category="fruits_and_vegetables", product="oranges", year=2012, salesAmount=100.75),
  Row(category="fruits_and_vegetables", product="apples", year=2013, salesAmount=200.25),
  Row(category="fruits_and_vegetables", product="oranges", year=2013, salesAmount=300.65),
  Row(category="fruits_and_vegetables", product="apples", year=2014, salesAmount=300.65),
  Row(category="fruits_and_vegetables", product="oranges", year=2015, salesAmount=100.35),
  Row(category="butcher_shop", product="beef", year=2012, salesAmount=200.50),
  Row(category="butcher_shop", product="chicken", year=2012, salesAmount=200.75),
  Row(category="butcher_shop", product="pork", year=2013, salesAmount=400.25),
  Row(category="butcher_shop", product="beef", year=2013, salesAmount=600.65),
  Row(category="butcher_shop", product="beef", year=2014, salesAmount=600.65),
  Row(category="butcher_shop", product="chicken", year=2015, salesAmount=200.35),
  Row(category="misc", product="gum", year=2012, salesAmount=400.50),
  Row(category="misc", product="cleaning_supplies", year=2012, salesAmount=400.75),
  Row(category="misc", product="greeting_cards", year=2013, salesAmount=800.25),
  Row(category="misc", product="kitchen_utensils", year=2013, salesAmount=1200.65),
  Row(category="misc", product="cleaning_supplies", year=2014, salesAmount=1200.65),
  Row(category="misc", product="cleaning_supplies", year=2015, salesAmount=400.35)
]))
salesEntryDataFrame.registerTempTable("test_sales_table")
display(sqlContext.sql("select * from test_sales_table"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %sql select count(*), education from adult group by education

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md **Tip:** Hover over each bar in the chart below to see the exact values plotted.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** A **Line Graph** is another example of a pivot table graph that can highlight trends for your data set.
***REMOVED*** MAGIC * **Plot Options...** was used to configure the graph below.
***REMOVED*** MAGIC * The **Key** is *Year* and appears on the X-Axis.
***REMOVED*** MAGIC * The **Series groupings** is *Category* and there is different color to denote each of those.
***REMOVED*** MAGIC * The **Values** is *salesAmount* and appears on the Y-Axis.
***REMOVED*** MAGIC * **Sum** is selected as the aggregation method 

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %sql select * from test_sales_table

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** A **Pie Chart** is pivot table graph type that can allow you to see what percentage of the whole your values represent.
***REMOVED*** MAGIC * **NOTE:** As opposed to the previous examples, Key & Series Groupings have been switched.
***REMOVED*** MAGIC * **Plot Options...** was used to configure the graph below.
***REMOVED*** MAGIC * The **Key** is *Category* and one color is used for each product.
***REMOVED*** MAGIC * The **Series groupings** is *Year* and there is different pie chart for each year.
***REMOVED*** MAGIC * The **Values** is *salesAmount* and is used to calculate the percentage of the pie.
***REMOVED*** MAGIC * **Sum** is selected as the aggregation method.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %sql select * from test_sales_table

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** A **Map Graph** is a way to visualize your data on a map.
***REMOVED*** MAGIC * **Plot Options...** was used to configure the graph below.
***REMOVED*** MAGIC * **Keys** should contain the field with the location.
***REMOVED*** MAGIC * **Series groupings** is always ignored for World Map graphs.
***REMOVED*** MAGIC * **Values** should contain exactly one field with a numerical value.
***REMOVED*** MAGIC * Since there can multiple rows with the same location key, choose "Sum", "Avg", "Min", "Max", "COUNT" as the way to combine the values for a single key.
***REMOVED*** MAGIC * Different values are denoted by color on the map, and ranges are always spaced evenly.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Tip:** Apply a smoothing function to your graph if your values are not evenly distributed.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row
stateRDD = sqlContext.createDataFrame(sc.parallelize([
  Row(state="MO", value=1), Row(state="MO", value=10),
  Row(state="NH", value=4),
  Row(state="MA", value=8),
  Row(state="NY", value=4),
  Row(state="CA", value=7)
]))
stateRDD.registerTempTable("test_state_table")
display(sqlContext.sql("Select * from test_state_table"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC To plot a graph of the world, use [country codes in ISO 3166-1 alpha-3 format](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-3) as the key.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row
worldRDD = sqlContext.createDataFrame(sc.parallelize([
  Row(country="USA", value=1000),
  Row(country="JPN", value=23),
  Row(country="GBR", value=23),
  Row(country="FRA", value=21),
  Row(country="TUR", value=3)
]))
display(worldRDD)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** A **Scatter Plot** allows you to see if there is a correlation between two variables.
***REMOVED*** MAGIC * **Plot Options...** was selected to configure the graph below.
***REMOVED*** MAGIC * **Keys** will be used to color the points on the graphs - with a legend on the side.
***REMOVED*** MAGIC * **Series Grouping** is ignored.
***REMOVED*** MAGIC * **Value** must contain at least two numberical fields.  This graph has a, b, and c as the values.
***REMOVED*** MAGIC * The diagonal of the resulting plot is the kernal density plot of the variable.
***REMOVED*** MAGIC * The row always has the variable in the Y-Axis, and the column has the variable in the X-Axis.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row
scatterPlotRDD = sqlContext.createDataFrame(sc.parallelize([
  Row(key="k1", a=0.2, b=120, c=1), Row(key="k1", a=0.4, b=140, c=1), Row(key="k1", a=0.6, b=160, c=1), Row(key="k1", a=0.8, b=180, c=1),
  Row(key="k2", a=0.2, b=220, c=1), Row(key="k2", a=0.4, b=240, c=1), Row(key="k2", a=0.6, b=260, c=1), Row(key="k2", a=0.8, b=280, c=1),
  Row(key="k1", a=1.8, b=120, c=1), Row(key="k1", a=1.4, b=140, c=1), Row(key="k1", a=1.6, b=160, c=1), Row(key="k1", a=1.8, b=180, c=1),
  Row(key="k2", a=1.8, b=220, c=2), Row(key="k2", a=1.4, b=240, c=2), Row(key="k2", a=1.6, b=260, c=2), Row(key="k2", a=1.8, b=280, c=2),
  Row(key="k1", a=2.2, b=120, c=1), Row(key="k1", a=2.4, b=140, c=1), Row(key="k1", a=2.6, b=160, c=1), Row(key="k1", a=2.8, b=180, c=1),
  Row(key="k2", a=2.2, b=220, c=3), Row(key="k2", a=2.4, b=240, c=3), Row(key="k2", a=2.6, b=260, c=3), Row(key="k2", a=2.8, b=280, c=3)
]))
display(scatterPlotRDD)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** LOESS Fit Curves for Scatter Plots
***REMOVED*** MAGIC 
***REMOVED*** MAGIC [LOESS](https://en.wikipedia.org/wiki/Local_regression) is a method of performing local regression on your data to produce a smooth estimation curve that describes the data trend of your scatter plot. It does this by interpolating a curve within its neighborhood of data points. The LOESS fit curve is controlled by a bandwidth parameter that specifies how many neighboring points should be used to smooth the plot. A high bandwidth parameter (close to 1) gives a very smooth curve that may miss the general trend, while a low bandwidth parameter (close to 0) does not smooth the plot much.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC LOESS fit curves are now available for scatter plots. Here is an example of how you can create a LOESS fit for your scatter plots.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **NOTE:** If your dataset has more than 5000 data points, the LOESS fit is computed using the first 5000 points.

***REMOVED*** COMMAND ----------

import numpy as np
import math

***REMOVED*** Create data points for scatter plot
np.random.seed(0)
points = sc.parallelize(range(0,1000)).map(lambda x: (x/100.0, 4 * math.sin(x/100.0) + np.random.normal(4,1))).toDF()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md You can turn this data into a scatter plot using the controls on the bottom left of the display table.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![screen shot 2015-10-13 at 3 42 52 pm](https://cloud.githubusercontent.com/assets/7594753/10472059/d7e16396-71d0-11e5-866c-20b4d8b746cb.png)
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can now access the LOESS fit option when you select *Plot Options*:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![screen shot 2015-10-13 at 3 43 16 pm](https://cloud.githubusercontent.com/assets/7594753/10472058/d7ce763c-71d0-11e5-91b2-4d90e9a704c9.png)
***REMOVED*** MAGIC 
***REMOVED*** MAGIC You can experiment with the bandwith parameter to see how the curve adapts to noisy data.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Once you accept the change, you will see the LOESS fit on your scatter plot!

***REMOVED*** COMMAND ----------

display(points)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** A **Histogram** allows you to determine the distribution of values.
***REMOVED*** MAGIC * **Plot Options...** was selected to configure the graph below.
***REMOVED*** MAGIC * **Value** should contain exactly one field.
***REMOVED*** MAGIC * **Series Grouping** is always ignored.
***REMOVED*** MAGIC * **Keys** can support up to 2 fields.
***REMOVED*** MAGIC   * When no key is specified, exactly one histogram is output.
***REMOVED*** MAGIC   * When 2 fields are specified, then there is a trellis of histograms.
***REMOVED*** MAGIC * **Aggregation** is not applicable.
***REMOVED*** MAGIC * **Number of bins** is a special option that appears only for histogram plots, and controls the number of bins in the histogram.
***REMOVED*** MAGIC * Bins are computed on the serverside for histograms, so it can plot all the rows in a table.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row
***REMOVED*** Hover over the entry in the histogram to read off the exact valued plotted.
histogramRDD = sqlContext.createDataFrame(sc.parallelize([
  Row(key1="a", key2="x", val=0.2), Row(key1="a", key2="x", val=0.4), Row(key1="a", key2="x", val=0.6), Row(key1="a", key2="x", val=0.8), Row(key1="a", key2="x", val=1.0), 
  Row(key1="b", key2="z", val=0.2), Row(key1="b", key2="x", val=0.4), Row(key1="b", key2="x", val=0.6), Row(key1="b", key2="y", val=0.8), Row(key1="b", key2="x", val=1.0), 
  Row(key1="a", key2="x", val=0.2), Row(key1="a", key2="y", val=0.4), Row(key1="a", key2="x", val=0.6), Row(key1="a", key2="x", val=0.8), Row(key1="a", key2="x", val=1.0), 
  Row(key1="b", key2="x", val=0.2), Row(key1="b", key2="x", val=0.4), Row(key1="b", key2="x", val=0.6), Row(key1="b", key2="z", val=0.8), Row(key1="b", key2="x", val=1.0)]))
display(histogramRDD)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** A **Quantile plot** allows you to view what the value is for a given quantile value.
***REMOVED*** MAGIC * For more information on Quantile Plots, see http://en.wikipedia.org/wiki/Normal_probability_plot.
***REMOVED*** MAGIC * **Plot Options...** was selected to configure the graph below.
***REMOVED*** MAGIC * **Value** should contain exactly one field.
***REMOVED*** MAGIC * **Series Grouping** is always ignored.
***REMOVED*** MAGIC * **Keys** can support up to 2 fields.
***REMOVED*** MAGIC   * When no key is specified, exactly one quantile plot is output.
***REMOVED*** MAGIC   * When 2 fields are specified, then there is a trellis of quantile plots .
***REMOVED*** MAGIC * **Aggregation** is not applicable.
***REMOVED*** MAGIC * Quantiles are not being calculated on the serverside for now, so only the 1000 rows can be reflected in the plot.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row
quantileSeries = map(lambda x: Row(key="key_%01d" % (x % 4), grouping="group_%01d" % (x % 3), otherField=x, value=x*x), range(1, 5001))
quantileSeriesRDD = sqlContext.createDataFrame(sc.parallelize(quantileSeries))
display(quantileSeriesRDD)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** A **Q-Q plot** shows you how a field of values are distributed.
***REMOVED*** MAGIC * For more information on Q-Q plots, see http://en.wikipedia.org/wiki/Q%E2%80%93Q_plot.
***REMOVED*** MAGIC * **Value** should contain one or two fields.
***REMOVED*** MAGIC * **Series Grouping** is always ignored.
***REMOVED*** MAGIC * **Keys** can support up to 2 fields.
***REMOVED*** MAGIC   * When no key is specified, exactly one quantile plot is output.
***REMOVED*** MAGIC   * When 2 fields are specified, then there is a trellis of quantile plots .
***REMOVED*** MAGIC * **Aggregation** is not applicable.
***REMOVED*** MAGIC * Q-Q Plots are not being calculated on the serverside for now, so only the 1000 rows can be reflected in the plot.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row
qqPlotSeries = map(lambda x: Row(key="key_%03d" % (x % 5), grouping="group_%01d" % (x % 3), value=x, value_squared=x*x), range(1, 5001))
qqPlotRDD = sqlContext.createDataFrame(sc.parallelize(qqPlotSeries))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md When there is only one field specified for Values, a Q-Q plot will just compare the distribution of the field with a normal distribution.

***REMOVED*** COMMAND ----------

display(qqPlotRDD)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md When there are two fields specified for Values, a Q-Q plot will compare the distribution of the two fields with each other.

***REMOVED*** COMMAND ----------

display(qqPlotRDD)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Up to two keys can be configured with a Q-Q plot to create a trellis of plots.

***REMOVED*** COMMAND ----------

display(qqPlotRDD)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED*** A **Box plot** gives you an idea of what the expected range of values are and shows the outliers.
***REMOVED*** MAGIC * See http://en.wikipedia.org/wiki/Box_plot for more information on Box Plots.
***REMOVED*** MAGIC * **Value** should contain exactly one field.
***REMOVED*** MAGIC * **Series Grouping** is always ignored.
***REMOVED*** MAGIC * **Keys** can be added.
***REMOVED*** MAGIC   * There will be one box and whisker plot for each combination of values for the keys.
***REMOVED*** MAGIC * **Aggregation** is not applicable.
***REMOVED*** MAGIC * Box plots are not being calculated on the serverside for now, so only the first 1000 rows can be reflected in the plot.
***REMOVED*** MAGIC * The Median value of the Box plot is displayed when you hover over the box.

***REMOVED*** COMMAND ----------

from pyspark.sql import Row
import random
***REMOVED*** Hovering over the Box will display the exact median value.
boxSeries = map(lambda x: Row(key="key_%01d" % (x % 2), grouping="group_%01d" % (x % 3), value=random.randint(0, x)), range(1, 5001))
boxSeriesRDD = sqlContext.createDataFrame(sc.parallelize(boxSeries))
display(boxSeriesRDD)