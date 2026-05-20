#!/usr/bin/env Rscript

# Upload data/international/results.csv to GCS, then load it into BigQuery dataset
# "analytics" (GCS mirrors Python-style staging; BQ load uses readr + bq_table_upload
# so literal "NA" scores in the CSV become NULL and are not mis-parsed as CSV text).
#
# R packages: install.packages(c("bigrquery", "googleCloudStorageR", "readr"))
#
# Environment (see .env.example): GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS
#
# Typical run (from anywhere under the repo, or with an absolute --file= path):
#   Rscript src/ingestion/upload_international_results.R

find_repo_root <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  ff <- sub("^--file=", "", args[startsWith(args, "--file=")])
  starts <- unique(c(
    normalizePath(getwd(), mustWork = TRUE),
    if (length(ff) && nzchar(ff[[1L]])) {
      normalizePath(dirname(ff[[1L]]), mustWork = TRUE)
    } else {
      character()
    }
  ))
  for (i in seq_along(starts)) {
    d <- starts[[i]]
    for (unused in seq_len(20L)) {
      if (file.exists(file.path(d, "environment.yml"))) {
        return(d)
      }
      parent <- dirname(d)
      if (identical(parent, d)) {
        break
      }
      d <- parent
    }
  }
  stop(
    "Could not locate the repository root (expected environment.yml). ",
    "`cd` into the capstone repo and run this script again."
  )
}

main <- function() {
  repo_root <- find_repo_root()
  env_path <- file.path(repo_root, ".env")
  if (file.exists(env_path)) {
    readRenviron(env_path)
  }

  project_id <- Sys.getenv("GCP_PROJECT_ID", "")
  if (!nzchar(project_id)) {
    stop("GCP_PROJECT_ID is not set; add it to .env or the environment.")
  }

  cred_raw <- Sys.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
  if (!nzchar(cred_raw)) {
    stop(
      "GOOGLE_APPLICATION_CREDENTIALS is not set; ",
      "point it at your service-account JSON (see README GCP setup)."
    )
  }

  cred_path <- if (startsWith(cred_raw, "/")) {
    cred_raw
  } else {
    normalizePath(file.path(repo_root, cred_raw), mustWork = TRUE)
  }
  if (!file.exists(cred_path)) {
    stop("Credential file not found: ", cred_path)
  }

  # ADC for googleCloudStorageR / gargle
  Sys.setenv(GOOGLE_APPLICATION_CREDENTIALS = cred_path)

  bucket <- "football-analytics-mds496219"
  dataset_id <- "analytics"
  table_id <- "international_results"
  local_csv <- file.path(repo_root, "data", "international", "results.csv")

  if (!file.exists(local_csv)) {
    stop("CSV not found: ", local_csv)
  }

  date_prefix <- format(Sys.Date(), "%Y-%m-%d")
  gcs_object <- sprintf("raw/international/results/%s/results.csv", date_prefix)
  gcs_uri <- sprintf("gs://%s/%s", bucket, gcs_object)

  suppressPackageStartupMessages({
    library(googleCloudStorageR)
    library(bigrquery)
    library(readr)
  })

  gcs_auth(json_file = cred_path)
  gcs_global_bucket(bucket)
  gcs_upload(local_csv, name = gcs_object)
  message("Uploaded ", local_csv, " -> ", gcs_uri)

  bq_auth(path = cred_path)
  dest <- bq_table(project_id, dataset_id, table_id)
  results <- read_csv(
    local_csv,
    na = c("", "NA"),
    lazy = FALSE,
    show_col_types = FALSE,
    col_types = cols(
      date = col_date(),
      home_team = col_character(),
      away_team = col_character(),
      home_score = col_integer(),
      away_score = col_integer(),
      tournament = col_character(),
      city = col_character(),
      country = col_character(),
      neutral = col_logical()
    )
  )
  bq_table_upload(
    dest,
    results,
    write_disposition = "WRITE_TRUNCATE"
  )
  n_rows <- bq_table_nrow(dest)
  message(
    "Loaded into ",
    project_id, ".", dataset_id, ".", table_id,
    " (", n_rows, " rows)."
  )
}

main()
