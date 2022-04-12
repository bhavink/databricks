from data_security.utils import *
from data_security.securables import *
from pyspark.sql.functions import udf,md5,lit
from pyspark.sql.types import *

spark = get_spark()
dbutils = get_dbutils(spark)

# to make it run on your local system add securables.py to (local)spark path
spark.sparkContext.addPyFile('./dist/cryptography-0.0.1-py3.5.egg')


def get_key():
    #dbutils.secrets.setToken("dksomekey96")
    #encryptionKey = dbutils.secrets.get("bk","encryption_key")
    encryptionKey = str('28cf740e10ea6502422755ec494fda6353760dd872c29abe8d6fd4baaebe5d6f')
    return encryptionKey


schema = StructType([StructField("age", IntegerType()),
                     StructField("workclass", StringType()),
                     StructField("education", StringType()),
                     StructField("income", StringType())])
list = [
  [50, "Self-emp-not-inc","Bachelors","<=50K"],
  [28, "Private","HS-grad",">50K"],
  [27, "Public","Masters",">50K"]
]

df = spark.createDataFrame(list,schema=schema)


encrypt = udf(func_encrypt, StringType())
decrypt = udf(func_decrypt, StringType())


encrypted_df = df.select("age","workclass","education", "income" ,
                                    encrypt("income",lit(get_key())).alias("encrypted_income") ,
                                    md5('income').alias('masked_income'))

encrypted_df.show()

# decrypted_df = encrypted_df.select("education","encrypted_income",decrypt(lit(get_key()),"encrypted_income"))

# decrypted_df.show()