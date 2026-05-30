````markdown
# Enriching a Music Encyclopedia via Automatic Data Integration

This repository contains the code and notebooks developed for my bachelor thesis:

**Enriching a Music Encyclopedia via Automatic Data Integration**

The thesis investigates how release-level metadata in MusicBrainz can be enriched automatically by integrating heterogeneous external sources, including the HPI CD Dataset, WebTables from Web Data Commons, and Discogs. The pipeline focuses on source-specific entity resolution, provenance preservation, validation-tier classification, release-group propagation, and evaluation of the enriched catalogue.

## Repository Structure

```text
.
├── jupyter/      # Jupyter notebooks used for data processing, matching, enrichment, and evaluation
├── src/          # Supporting source code and reusable pipeline components
└── README.md     # Repository overview
````

## Main Pipeline

The enrichment pipeline follows these main steps:

1. Load MusicBrainz release data and external source snapshots.
2. Clean and normalise artist, title, label, and catalogue-number fields.
3. Generate candidate pairs using blocking keys.
4. Apply source-specific matching strategies for HPI, WebTables, and Discogs.
5. Preserve provenance for accepted matches.
6. Classify enrichment evidence into validation tiers.
7. Propagate selected release-group-level descriptors where appropriate.
8. Evaluate the final enriched catalogue.

## Data Sources

The thesis uses the following data sources:

- **MusicBrainz release data**  
  https://metabrainz.org/datasets/postgres-dumps  
  https://musicbrainz.org/doc/MusicBrainz_Database/Download

- **HPI CD Dataset**  
  https://hpi.de/naumann/projects/repeatability/datasets/cd-datasets.html

- **Web Data Commons WebTables**  
  https://webdatacommons.org/webtables/

- **Discogs release data**  
  https://data.discogs.com/

Due to size and licensing constraints, raw data dumps are not included in this repository. The notebooks assume that the required datasets are available locally in the expected data directories.

## Evaluation

The evaluation combines several complementary methods because no complete gold-standard alignment is available. These include source-side match-rate estimates, proxy precision, validation-tier analysis, Mean Hamming Distance, source overlap, dependency checks, duplicate analysis, and ablation analysis.

## Notes

This repository documents the implementation behind the thesis and supports reproducibility of the described pipeline. Some paths and intermediate files may need to be adapted depending on the local environment.
```
```
