from pyspark import SparkContext
from pyspark.sql.session import SparkSession
from pyspark.conf import SparkConf
from pyspark.sql.functions import from_json
from pyspark.sql.types import *
from pyspark.sql.functions import lit, col, regexp_replace, substring, sum, session_window, max
from pyspark.sql import SparkSession
from pyspark.ml.regression import LinearRegression
from pyspark.ml.feature import VectorAssembler
import time

print("waiting for logstash to start")
print("*********************************************************************************")
time.sleep(60)

elastic_host="http://elasticsearch:9200"
elastic_index="apples"
topic = 'apples'
kafkaServer = "kafkaServer:9092"

es_mapping = {
    "mappings": {
        "properties":
        {
            "week": {"type": "integer"},
            "year": {"type": "integer"},
            "quantity": {"type": "integer"},
            "@timestamp": {"type": "date","format": "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"}
        }
    }
}


schema = StructType([
    StructField(name='beginDate', dataType=StringType(), nullable=False),
    StructField(name='description', dataType=StringType(), nullable=True),
    StructField(name='endDate', dataType=StringType(), nullable=True),
    StructField(name='memberStateCode', dataType=StringType(), nullable=True),
    StructField(name='memberStateName', dataType=StringType(), nullable=True),
    StructField(name='price', dataType=StringType(), nullable=False),
    StructField(name='product', dataType=StringType(), nullable=False),
    StructField(name='unit', dataType=StringType(), nullable=False),
    StructField(name='variety', dataType=StringType(), nullable=False),
    StructField(name='weekNumber', dataType=IntegerType(), nullable=False)
])


def transformDataFrame(df):
    new_df = df.withColumn("price", (regexp_replace(col("price"), "€", "")))
    new_df = new_df.withColumn("unit", (regexp_replace(col("unit"), "KG", "")))
    grouped = new_df.withColumn("price", col("price").cast("int"))
    final = grouped.withColumn("unit", col("unit").cast("int"))
    final = final.withColumn("beginDate", substring('beginDate', 7, 10).cast('int'))
    last = final.withWatermark("timestamp", "1 minutes").groupBy(session_window("timestamp", "1 minutes"), "weekNumber", "beginDate").agg(sum("price").alias("price"), sum("unit").alias("quantity"))

    return last


def createFutureWeeks(maxYear, maxWeek):
    schema = StructType([
        StructField('week', IntegerType(), True),
        StructField('year', IntegerType(), True),
        StructField('quantity', IntegerType(), True)
    ])

    data = []

    for i in range(1, 20):
        maxWeek += 1

        if maxWeek > 51:
            maxWeek = 1
            maxYear += 1

        data.append((maxWeek, maxYear, 0))

    df = spark.createDataFrame(data, schema=schema)
    return df


def findlastRecord(df):
    maxYear = df.agg({"beginDate": "max"}).collect()[0][0]
    maxWeek = df.filter(col("beginDate") == maxYear).select(max("weekNumber")).head()[0]

    return maxWeek, maxYear


def trainRegressors(df):
    featureassembler = VectorAssembler(inputCols = ["weekNumber", "beginDate"], outputCol = "features")
    output = featureassembler.setHandleInvalid("skip").transform(df)
    quantityData = output.select("features", "quantity")

    quantityRegressor = LinearRegression(featuresCol = 'features', labelCol = 'quantity')
    quantityRegressor = quantityRegressor.fit(quantityData)

    featureassembler = VectorAssembler(inputCols = ["weekNumber", "beginDate", 'quantity'], outputCol = "features")
    output = featureassembler.setHandleInvalid("skip").transform(df)
    priceData = output.select("features", "price")

    priceRegressor = LinearRegression(featuresCol = 'features', labelCol = 'price')
    priceRegressor = priceRegressor.fit(priceData)

    return quantityRegressor, priceRegressor

def writeData(df):
    df.write.format("org.elasticsearch.spark.sql") \
                .option("es.nodes", "elasticsearch") \
                .option("es.port", "9200") \
                .option("es.resource", elastic_index) \
                .mode("append") \
                .save()

def predictFuturePrices(data, epoch_id):
    df = transformDataFrame(data)
    df.printSchema()

    beginWeek, beginYear = findlastRecord(df)

    quantityRegressor, priceRegressor = trainRegressors(df)

    futureWeeks = createFutureWeeks(beginYear, beginWeek)

    quantityAssembler = VectorAssembler(inputCols=["week", "year"], outputCol="features")
    data = quantityAssembler.transform(futureWeeks)
    quantityValues = quantityRegressor.evaluate(data)

    quantityData = quantityValues.predictions.withColumn("price", lit(0))
    quantityData = quantityData.drop("features")
    quantityData = quantityData.drop("quantity")
    quantityData = quantityData.withColumnRenamed("prediction", "quantity")

    priceAssembler = VectorAssembler(inputCols = ["week", "year", "quantity"], outputCol = "features")
    data = priceAssembler.transform(quantityData)
    priceValues = priceRegressor.evaluate(data)

    priceData = priceValues.predictions
    priceData = priceData.drop("features")
    priceData = priceData.drop("price")
    priceData = priceData.withColumnRenamed("prediction", "prices")

    writeData(priceData)


# setting up spark
sparkConf = SparkConf().set("es.nodes", "elasticsearch") \
                        .set("es.port", "9200")
sc = SparkContext(appName="liveRegression", conf=sparkConf)
spark = SparkSession(sc)
sc.setLogLevel("ERROR")

# reads the data from kafka
df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafkaServer) \
        .option("subscribe", topic) \
        .option("startingOffsets", "earliest") \
        .load() \
        .select(from_json(col("value").cast("string"), schema).alias("data"), col("timestamp")) \
        .selectExpr("data.*", "timestamp")

df.writeStream.foreachBatch(predictFuturePrices).start().awaitTermination()
