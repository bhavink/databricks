terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }

  
}

provider "google" {
  project     = var.vpc_project_id
 ***REMOVED*** region      = var.vpc_project_region
}

provider "google-beta" {
  project     = var.vpc_project_id
***REMOVED***  region      = var.vpc_project_region
} 