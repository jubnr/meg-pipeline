#!/usr/bin/env python

import os, yaml, mne
from pathlib import Path

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

NUM_THREADS = str(config["num_threads"])
os.environ["OMP_NUM_THREADS"] = NUM_THREADS
os.environ["OPENBLAS_NUM_THREADS"] = NUM_THREADS
os.environ["MKL_NUM_THREADS"] = NUM_THREADS

BASE_PATH = Path(config["base_path"])
SUBJECTS_DIR = BASE_PATH / config["subjects_dir"]
CROSS_TALK_FILE = BASE_PATH / config["cross_talk_file"]
CALIBRATION_FILE = BASE_PATH / config["calibration_file"]

SPECIFIC_SUBJECTS = config.get("subjects", []) 
if isinstance(SPECIFIC_SUBJECTS, str):  
    SPECIFIC_SUBJECTS = [SPECIFIC_SUBJECTS]

def get_noise_cov(SUBJECT):
    raw_for_cov = []

    for i in range(1, 10):

        raw_fname = BASE_PATH / f"{STUDY}/derivatives/preprocessed_data/{SUBJECT}/{SUBJECT}_{SESSION}task-{TASK}_run-0{i}_meg_raw_sss.fif"
        raw = mne.io.read_raw_fif(raw_fname, allow_maxshield=True)

        events = mne.find_events(raw, stim_channel='STI101')

        tmin = events[0][0] / raw.info['sfreq']
        tmax=events[1][0]/raw.info['sfreq']
        raw.crop(tmin=tmin, tmax=tmax)

        raw_for_cov.append(raw)

    concatenated_raws = mne.concatenate_raws(raw_for_cov)
    noise_cov = mne.compute_raw_covariance(concatenated_raws,method=['shrunk', 'empirical'], rank='info')

    return noise_cov

    #info = evoked.info #load evoked before
    #noise_cov.plot(info, proj=True)

for subject_folder in subjects_dir.iterdir():
    subject = subject_folder.name
    if not subject.startswith('sub-'):
        continue
    if subject in ['sub-17', 'sub-21', 'sub-23', 'sub-26']:
        continue

    noise_cov = get_noise_cov(subject)

    os.makedirs(BASE_PATH / f'LPP_MEG_auditory/derivatives/preprocessed_data/{subject}', exist_ok=True)
    noise_cov.save(BASE_PATH / f'LPP_MEG_auditory/derivatives/preprocessed_data/{subject}/{subject}_noise-cov.fif', overwrite=True)
