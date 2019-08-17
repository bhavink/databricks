from nlp.reviews.utils import *
from pyspark.ml.feature import RegexTokenizer, StopWordsRemover, HashingTF, Binarizer
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline


***REMOVED*** we will be using a public dataset that's available on databricks platform by default
raw_data_location = "/databricks-datasets/amazon/data20K"
spark = get_spark()
spark.sparkContext.setLogLevel("warn")
logger = get_logger()


***REMOVED*** bucketize rating into 2 buckets 0 || 1
def binarize_training_data(trainingRawData):
    binarizer = Binarizer() \
        .setInputCol("rating") \
        .setOutputCol("label") \
        .setThreshold(3.5)
    return binarizer.transform(trainingRawData)


***REMOVED*** sets aside train, test and validate datasets
def prepare_data():
    data = spark.table('reviews').select("rating","review")
    split_sample = data.randomSplit([0.6, 0.2, 0.2], 123)
    training_raw_data = split_sample[0].cache()
    validate_raw_data = split_sample[1].cache()
    training_df = binarize_training_data(training_raw_data)
    validate_df = binarize_training_data(validate_raw_data)
    test_df = split_sample[2].select("review").cache()
    return training_df, validate_df, test_df


***REMOVED*** build a multi stage ml pipeline
def build_ml_pipeline():
    tokenizer = RegexTokenizer() \
        .setInputCol("review") \
        .setOutputCol("tokens") \
        .setPattern("\\W+")

    remover = StopWordsRemover() \
        .setInputCol("tokens") \
        .setOutputCol("stopWordFree") \

    counts = HashingTF() \
        .setInputCol("stopWordFree") \
        .setOutputCol("features")

    lr = LogisticRegression()

    return tokenizer, remover, counts, lr


***REMOVED*** demonstrate's feature vector building
def create_feature_vector():
    tokenizer, remover, counts, lr = build_ml_pipeline()
    training_df, validate_df, test_df = prepare_data()
    feature_pipeline = Pipeline().setStages([tokenizer, remover, counts])
    prepped_train_df = feature_pipeline.fit(training_df).transform(training_df)
    prepped_test_df = feature_pipeline.fit(test_df).transform(test_df)
    return prepped_train_df, prepped_test_df


***REMOVED*** train classifier
def nostradamus():
    tokenizer, remover, counts, lr = build_ml_pipeline()
    pipeline = Pipeline().setStages([tokenizer, remover, counts, lr])
    training_df, validate_df, test_df = prepare_data()
    lr_pipeline_model = pipeline.fit(training_df)

    ***REMOVED*** Make predictions on test data and print columns of interest.
    prediction = lr_pipeline_model.transform(test_df)
    selected = prediction.select("review", "probability", "prediction")
    for row in selected.collect():
        review, prob, prediction = row
        logger.info("(%s) --> prob=%s, prediction=%f" % (review, str(prob), prediction))

    print("\nROC: " + str(lr_pipeline_model.stages[-1].summary.areaUnderROC))
    ***REMOVED*** return lrPipelineModel


***REMOVED*** run ml pipeline i.e train + test
def run_ml_pipeline():
    prepped_train_df, prepped_test_df = create_feature_vector()
    prepped_train_df.show(n=5,truncate=False)
    prepped_test_df.show(n=5,truncate=False)
    nostradamus()