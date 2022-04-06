# Databricks on GCP
## _The best practice guide that you've been looking for_

## Introduction

[Databricks](https://www.databricks.com) provides a data lakehouse platform unifying the best of data warehouses and data lakes in one simple platform to handle all your data, analytics and AI use cases. It’s built on an open and reliable data foundation that efficiently handles all data types and applies one common security and governance approach across all of your data and cloud platforms.

In this guide we'll share with you architectural patterns and design guidelines to:
* Infrastruture planning
* Platform Security and Architecture
* Provisioning the [workspace](https://docs.gcp.databricks.com/workspace/index.html)
* Identity and Access Management
* Observability and Monitoring
* Cost Management, Charge backs & Analysis

## Consuming Databricks on GCP
Databricks service is available as a GCP market place offering and the unit of deployment is called a [`workspace`](https://docs.gcp.databricks.com/getting-started/concepts.html#workspace), from here onwards we'll be using `workspace` to refer to databricks service through out this guide.

* Trying databricks in an indidvidual capacity? here's your 14 days free [trial](https://docs.gcp.databricks.com/getting-started/try-databricks-gcp.html#start-a-databricks-free-trial) Please note that free trial requires credit card and the trial is converted to a pay-as-you-go subscription after 14 days. Not ready for this? then check out our [community edition](https://community.cloud.databricks.com/login.html), no credit card required.
* If your company has a contract subscription in place with GCP, you have two options:
  *  start the free trial and at the end of trial become a pay-as-you-go customer or end the trial.
  *  for any reason have a need to extend the trial then reach out to your databricks representative or send an email to `sales@databricks.com` about how to create/extend your subscription with a Google Marketplace Private Offer.

| Databricks  | Relationship  | GCP  |
|---|---|---|
| Account  |  1:1 maps to | [Billing Account](https://cloud.google.com/billing/docs/concepts#overview)  |
| Subscription | maps to | Entitlements* |
| Workspaces | resides in | [Consumer Project](https://cloud.google.com/resource-manager/docs/creating-managing-projects) |
| Worker Environment (dataplane) | 1:1 maps to | GKE cluster |
| Databricks Cluster | 1:1 maps to | GKE namespace |

*Represents purchase, pricing, and payment mechanism for an account

*Things to remember*
* Customer can have more than one GCP Billing Accounts
* Customer can have more than one Databricks Accounts
* Each Databricks account is mapped to one Billing Account (1:1)
* Subscription is a Databricks concept, it represent various [tiers](https://databricks.com/product/gcp-pricing) available to our customers
* Subscription tiers dictates workspace features as well [pricing](https://databricks.com/product/gcp-pricing/instance-types)
* Subscription [cost](https://databricks.com/product/pricing) does not include cloud resource cost (storage, compute, network)
* Cloud resource cost is billed separately by GCP

## Availability Regions
Please refer to public doc site for [supported regions](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/regions.html)

## Workspace Architecture
From [here](https://docs.gcp.databricks.com/getting-started/overview.html#high-level-architecture): Databricks is built on GCP and operates out of a `control plane` and a `data plane`.

The `control plane` includes the backend services that Databricks manages in its own Google Cloud account. Notebook commands and many other workspace configurations are stored in the control plane and encrypted at rest.

The `data plane` is managed by `your` Google Cloud account and is where `your data resides`. This is also where `data is processed`. You can use Databricks [connectors](https://docs.gcp.databricks.com/data/data-sources/index.html) so that your databricks clusters can `connect to data sources` to ingest data or for storage. You can also ingest data from external streaming data sources, such as events data, streaming data, IoT data, and more.

The following diagram represents the flow of data for Databricks on Google Cloud:

![workspace-architecture](https://docs.gcp.databricks.com/_images/databricks-architecture-gcp.png)

*Things to remember*
* There's a 1:1 mapping between a workspace and GKE cluster and a workspace can atmost have 1 GKE cluster
* GKE cluster is managed by Databricks and runs under Customer's GCP Project, using customer's vpc
* Workspace use GKE cluster in a multi-tenant fashion i.e. each Databricks cluster is mapped to a GKE namespace and is isolated from other databricks clusters running within same GKE, more details under `Data Plane Architecture` section
* There's a:
  * 1:1 mapping between a workspace and GCP Project
  * A workspace  

## Workspace Deployment Considerations
* How many workspaces do I need?
* Do I need workspace per project or a team or a buisness unit?
* Can I share workspaces among teams?




### Prerequisites

This is an example of how to list things you need to use the software and how to install them.
* npm
  ```sh
  npm install npm@latest -g
  ```

### Installation

1. Get a free API Key at [https://example.com](https://example.com)
2. Clone the repo
   ```sh
   git clone https://github.com/github_username/repo_name.git
   ```
3. Install NPM packages
   ```sh
   npm install
   ```
4. Enter your API in `config.js`
   ```js
   const API_KEY = 'ENTER YOUR API';
   ```
   
<!-- USAGE EXAMPLES -->
## Usage

Use this space to show useful examples of how a project can be used. Additional screenshots, code examples and demos work well in this space. You may also link to more resources.

_For more examples, please refer to the [Documentation](https://example.com)_





<!-- ROADMAP -->
## Roadmap

- [ ] Feature 1
- [ ] Feature 2
- [ ] Feature 3
    - [ ] Nested Feature

See the [open issues](https://github.com/github_username/repo_name/issues) for a full list of proposed features (and known issues).




<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- CONTACT -->
## Contact

Project Link: [https://github.com/bhavink/databricks/gcpdb4u](https://github.com/bhavink/databricks/gcpdb4u)


<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* []()
* []()
* []()

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
