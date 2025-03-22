#!usr/bin/env python
# coding: UTF-8

from pathlib import Path
import mne, argparse
from mne.coreg import Coregistration
from mne.io import read_info
import numpy as np

def automated_coreg(subject, subjects_dir, meg_dir):
    """
    Coregister MEG runs for a given subject and session.
    
    Parameters:
    - subject: str, subject identifier (e.g., 'sub-11')
    - subjects_dir: str or Path, path to the directory where the Freesurfer subjects are stored
    - meg_dir: str or Path, path to the directory where the MEG .fif files are stored
    - task: str, task identifier (e.g., 'read', 'listen' or 'distraction')
    """

    task = input("Task: ")
    meg_dir = Path(meg_dir)
    subjects_dir = Path(subjects_dir)
    output_dir = Path("/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_distraction/derivatives/preprocessed_data/")

    # Ensure the output directory exists
    if not output_dir.exists():
        print(f"Creating output directory at {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

    middle_run_path = meg_dir / f'{subject}_task-{task}_run-14_meg.fif' # TO CHANGE WITH YOUR RUN NUMBER

    # Extract run number from the file name
    run_number = middle_run_path.stem.split('_')[-2]

    # Printing colors
    CRED = '\033[91m'
    CBLUE = '\033[34m'
    CYELLOW = '\033[103m'
    CGREEN = '\033[92m'
    CEND = '\033[0m'

    print(CBLUE + f"Loading files for {subject}, {run_number}..." + CEND)

    # Read MEG information
    info = read_info(str(middle_run_path))

    # Coregistration settings
    plot_kwargs = dict(
        subject=subject,
        subjects_dir=str(subjects_dir),
        surfaces="head-dense",  
        dig=True,
        eeg=[],
        meg="sensors",
        show_axes=True,
        coord_frame="meg",
    )

    # use fsaverage if no T1 MRI is available
    
    view_kwargs = dict(azimuth=45, elevation=90, distance=0.6, focalpoint=(0.0, 0.0, 0.0))

    input(CYELLOW + f"Press Enter to start coregistration for {subject}, {run_number}" + CEND)
    
    # Perform coregistration
    print(CBLUE + "Fitting fiducials..." + CEND)
    fiducials = "auto"
    coreg = Coregistration(info, subject, str(subjects_dir), fiducials=fiducials)
    #fig = mne.viz.plot_alignment(info, trans=coreg.trans, **plot_kwargs)

    # Set fiducial matching
    coreg.set_fid_match("matched") 

    coreg.fit_fiducials(verbose=True)
    #fig = mne.viz.plot_alignment(info, trans=coreg.trans, **plot_kwargs)
    print(CGREEN + "Fiducials done!" + CEND)


    coreg.fit_icp(n_iterations=6, verbose=True)
    fig_first_icp = mne.viz.plot_alignment(info, trans=coreg.trans, **plot_kwargs)
    fig_first_icp.plotter.add_text("Quick check for the fiducials fitting", position="upper_edge", font_size=14, color="white")
    fig_first_icp.plotter.show()

    coreg.omit_head_shape_points(distance=5.0 / 1000) 

    # Refined fitting with adjusted weights
    # Increase nasion weight if nasion alignment was poor
    nasion_weight = 10.0 if input(CYELLOW + "Was the nasion alignment poor? (y/n): " + CEND).lower() == 'y' else 5.0
    # Adjust LPA and RPA weights based on initial fitting
    lpa_weight = 5.0 if input(CYELLOW + "Was the LPA alignment poor? (y/n): " + CEND).lower() == 'y' else 1.0
    rpa_weight = 5.0 if input(CYELLOW + "Was the RPA alignment poor? (y/n): " + CEND).lower() == 'y' else 1.0

    print("Fitting ICP...")    
    
    coreg.fit_icp(n_iterations=20, nasion_weight=nasion_weight, lpa_weight=lpa_weight, rpa_weight=rpa_weight, verbose=True)

    # Plot after fitting
    fig_final_icp = mne.viz.plot_alignment(info, trans=coreg.trans, **plot_kwargs)
    fig_final_icp.plotter.add_text("Final ICP fitting", position="upper_edge", font_size=14, color="white")
    fig_final_icp.plotter.show()
    mne.viz.set_3d_view(fig_final_icp, **view_kwargs)

    dists = coreg.compute_dig_mri_distances() * 1e3  # in mm
    print( 
        f"Run {run_number} - Distance between HSP and MRI (mean/min/max):\n{np.mean(dists):.2f} mm "
        f"/ {np.min(dists):.2f} mm / {np.max(dists):.2f} mm" 
    )

    # Save the transformation
    trans_fname = output_dir / f'{subject}/{subject}_task-{task}_{run_number}_meg_trans.fif'
    mne.write_trans(str(trans_fname), coreg.trans, overwrite = True)

    print(CGREEN + "Coregistration saved for", subject, run_number,"!" + CEND)


    # Optional: Manual Checking and Correction
    user_input = input(CYELLOW + "Please inspect the coregistration. Press Enter to finish, 'm' for a manual correction, or 'q' to cancel the process: " + CEND)
    if user_input.lower() == 'q':
        print(CRED + "Coregistration process canceled." + CEND)
        return
    elif user_input.lower() == 'm':
        print(CBLUE + "Opening MNE coregistration GUI for manual placement..." + CEND)
        mne.gui.coregistration(inst=str(middle_run_path), subject=subject, subjects_dir=str(subjects_dir), head_high_res=True, trans=trans_fname, interaction='terrain')


    print(CGREEN + "Coregistration completed for", subject, "on the middle run." + CEND)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coregister MEG run for a given subject and session.")
    parser.add_argument('--subject', required=True, help='Subject identifier (e.g., sub-11)')

    #parser.add_argument('--output_dir', required=True, help='Path to the directory where the coregistration results will be saved')

    args = parser.parse_args()

    # Define directories based on the subject and output directory
    base_meg_dir = Path("/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_distraction/")
    subjects_dir = Path("/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_distraction/derivatives/freesurfer/")

    meg_dir = base_meg_dir / args.subject / 'meg'
    #output_dir = Path(args.output_dir) / args.subject

    automated_coreg(args.subject, subjects_dir, meg_dir)