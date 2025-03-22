#! /usr/bin/env python

import os

# To set the number of threads
num_threads = '1'
os.environ["OMP_NUM_THREADS"] = num_threads
os.environ["OPENBLAS_NUM_THREADS"] = num_threads
os.environ["MKL_NUM_THREADS"] = num_threads

from pathlib import Path
import mne
from mne.minimum_norm import (make_inverse_operator, apply_inverse, write_inverse_operator)

## ----- DEFINE PATHS ----- ##
BASE_PATH = Path('/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_auditory/')
cross_talk_file = BASE_PATH / 'calibration_MEG/old_MEG/ct_sparse_nspn.fif'
calibration_file = BASE_PATH / 'calibration_MEG/old_MEG/sss_cal_nspn.dat'
subjects_dir = BASE_PATH / 'derivatives/freesurfer/'
## ----------------------- ##

for subject_folder in subjects_dir.iterdir():    
    subject = subject_folder.name
    if not subject.startswith('sub-'):
        continue
    if subject in ['sub-17', 'sub-21', 'sub-23', 'sub-26']:
        continue

    evo_diff_dir = BASE_PATH / f'derivatives/preprocessed_data/{subject}/{subject}_evo_diff-ave.fif'
    evo_diff = mne.read_evokeds(evo_diff_dir)

    trans_fname = subjects_dir / subject / f'coreg/coreg_{subject}_ses-01_task-listen_run-05_meg_trans.fif'
    noise_cov = mne.read_cov(BASE_PATH / f'derivatives/preprocessed_data/{subject}/{subject}_noise-cov.fif')

    evo_diff = evo_diff[0]
    info = evo_diff.info
    
    # ------------- Source space ------------- #

    src = mne.setup_source_space(subject=subject,
                                spacing='oct6', 
                                subjects_dir=subjects_dir,
                                add_dist=False) 

    #mne.viz.plot_alignment(info=info, trans=trans_fname, subject=subject,
    #                    src=src, subjects_dir=subjects_dir, dig=True,
    #                    surfaces=['head-dense', 'white'], coord_frame='meg')
    
    preprocessed_dir = BASE_PATH / f'derivatives/preprocessed_data/'
    os.makedirs(preprocessed_dir / subject, exist_ok=True)
    src.save(preprocessed_dir / f'{subject}/{subject}-src.fif', overwrite=True)

    # ------------- Forward solution ------------- #

    conductivity = (0.3,) 
    model = mne.make_bem_model(subject=subject, ico=4,
                            conductivity=conductivity,
                            subjects_dir=subjects_dir)

    bem_sol = mne.make_bem_solution(model)

    fwd = mne.make_forward_solution(evo_diff_dir,
                                    trans=trans_fname,
                                    src=src,
                                    bem=bem_sol,
                                    meg=True, # include MEG channels
                                    eeg=False, # exclude EEG channels
                                    mindist=5.0, # ignore sources <= 5mm from inner skull
                                    n_jobs=1) # number of jobs to run in parallel

    del bem_sol, src

    fwd = mne.convert_forward_solution(fwd, surf_ori=True)

    fwd = mne.pick_types_forward(fwd, meg=True, eeg=False)

    fwd_fname = preprocessed_dir / f'{subject}/{subject}-fwd.fif'
    mne.write_forward_solution(fwd_fname, fwd, overwrite=True)

    # ------------- Inverse operator ------------- #

    inverse_operator = make_inverse_operator(info, fwd, noise_cov,
                                            loose=0.2, depth=0.8, rank = 'info')
    

    write_inverse_operator(preprocessed_dir / f'{subject}/{subject}-inv.fif', inverse_operator, overwrite=True)
    
    # ------------- Applying inverse operator ------------- #

    method = "dSPM"
    snr = 3.
    lambda2 = 1. / snr ** 2
    stc = apply_inverse(evo_diff, inverse_operator, lambda2,
                        method=method, pick_ori=None)

    stc.save(preprocessed_dir / f'{subject}/{subject}-stc.h5', overwrite=True)


brain = stc.plot(surface='inflated',
                 hemi='both',
                 subjects_dir=subjects_dir,
                 time_viewer=True)
