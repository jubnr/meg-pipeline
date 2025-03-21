import matplotlib, nibabel, pyvista, PyQt5, os, scipy.ndimage
import matplotlib.pyplot as plt
matplotlib.use('Agg')
pyvista.OFF_SCREEN = True
import mne_bids, mne
from mne.preprocessing import find_bad_channels_maxwell
from mne.preprocessing import maxwell_filter
from mne.minimum_norm import (make_inverse_operator, apply_inverse, write_inverse_operator)
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import seaborn as sns
from mne.report import Report

## ----------- Evo diff plotting ----------- ##

BASE_PATH = Path('/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_auditory')
subjects_dir = BASE_PATH / 'derivatives/preprocessed_data/'

all_evokeds = []

for subject in os.listdir(subjects_dir):
    if not subject.startswith('sub-'):
        continue
    if subject in ['sub-17', 'sub-21', 'sub-23', 'sub-26']:
        continue
    epo_file = subjects_dir / subject / f'{subject}_evo_diff-ave.fif'   
    evoked_list = mne.read_evokeds(epo_file)
    evoked = evoked_list[0] 
    all_evokeds.append(evoked)

evo_diff_all = mne.grand_average(all_evokeds)

times = np.linspace(-0.5, 0.8, 10)
fig = evo_diff_all.plot_joint(times=times, title='Auditory response', picks='meg', exclude = 'bads')


report = mne.Report(title="Source Reconstruction - LPP auditory paradigm (all subjects)")
report.add_figure(fig=fig, title="Evo diff across all subjects")  
report.save("report_evoked_response.html", overwrite=True)

## STC ##


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

report.add_stc(
    stc=stc_avg,
    subject=fsaverage,
    subjects_dir=subjects_dir,
    title="Source estimate",
    n_time_points=100  
)
report.save("report_stc.html", overwrite=True)
