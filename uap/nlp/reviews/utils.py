from __future__ import print_function
from pyspark.sql import SparkSession


***REMOVED*** Utils for accessing spark and dbutils object

def get_spark():
    return (SparkSession.builder.master("local").getOrCreate())


def get_dbutils(spark):
  try:
      import IPython
      dbutils = IPython.get_ipython().user_ns["dbutils"]
  except ImportError:
      from pyspark.dbutils import DBUtils
      dbutils = DBUtils(spark)
      '''
      run this in a databricks notebook cell to get a 48hr valid token, this is different than the PAT token that one uses with
      CLI/REST calls

      %scala
      //code start
      displayHTML(
        "<b>Privileged DBUtils token (expires in 48 hours): </b>" +
        dbutils.notebook.getContext.apiToken.get.split("").mkString("<span/>"))
      //code end

      Then, run dbutils.secrets.setToken(<value>) locally to save the token.

      '''
      dbutils.secrets.setToken("dkeasomekeyvalue1f")
  return dbutils


def get_logger():
    sc = get_spark().sparkContext
    sc._jvm.org.apache.log4j
    log4j = sc._jvm.org.apache.log4j
    logger = log4j.LogManager.getRootLogger()
    return logger