#! /usr/bin/env python

import os

num_threads = '1'
os.environ["OMP_NUM_THREADS"] = num_threads
os.environ["OPENBLAS_NUM_THREADS"] = num_threads
os.environ["MKL_NUM_THREADS"] = num_threads

from pathlib import Path
import argparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import mne_bids
import mne

BASE_PATH = Path('/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/')
subjects_dir = BASE_PATH / 'LPP_MEG_auditory/derivatives/preprocessed_data/'
cross_talk_file = BASE_PATH / 'calibration_MEG/old_MEG/ct_sparse_nspn.fif'
calibration_file = BASE_PATH / 'calibration_MEG/old_MEG/sss_cal_nspn.dat'

def get_noise_cov(subject):
    raw_for_cov = []

    for i in range(1, 10):
        raw_fname = BASE_PATH / f'LPP_MEG_auditory/derivatives/preprocessed_data/{subject}/{subject}_ses-01_task-listen_run-0{i}_meg_raw_sss.fif'

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
