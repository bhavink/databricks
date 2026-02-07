"""
FHIR Streaming Ingestion with Spark Declarative Pipelines (SDP)

This is an EXAMPLE showing how to ingest FHIR resources from streaming sources
(Kafka, Event Hubs, Kinesis) using SDP.

Use this when:
- You have real-time FHIR events (webhooks, subscriptions)
- You need sub-minute latency
- Your FHIR server pushes to a message queue

Architecture:
    FHIR Server → Kafka/Event Hubs → SDP Streaming Table → Silver Tables
    
Configuration (in databricks.yml):
    configuration:
      fhir.streaming.kafka.servers: "your-kafka:9092"
      fhir.streaming.kafka.topic: "fhir-events"
      fhir.streaming.kafka.group_id: "fhir-pipeline"

Note: This file is an EXAMPLE. Modify and include in your pipeline bundle as needed.
"""

# Modern SDP API (2026 best practice)
from pyspark import pipelines as dp
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, from_json, current_timestamp, expr, lit,
    when, coalesce
)
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType,
    BooleanType, MapType
)


# =============================================================================
# Configuration
# =============================================================================

def get_kafka_config():
    """Get Kafka configuration from Spark conf"""
    return {
        "kafka.bootstrap.servers": spark.conf.get("fhir.streaming.kafka.servers", "localhost:9092"),
        "subscribe": spark.conf.get("fhir.streaming.kafka.topic", "fhir-events"),
        "startingOffsets": spark.conf.get("fhir.streaming.kafka.starting_offsets", "latest"),
        "kafka.group.id": spark.conf.get("fhir.streaming.kafka.group_id", "fhir-sdp-pipeline"),
    }


def get_eventhub_config():
    """Get Azure Event Hubs configuration from Spark conf"""
    connection_string = spark.conf.get("fhir.streaming.eventhub.connection_string")
    return {
        "eventhubs.connectionString": connection_string,
        "eventhubs.consumerGroup": spark.conf.get("fhir.streaming.eventhub.consumer_group", "$Default"),
        "eventhubs.startingPosition": '{"offset": "-1", "enqueuedTime": null, "isInclusive": true}',
    }


# =============================================================================
# Bronze Layer - Raw Streaming Ingestion
# =============================================================================

# Schema for FHIR resource envelope (minimal for bronze)
FHIR_ENVELOPE_SCHEMA = StructType([
    StructField("resourceType", StringType(), True),
    StructField("id", StringType(), True),
    StructField("meta", StructType([
        StructField("versionId", StringType(), True),
        StructField("lastUpdated", StringType(), True),
    ]), True),
])


@dp.table(
    name="bronze_fhir_streaming",
    comment="Real-time FHIR resources from Kafka/Event Hubs",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.zOrderCols": "resource_type,resource_id",
    }
)
@dp.expect_or_quarantine("valid_json", "parsed_resource IS NOT NULL")
@dp.expect("has_resource_type", "resource_type IS NOT NULL")
@dp.expect("has_resource_id", "resource_id IS NOT NULL")
def bronze_fhir_streaming():
    """
    Ingest FHIR resources from Kafka/Event Hubs in real-time.
    
    Expects messages with FHIR JSON in the value field.
    Supports both Kafka and Azure Event Hubs.
    """
    source_type = spark.conf.get("fhir.streaming.source", "kafka")
    
    if source_type == "kafka":
        config = get_kafka_config()
        raw_stream = (
            spark.readStream
            .format("kafka")
            .options(**config)
            .load()
        )
    elif source_type == "eventhub":
        config = get_eventhub_config()
        raw_stream = (
            spark.readStream
            .format("eventhubs")
            .options(**config)
            .load()
        )
    else:
        raise ValueError(f"Unknown streaming source: {source_type}")
    
    return (
        raw_stream
        .select(
            # Message metadata
            col("key").cast("string").alias("message_key"),
            col("value").cast("string").alias("raw_json"),
            col("timestamp").alias("event_timestamp"),
            coalesce(col("partition"), lit(-1)).alias("partition"),
            coalesce(col("offset"), lit(-1)).alias("offset"),
            
            # Ingestion metadata
            current_timestamp().alias("_ingestion_timestamp"),
            lit(source_type).alias("_source_type"),
        )
        # Parse JSON envelope
        .withColumn("parsed_resource", from_json(col("raw_json"), FHIR_ENVELOPE_SCHEMA))
        .withColumn("resource_type", col("parsed_resource.resourceType"))
        .withColumn("resource_id", col("parsed_resource.id"))
        .withColumn("meta_version_id", col("parsed_resource.meta.versionId"))
        .withColumn("meta_last_updated", col("parsed_resource.meta.lastUpdated"))
        
        # Validation flag
        .withColumn("is_valid", col("parsed_resource").isNotNull())
    )


