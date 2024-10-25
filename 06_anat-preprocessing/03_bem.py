#! /usr/bin/env python

import os
import mne
import mne_bids

# Subjects folder
subjects_dir = "/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/freesurfer"

# BEM function
def run_bem(subjects_dir, subject_id):
    bem_dir = os.path.join(subjects_dir, subject_id, "bem")
    if not os.path.exists(bem_dir):
        mne.bem.make_watershed_bem(
            subject=subject_id,
            subjects_dir=subjects_dir,
            copy=True,
            overwrite=True,
            show=False
        )

        mne.bem.make_scalp_surfaces(
            subject=subject_id,
            subjects_dir=subjects_dir,
            force=True,
            overwrite=True
        )
        print(f"BEM done for subject {subject_id}")
    else:
        print(f"BEM folder already exists for subject {subject_id}. Skipping BEM processing.")

if __name__ == "__main__":
    # Iterate over subjects in the directory
    for subject_id in os.listdir(subjects_dir):
        if subject_id.startswith("sub-"):
            run_bem(subjects_dir, subject_id)
