#! /usr/bin/env python

import os

# To set the number of threads
num_threads = '1'
os.environ["OMP_NUM_THREADS"] = num_threads
os.environ["OPENBLAS_NUM_THREADS"] = num_threads
os.environ["MKL_NUM_THREADS"] = num_threads

import mne
import numpy as np
from mne import read_source_estimate
from pathlib import Path
from mne.datasets import fetch_fsaverage

BASE_PATH = Path('/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_auditory')
subjects_dir = BASE_PATH / 'derivatives/freesurfer/'
stc_list = []

#fsaverage_dir = fetch_fsaverage(subjects_dir=subjects_dir) # si besoin de récupérer fichier fsaverage

fsaverage = 'fsaverage'

for subject_folder in subjects_dir.iterdir():
    subject = subject_folder.name
    if not subject.startswith('sub-'):
        continue
    if subject in ['sub-17', 'sub-21', 'sub-23', 'sub-26']:
        continue
    
    stc_fname = BASE_PATH / f'derivatives/preprocessed_data/{subject}/{subject}-stc.h5'
    stc = read_source_estimate(stc_fname)
    
    morph = mne.compute_source_morph(stc, subject_from=subject, subject_to=fsaverage, 
                                     subjects_dir=subjects_dir)
    
    stc_fsaverage = morph.apply(stc)
    
    stc_fsaverage.data /= np.max(stc_fsaverage.data)

    stc_list.append(stc_fsaverage)

stc_mean = np.mean([s.data for s in stc_list], axis=0)

stc_avg = stc_list[0].copy()
stc_avg._data = stc_mean

output_stc_avg = BASE_PATH / 'derivatives/preprocessed_data/stc_avg.h5'
stc_avg.save(output_stc_avg, ftype='h5', overwrite=True)

#stc_avg = mne.read_source_estimate(output_stc_avg) # to read it

brain = stc_avg.plot(subject=fsaverage, subjects_dir=subjects_dir, time_viewer=True,
                     hemi='both', smoothing_steps=5, time_unit='s')
