from pyspark import SparkContext
from pyspark.sql.session import SparkSession
from pyspark.conf import SparkConf
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import *
import time

print("waiting for logstash to start")
print("*********************************************************************************")
time.sleep(60)

elastic_host="http://elasticsearch:9200"
elastic_index="indicators"
topic = 'indicators'
kafkaServer = "kafkaServer:9092"

es_mapping = {
    "mappings": {
        "properties":
        {
            "subindicator": {"type": "text"},
            "parameter": {"type": "text"},
            "unit": {"type": "text"},
            "memberStateName": {"type": "text"},
            "year": {"type": "integer"},
            "value": {"type": "integer"},
            "flag": {"type": "text"}
        }
    }
}



schema = StructType([
    StructField(name='indicator', dataType=StringType(), nullable=False),
    StructField(name='subindicator', dataType=StringType(), nullable=True),
    StructField(name='parameter', dataType=StringType(), nullable=True),
    StructField(name='unit', dataType=StringType(), nullable=True),
    StructField(name='code', dataType=StringType(), nullable=True),
    StructField(name='source', dataType=StringType(), nullable=False),
    StructField(name='memberStateCode', dataType=StringType(), nullable=False),
    StructField(name='memberStateName', dataType=StringType(), nullable=False),
    StructField(name='year', dataType=IntegerType(), nullable=False),
    StructField(name='value', dataType=FloatType(), nullable=False),
    StructField(name='flag', dataType=StringType(), nullable=False)

])


def writeData(df):
    df.write.format("org.elasticsearch.spark.sql") \
            .option("es.nodes", "elasticsearch") \
            .option("es.port", "9200") \
            .option("es.resource", elastic_index) \
            .mode("append") \
            .save()


def treatData(df, epoch_id):
    new_df = df.drop("source")
    new_df = new_df.drop("memberStateCode")
    new_df = new_df.drop("indicator")
    new_df = new_df.drop("code")

    new_df.printSchema()

    writeData(new_df)


# setting up spark
sparkConf = SparkConf().set("es.nodes", "elasticsearch") \
                        .set("es.port", "9200")
sc = SparkContext(appName="liveRegression", conf=sparkConf)
spark = SparkSession(sc)
sc.setLogLevel("ERROR")


df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafkaServer) \
        .option("subscribe", topic) \
        .option("startingOffsets", "earliest") \
        .load() \
        .select(from_json(col("value").cast("string"), schema).alias("data")) \
        .selectExpr("data.*")


df.writeStream.foreachBatch(treatData).start().awaitTermination()
