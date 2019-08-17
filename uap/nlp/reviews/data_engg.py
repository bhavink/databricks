from nlp.reviews.utils import *

***REMOVED*** we will be using a public dataset that's available on databricks platform by default
***REMOVED*** raw_data_location = "/databricks-datasets/amazon/data20K"
spark = get_spark()
logger = get_logger()


def ingest_data(raw_data_location):
    logger.info("reading data from: " + raw_data_location)
    data = spark.read.parquet(raw_data_location)
    data.createOrReplaceTempView("reviews")
    logger.info("temp view called reviews created")


def analyze_data():
    logger.info("\n\nTotal record count:")
    spark.sql("select count(*) from reviews").show()
    logger.info("Record looks like: ")
    spark.sql("select * from reviews limit 5").show(truncate=False)
    logger.info("How do the ratings fair across all brands?")
    spark.sql("select rating, count(1) as count from reviews group by rating order by rating desc").show()
    logger.info("Ratings distribution having word 'great' ")
    spark.sql("SELECT count(1), rating FROM reviews WHERE review LIKE '%great%' GROUP BY rating ORDER BY rating").show()
    logger.info("Ratings distribution having word 'poor' ")
    spark.sql("SELECT count(1), rating FROM reviews WHERE review LIKE '%poor%' GROUP BY rating ORDER BY rating").show()


def test_logger():
    logger = get_logger()
    for x in range(3):
        logger.warn("logging msgs from dbconnect-" + str(x))