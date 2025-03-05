# Jobs Monitoring Guide

This guide provides best practices for monitoring jobs in Databricks on Google Cloud, ensuring efficient troubleshooting, performance optimization, and cost control. Based on the official Databricks documentation: [Monitor Databricks Jobs](https://docs.databricks.com/gcp/en/jobs/monitor).

## Table of Contents
1. [View Job Runs](#view-job-runs)
2. [Monitor Job Run Details](#monitor-job-run-details)
3. [Set Up Alerts](#set-up-alerts)
4. [Analyze Job Performance](#analyze-job-performance)
5. [Monitor Job Costs](#monitor-job-costs)
6. [Use REST API for Monitoring](#use-rest-api-for-monitoring)

## View Job Runs
- Access job run history via the **Jobs UI** in Databricks.
- Navigate to **Workflows > Jobs** to see scheduled and manual job runs.
- Filter job runs based on **status, start time, duration, and cluster used**.
- Reference: [Jobs UI](https://docs.databricks.com/gcp/en/jobs/index.html#jobs-ui).

## Monitor Job Run Details
- Click on a specific job run to view logs, execution graphs, and detailed metrics.
- Review the **task execution timeline** to identify bottlenecks.
- Use **cluster logs** and **Spark UI** to debug failures.
- Reference: [Spark UI](https://docs.databricks.com/gcp/en/clusters/spark-ui.html).

## Set Up Alerts
- Enable **failure notifications** via email or webhooks in job settings.
- Use **Databricks Alerts** to trigger actions when jobs meet specific conditions.
- Configure alerts in the **Jobs UI** under the **Notifications** tab.
- Reference: [Databricks Alerts](https://docs.databricks.com/gcp/en/alerts/index.html).

## Analyze Job Performance
- Use **Ganglia Metrics** and **Spark UI** to analyze resource usage.
- Optimize job execution by tuning cluster settings, caching, and parallelism.
- Identify long-running tasks and optimize data partitioning.
- Reference: [Performance Tuning](https://docs.databricks.com/gcp/en/clusters/performance.html).

## Monitor Job Costs
- Use the **Usage Dashboard** to track compute and storage costs.
- Identify high-cost jobs and optimize resource allocation.
- Enable **job-level tagging** to track costs by project or team.
- Reference: [Databricks Usage Dashboard](https://docs.databricks.com/gcp/en/admin/account-settings/usage.html).

## Use REST API for Monitoring
- Retrieve job run details programmatically using the Databricks Jobs API.
- Automate monitoring by integrating with external dashboards or alerting systems.
- API Example: 
  ```bash
  curl -X GET https://<databricks-instance>/api/2.1/jobs/runs/list \
       -H "Authorization: Bearer <your-token>"
  ```
- Reference: [Databricks Jobs API](https://docs.databricks.com/api/workspace/jobs).

For more details, refer to the official [Databricks Jobs Monitoring Documentation](https://docs.databricks.com/gcp/en/jobs/monitor).

---
Following these best practices ensures reliable job execution, proactive troubleshooting, and optimized performance in Databricks on Google Cloud.
