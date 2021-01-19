Azure Databricks with ADLS Gen2
==============
Documenting and sharing best practices related to using ADLS Gen2 with ADB.


***REMOVED******REMOVED******REMOVED*** Accessing ADLS
- ***REMOVED******REMOVED******REMOVED******REMOVED*** [Demo video](https://drive.google.com/file/d/1o9j6KIgQd-EjvEQiHEnu-I6A9aHnwn22/view?usp=sharing)
- ***REMOVED******REMOVED******REMOVED******REMOVED*** [Access directly using storage account key](https://docs.microsoft.com/en-us/azure/databricks/data/data-sources/azure/azure-datalake-gen2***REMOVED***--access-directly-using-the-storage-account-access-key)
- ***REMOVED******REMOVED******REMOVED******REMOVED*** Access using service principal
    - [Directly](https://docs.microsoft.com/en-us/azure/databricks/data/data-sources/azure/azure-datalake-gen2***REMOVED***create-and-grant-permissions-to-service-principal) or
    - [Mount](https://docs.microsoft.com/en-us/azure/databricks/data/data-sources/azure/azure-datalake-gen2***REMOVED***--mount-an-azure-data-lake-storage-gen2-account-using-a-service-principal-and-oauth-20) points
      - mount points available to all the users
    - ***REMOVED******REMOVED******REMOVED******REMOVED*** Best suited for:    
     - Ideal for running jobs, automated workloads
     - Best suited for auto-pilot data-eng workloads
- ***REMOVED******REMOVED******REMOVED******REMOVED*** [AAD credential pass thru](https://docs.microsoft.com/en-us/azure/databricks/data/data-sources/azure/azure-datalake-gen2***REMOVED***---access-automatically-with-your-azure-active-directory-credentials)
  - Ideal for interactive analytical workloads
  - Supports mount points
  - Available for ADLS Gen2, PowerBI, Synapse DW
