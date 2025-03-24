#!/usr/bin/env python

import pandas as pd
import os, re, mne
from pathlib import Path
from mne_bids import BIDSPath, write_raw_bids

# Set mne only for errors, no warnings
mne.set_log_level("ERROR")

# Load configuration file
with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

# Load general parameters of the study
STUDY = config["study"]
TASK = config["task"]
SESSION = config["session"]
MEG_DIR = config["meg_dir"]
RUNS = config["runs"]

# Define paths from config
BASE_PATH = Path(config["base_path"])
METADATA = config["metadata"]
BIDS_PATH = BASE_PATH / 'bids'
RAW_DATA_PATH = BASE_PATH / 'raw'
TASK = 'distraction'

dict_nip_to_sn = {'fa_123456': '1','mn_240236': '2', 'to_220041': '3', 'sg_230179': '4',
                  'mb_220766': '5', 'ka_230246' : '6', 'tm_240091' : '7', 'fb_210353': '8',
                  'lr_210454': '9', 'da_240251': '10', 'll_180197' : '11'}

# For each of these folders, go into the sub folder
for folder in RAW_DATA_PATH.iterdir():
    sub_dir = RAW_DATA_PATH / folder / 'cropped_runs'
    for file in os.listdir(sub_dir):
        if file.endswith('.fif'):
            nip = str(folder).split('/')[-1]
            sub = dict_nip_to_sn[nip]

            # Extract run number
            match = re.search(r"run_(\d+)\.fif", file)
            if match:
                run = match.group(1)
            else:
                print(f"No run number found for file: {file}")
                continue

            # Check if the BIDS dataset already exists:
            run = int(run)
            fname = f"sub-{sub}/ses-01/meg/sub-{sub}_task-{TASK}_run-{run:02d}_meg.fif"
            if (BIDS_PATH / fname).exists():
                print(f"The file {fname} already exists: not created again.")
                continue

            # Open the raw file
            raw = mne.io.read_raw_fif(sub_dir / file, allow_maxshield=True)

            # Create a BIDS path with the correct parameters
            bids_path = BIDSPath(subject=sub, session=SESSION, run=run,
                                 datatype='meg', root=BIDS_PATH)
            bids_path.task = TASK

            # Write the BIDS path from the raw file
            write_raw_bids(raw, bids_path=bids_path, overwrite=True)
        else:
            print(f"Skipping file {file}")
            continue

# Putting the generated annotation files in the correct directories
for sub in os.listdir(BIDS_PATH):
    if sub.startswith('sub-'):
        SUBJ_PATH_BIDS = BIDS_PATH / f'{sub}/meg'
        files_bids = os.listdir(SUBJ_PATH_BIDS)
        for file in files_bids:
            match = re.search(r"run-(\d+)_meg\.fif", file)
            if match:
                run = match.group(1)
                run = int(run)
                try:
                    df = pd.read_csv(METADATA / f'task-distraction_run-{run:02d}_extra_info.csv', sep='\t')

                    df.to_csv(f'{SUBJ_PATH_BIDS}/{sub}_task-{TASK}_run-{run:02d}_events.tsv', sep='\t')
                except FileNotFoundError:
                    print(f"No metadata file for {run}")
                    continue
print(f"\n \n ***************************************************\
\n Script finished!\n \
***************************************************\
\n Folder created: \n For bids: {BIDS_PATH} \n ")