#! /usr/bin/env python

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import mne_bids, mne, os

BASE_PATH = Path('/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/')
subjects_dir = BASE_PATH / 'LPP_MEG_auditory/derivatives/preprocessed_data/'

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
evo_diff_all.plot_joint(times=times, title='Auditory response', picks='meg', exclude = 'bads')
evo_diff_all.plot_topomap(ch_type='mag', times=times, colorbar=True)

evo_diff_all.plot_topomap(times, ch_type="mag", average=0.05)

fig = evo_diff_all.plot_topomap(0.2, ch_type="mag", show_names=True, colorbar=False, size=6, res=128)
fig.suptitle("Auditory response")


## N400 response ##

temporal_left_channels_post = ['MEG0241', 'MEG0231', 'MEG1611', 'MEG1621', 
                          'MEG1811', 'MEG1641', 'MEG1631', 'MEG1841']  

temporal_left_channels = [
    'MEG0121',
    'MEG0122',
    'MEG0123',
    'MEG0141',
    'MEG0142',
    'MEG0143',
    'MEG0241',
    'MEG0242',
    'MEG0243',
    'MEG0341',
    'MEG0342',
    'MEG0343',
    'MEG0541',
    'MEG0542',
    'MEG0543',
    'MEG0641',
    'MEG0642',
    'MEG0643']

picks_temporal_left_post = mne.pick_channels(evo_diff_all.ch_names, temporal_left_channels_post)
picks_temporal_left = mne.pick_channels(evo_diff_all.ch_names, temporal_left_channels)

picks_mag = mne.pick_types(evo_diff_all.info, meg='mag', exclude='bads')

picks_temporal_left_mag_post = np.intersect1d(picks_temporal_left_post, picks_mag)
picks_temporal_left_mag = np.intersect1d(picks_temporal_left, picks_mag)

data_temporal_left_mag_post = evo_diff_all.data[picks_temporal_left_mag_post]
data_temporal_left_mag = evo_diff_all.data[picks_temporal_left_mag]

mean_temporal_left_mag_post = np.mean(data_temporal_left_mag_post, axis=0)
mean_temporal_left_mag = np.mean(data_temporal_left_mag, axis=0)

times = evo_diff_all.times

max_index = np.argmax(mean_temporal_left_mag)

max_time = times[max_index]

#print(f"Le maximum de la réponse N400 est atteint à {max_time:.3f} secondes.")

highlight_start = max_time - 0.1  # -100 ms
highlight_end = max_time + 0.1    # +100 ms

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(times, mean_temporal_left_mag_post, label='N400 Response - Temporal Left Post Channels (Mag)')
ax.plot(times, mean_temporal_left_mag, label='N400 Response - Temporal Left Channels (Mag)')
ax.set_title('N400 Response - Temporal Left Channels (Mag)')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Amplitude (fT)')
ax.axvline(x=0, color='k', linestyle='--', label='Stimulus Onset') 

#ax.axvspan(highlight_start, highlight_end, color='yellow', alpha=0.5, label='Highlight Zone (-100 to +100 ms)')

ax.legend()
plt.show()
