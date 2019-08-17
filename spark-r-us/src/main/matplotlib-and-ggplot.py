# Databricks notebook source
# MAGIC %md
# MAGIC 
# MAGIC # **Matplotlib and GGPlot**
# MAGIC You can display MatPlotLib and GGPlot objects in Python notebooks.

# COMMAND ----------

# MAGIC %md ### **Matplotlib** objects can be viewed in Python notebooks using the **display** command.

# COMMAND ----------

import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 2*np.pi, 50)
y = np.sin(x)
y2 = y + 0.1 * np.random.normal(size=x.shape)

fig, ax = plt.subplots()
ax.plot(x, y, 'k--')
ax.plot(x, y2, 'ro')

# set ticks and tick labels
ax.set_xlim((0, 2*np.pi))
ax.set_xticks([0, np.pi, 2*np.pi])
ax.set_xticklabels(['0', '$\pi$','2$\pi$'])
ax.set_ylim((-1.5, 1.5))
ax.set_yticks([-1, 0, 1])

# Only draw spine between the y-ticks
ax.spines['left'].set_bounds(-1, 1)
# Hide the right and top spines
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
# Only show ticks on the left and bottom spines
ax.yaxis.set_ticks_position('left')
ax.xaxis.set_ticks_position('bottom')

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC * Copy the cell above and run it in your notebook, and then run the **display** command below to view the graph.

# COMMAND ----------

display(fig)

# COMMAND ----------

# MAGIC %md ### **GGPlot** objects can be displayed as well.

# COMMAND ----------

from ggplot import *
p = ggplot(meat, aes('date','beef')) + \
    geom_line(color='black') + \
    scale_x_date(breaks=date_breaks('7 years'), labels='%b %Y') + \
    scale_y_continuous(labels='comma') + theme_bw()

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC ### **Note:** Since this notebook is locked, you won't actually see the GGPlot object here.
# MAGIC * Copy the cell above and run it in your notebook, and then run the **display** command below to view the graph.

# COMMAND ----------

display(p)