Azure Databricks with ADLS Gen2
==============
Documenting and sharing best practices related to using ADLS Gen2 with ADB.


### Accessing ADLS
- #### [Demo video](https://drive.google.com/file/d/1o9j6KIgQd-EjvEQiHEnu-I6A9aHnwn22/view?usp=sharing)
- #### [Access directly using storage account key](https://docs.microsoft.com/en-us/azure/databricks/data/data-sources/azure/azure-datalake-gen2#--access-directly-using-the-storage-account-access-key)
- #### Access using service principal
    - [Directly](https://docs.microsoft.com/en-us/azure/databricks/data/data-sources/azure/azure-datalake-gen2#create-and-grant-permissions-to-service-principal) or
    - [Mount](https://docs.microsoft.com/en-us/azure/databricks/data/data-sources/azure/azure-datalake-gen2#--mount-an-azure-data-lake-storage-gen2-account-using-a-service-principal-and-oauth-20) points
      - mount points available to all the users
    - #### Best suited for:    
     - Ideal for running jobs, automated workloads
     - Best suited for auto-pilot data-eng workloads
- #### [AAD credential pass thru](https://docs.microsoft.com/en-us/azure/databricks/data/data-sources/azure/azure-datalake-gen2#---access-automatically-with-your-azure-active-directory-credentials)
  - Ideal for interactive analytical workloads
  - Supports mount points
  - Available for ADLS Gen2, PowerBI, Synapse DW
