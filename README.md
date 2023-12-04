# CropPrediction-Monitoring

This project aims at creating a pipeline for crop prediction an soil monitoring.
The pipeline is composed of:

### Used technologies:

**Logstash**:Logstash is used for data ingestion, multiple pipelines have been used to send data to the message broker

**Kafka**:Kafka is used to divide the data and send them to the different spark scripts to be elaborated, the events are registered in separated topics and treated differently.

**Spark**:The bulk of the computation is done by spark, here data is treated accordingly to it's usage, regression is performed and prediction are then sent to the next step in the pipeline.

**Elasticsearch**:Data from spark is then stored here, whether regression results or different metrics we the access it for visualization

**Kibana**:Last step, it's used to visualize and gather conclusion using the treated and not treated data.

Example of a kibana dash using this pipeline:

## Indicators dashboard:

![Alt text](/home/stefano/Uni/TAP/Schermata del 2023-12-04 16-53-05.png)

## Prediction dashboard:

![Alt text](/home/stefano/Uni/TAP/Schermata del 2023-12-04 16-52-45.png)

------

## Starting the project

The entire system can be started by executing a bash script called `startup.sh` this will start any necessary utility and the external script to gather data.

**WARNING**: In case of error and stopping of the application the api scripts that gather data will not stop until completition.

The project can be monitored by 2 access points:
**Kafka**: http://localhost:8080
**Kibana**: http://localhost:5601
