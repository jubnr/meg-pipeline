#! /usr/bin/env bash
# take a list of subjects id as arguments

SUBJECT_DIR=/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_visual/freesurfer
ANAT_DIR=/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_visual

for s in $@; do
    T1PATH=${ANAT_DIR}/sub-${s}/ses-01/anat/sub-${s}_ses-01_T1w.nii.gz
    echo recon-all -s sub-${s} -i ${T1PATH} -all &
done
