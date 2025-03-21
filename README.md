# MEG Pipeline: From Raw Data to Source Reconstruction

Welcome to the **MEG Pipeline**! This repository contains a comprehensive and modular pipeline for processing MEG data, from raw data preparation to source reconstruction. The pipeline is designed to be easy to use, reproducible, and adaptable to various datasets.

---

## Table of Contents
1. [Overview](#overview)
2. [Pipeline Structure](#pipeline-structure)
3. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Running the Pipeline](#running-the-pipeline)
4. [Pipeline Steps](#pipeline-steps)
   - [01_finding-data](#01_finding-data)
   - [02_data-preparation](#02_data-preparation)
   - [03_bids-conversion](#03_bids-conversion)
   - [04_meg-preprocessing](#04_meg-preprocessing)
   - [05_anat-preprocessing](#05_anat-preprocessing)
   - [06_source-reconstruction](#06_source-reconstruction)
5. [Outputs](#outputs)

---

## 1. Overview 👀

This pipeline processes MEG data through a series of well-defined steps, ensuring high-quality results for source reconstruction. It includes:

- 📂 **Data preparation [Optional]**: Cropping and organizing raw data.
- 💱 **BIDS conversion**: Converting data to the Brain Imaging Data Structure (BIDS) format.
- 🧹 **Preprocessing**: Filtering, noise covariance estimation, and artifact removal.
- 📊 **Anatomical preprocessing**: FreeSurfer reconstruction, BEM creation, and coregistration.
- 🧠 **Source reconstruction**: Estimating neural activity and generating reports.

The pipeline is implemented using a combination of Python scripts, shell scripts, and Jupyter notebooks, and can be run using a **Makefile** for automation.

![Pipeline Overview](images/pipeline.png "Pipeline Overview")

---

## 2. Pipeline Structure 🏗️

The pipeline is organized into the following directories:
```
.
├── 01_finding-data
├── 02_data-preparation
├── 03_bids-conversion
├── 04_meg-preprocessing
├── 05_anat-preprocessing
├── 06_source-reconstruction
└── README.md
```

Each directory corresponds to a specific step in the pipeline. Below is a brief description of each step.

---

## 3. Getting Started 📍

### Prerequisites

Before running the pipeline, ensure you have the following installed:

- **Python 3.8+**
- **MNE-Python** (for MEG processing)
- **FreeSurfer** (for anatomical preprocessing)
- **Jupyter Notebook** (for data exploration)
- **BIDS Validator** (for BIDS compliance checking)
- **Make** (for running the pipeline)

### Installation 

1. Clone this repository:
   ```bash
   git clone https://github.com/jubnr/meg-pipeline.git
   cd meg-pipeline
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up FreeSurfer
    * Follow the FreeSurfer installation [guide](https://surfer.nmr.mgh.harvard.edu/fswiki/DownloadAndInstall).
    * Ensure the FreeSurfer environment is sourced in your shell:
        ```bash
        export FREESURFER_HOME=/path/to/freesurfer
        source $FREESURFER_HOME/SetUpFreeSurfer.sh
        ```

### Running the Pipeline
To run the entire pipeline, use the provided Makefile:
   ```bash
    make all
```

To run a specific step (e.g., MEG preprocessing):
   ```bash
    make meg-preprocessing
```

---

## 4. Pipeline Steps 📋

### 01_finding-data

**Purpose:** Identify and organize raw data files.

**Input:** Raw MEG and MRI data.

**Output:** List of participants and anatomical MRI files.

**Scripts:**

- `find_anat_mri.ipynb` (Jupyter notebook for finding anatomical MRI files)

- `participants_to_import.tsv` (List of participants to process)

### 02_data-preparation

**Purpose:** Prepare raw data for processing. This step is **optional**.

**Input:** Raw MEG data.

**Output:** Cropped MEG runs.

**Scripts:** `crop_runs.py` (Python script for cropping MEG runs)

### 03_bids-conversion

**Purpose:** Convert data to BIDS format.

**Input:** MEG runs (.fif files).

**Output:** BIDS-compliant dataset.

**Scripts:** `formatting_distraction.py` (Python script for BIDS conversion)

### 04_meg-preprocessing

**Purpose:** Preprocess MEG data.

**Input:** BIDS dataset.

**Output:** Preprocessed MEG data and noise covariance.

**Scripts:**

- Python script for MEG preprocessing: `01_preprocessing.py`
- Python script for noise covariance estimation: `02_get_noise_cov.py`

### 06_anat-preprocessing

**Purpose:** Preprocess anatomical data.

**Input:** Anatomical MRI data.

**Output:** FreeSurfer reconstruction, BEM model, and coregistration.

**Scripts:**

- Shell script for FreeSurfer reconstruction: `01_run_freesurfer_on_subject_id.sh` 
- Shell script for batch FreeSurfer processing: `02_run_freesurfer_on_all_subjects.sh`
- Python script for BEM creation: `03_bem.py`
- Python script for coregistration: `04_coreg.py`
 
### 07_source-reconstruction

**Purpose:** Perform source reconstruction and generate reports.

**Input:** Preprocessed MEG and anatomical data.

**Output:** Source estimates, morphed data, and reports.

**Scripts:**

- Python script for source estimation: `01_get_source_estimate.py`
- Python script for morphing source estimates: `02_stc_morphing.py`
- Python script for visualization: `03_plotting.py`
- Python script for generating reports: `04_make_report.py`

---

## 5. Outputs

The pipeline generates the following outputs:

* **BIDS-compliant dataset:** Organized and standardized data.
* **Preprocessed MEG data:** Filtered and cleaned MEG data.
* **Noise covariance:** Estimated noise covariance matrix.
* **FreeSurfer reconstruction:** Anatomical surfaces and labels.
* **BEM model:** Boundary element model for forward modeling.
* **Coregistration:** Alignment of MEG and MRI data.
* **Source estimates:** Reconstructed neural activity.
* **Reports:** Visualizations and summaries of results.

---