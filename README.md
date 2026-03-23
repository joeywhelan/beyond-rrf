# Beyond Rank Fusion: A Practical Guide to Elasticsearch Retrievers
## Contents
1.  [Summary](#summary)
2.  [Architecture](#architecture)
3.  [Features](#features)
4.  [Prerequisites](#prerequisites)
5.  [Installation](#installation)
6.  [Usage](#usage)

## Summary <a name="summary"></a>
  A step-by-step Elasticsearch notebook comparing retriever strategies on a hand tools product catalog. BM25 and semantic search form the baseline, but neither alone gives the full picture. RRF merges rank positions but can't distinguish a strong #1 from a weak one. Linear adds score magnitudes and weight tuning. The Rescorer layers on business signals like sales velocity, ratings, and stock status — letting you inject constraints that no query can express.   
## Architecture <a name="architecture"></a>
![architecture](assets/arch.png) 


## Features <a name="features"></a>
- Jupyter notebook
- Builds an Elastic Serverless deployment via Terraform
- Creates a data set on hand tools.
- Utilizes the Jina embeddings v5 model to embed the product descriptions.
- Performs various hybrid search scenarios over RRF, Linear combination, and Rescoring to differentiate those techniques
- Deletes the entire deployment via Terraform

## Prerequisites <a name="prerequisites"></a>
- terraform
- Elastic Cloud account and API key
- Python

## Installation <a name="installation"></a>
- Edit the terraform.tfvars.sample and rename to terraform.tfvars
- Create a Python virtual environment

## Usage <a name="usage"></a>
- Execute notebook