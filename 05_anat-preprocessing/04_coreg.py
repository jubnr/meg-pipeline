import mne 

subject = 'sub-58'
subjects_dir = '/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/freesurfer/'
mne.gui.coregistration(
inst= "/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/LPP_MEG_auditory/sub-58/ses-01/meg/sub-58_ses-01_task-listen_run-01_meg.fif",
		    subject=subject,
		  subjects_dir=subjects_dir,  # contains a sub-folder for subject
		  head_high_res=True,
		  trans='/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/freesurfer/sub-58/coreg/coreg_sub-58_ses-01_task-listen_run-01_meg_trans.fif',
	    interaction='terrain')