@dp.table(
    name="bronze_fhir_streaming_quarantine",
    comment="Failed/invalid streaming FHIR resources"
)
def bronze_fhir_streaming_quarantine():
    """Quarantine table for invalid streaming messages"""
    # This is automatically populated by @dp.expect_or_quarantine
    pass


# =============================================================================
# Silver Layer - Process by Resource Type
# =============================================================================

# Silver tables can read from EITHER batch or streaming bronze
# The processing logic is the same!

@dp.table(
    name="silver_fhir_patient_streaming",
    comment="Parsed Patient resources from streaming"
)
def silver_fhir_patient_streaming():
    """
    Extract Patient resources from streaming bronze.
    
    Same parsing logic as batch - just different source table.
    
    NOTE: Use spark.readStream.table() for streaming reads (2026 best practice).
    Don't use dp.read_stream() (old syntax, no longer documented).
    """
    return (
        spark.readStream.table("bronze_fhir_streaming")
        .filter("resource_type = 'Patient'")
        .select(
            col("resource_id").alias("id"),
            col("raw_json"),
            col("event_timestamp"),
            col("_ingestion_timestamp"),
            col("meta_version_id"),
            col("meta_last_updated"),
            # Add full parsing here (same UDF as batch)
        )
    )


@dp.table(
    name="silver_fhir_observation_streaming", 
    comment="Parsed Observation resources from streaming"
)
def silver_fhir_observation_streaming():
    """Extract Observation resources from streaming bronze"""
    return (
        spark.readStream.table("bronze_fhir_streaming")
        .filter("resource_type = 'Observation'")
        .select(
            col("resource_id").alias("id"),
            col("raw_json"),
            col("event_timestamp"),
            col("_ingestion_timestamp"),
        )
    )


# =============================================================================
# Unified View (Combines Batch + Streaming)
# =============================================================================

@dp.view(
    name="unified_fhir_patient",
    comment="Combines batch and streaming Patient data"
)
def unified_fhir_patient():
    """
    Union of batch and streaming Patient data.
    
    Use this view when you want to query all patients regardless of source.
    Deduplication is handled by resource_id.
    
    NOTE: Use spark.read.table() for batch reads (2026 best practice).
    Don't use dp.read() (old syntax, no longer documented).
    """
    # Batch patients (from file-based ingestion)
    batch_patients = spark.read.table("silver_fhir_patient").select(
        "id", "gender", "birth_date", "name_family", "name_given",
        "_ingestion_timestamp",
        lit("batch").alias("_source")
    )
    
    # Streaming patients
    streaming_patients = spark.read.table("silver_fhir_patient_streaming").select(
        "id", 
        # Parse same fields from raw_json
        lit("streaming").alias("_source")
    )
    
    # Union with deduplication (latest wins)
    return (
        batch_patients.union(streaming_patients)
        .withColumn("row_num", expr(
            "ROW_NUMBER() OVER (PARTITION BY id ORDER BY _ingestion_timestamp DESC)"
        ))
        .filter("row_num = 1")
        .drop("row_num")
    )


# =============================================================================
# Monitoring Tables
# =============================================================================

@dp.table(
    name="streaming_metrics",
    comment="Streaming pipeline metrics for monitoring"
)
def streaming_metrics():
    """
    Aggregate streaming metrics for monitoring dashboards.
    
    Tracks:
    - Messages per minute
    - Resource type distribution
    - Error rates
    
    NOTE: Use spark.read.table() for batch reads (2026 best practice).
    """
    return (
        spark.read.table("bronze_fhir_streaming")
        .withColumn("minute", expr("date_trunc('minute', event_timestamp)"))
        .groupBy("minute", "resource_type", "is_valid")
        .agg(
            expr("count(*) as message_count"),
            expr("min(event_timestamp) as first_event"),
            expr("max(event_timestamp) as last_event"),
        )
    )


# =============================================================================
# Example: FHIR Subscription Webhook Handler
# =============================================================================

"""
If your FHIR server supports Subscriptions, you can:
1. Create a FHIR Subscription resource pointing to your webhook endpoint
2. Have the webhook write to Kafka/Event Hubs
3. This pipeline processes in real-time

Example FHIR Subscription:
{
    "resourceType": "Subscription",
    "status": "active",
    "criteria": "Observation?code=http://loinc.org|8867-4",  # Heart rate
    "channel": {
        "type": "rest-hook",
        "endpoint": "https://your-webhook.com/fhir-events",
        "payload": "application/fhir+json"
    }
}

Your webhook then pushes to Kafka:
    producer.send("fhir-events", value=fhir_resource_json)
"""
