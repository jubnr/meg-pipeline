import mne, re
import numpy as np
from pathlib import Path


def extract_run_numbers(filename):
    """Extract run numbers from a given filename."""
    numbers = re.findall(r'\d+', filename)
    return list(map(int, numbers))

def detect_and_save_runs(participant_dir, output_dir):
    """Detect and save runs from MEG data for all files in participant's directory."""
    participant_dir = Path(participant_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Iterate over all .fif files in the participant's directory
    for fif_file in participant_dir.glob('*.fif'):
        raw = mne.io.read_raw_fif(fif_file, preload=True, allow_maxshield=True)

        # Use the MISC channel to detect breaks
        raw_misc005 = raw.copy().pick_channels(['MISC005'])
        misc005_data = raw_misc005.get_data()

        # Parameters for detecting the runs
        eps = 1e-3
        time_tresh = 5 * raw.info['sfreq']
        gap_left = 10 * raw.info['sfreq']
        gap_right = 3 * raw.info['sfreq']

        # Find indices where MISC005 is below a specific threshold
        indices = np.where(misc005_data[0] < eps)[0]
        grad = np.gradient(indices)
        ind = np.where(grad > time_tresh)[0]

        # Calculate the start and end indices for each run
        indices_runs = [0]
        for i, index in enumerate(ind):
            if i % 2 != 0 and i > 0:
                j = indices[index] - gap_left
            else:
                j = indices[index] + gap_right
            indices_runs.append(j)
        indices_runs.append(len(misc005_data[0])-1)
        indices_runs = np.array(indices_runs).astype(int)


        # Extract run numbers from the file name
        run_numbers = extract_run_numbers(fif_file.stem)

        # Save each run
        for i in range(0, len(indices_runs) - 1, 2):
            start_idx = indices_runs[i]
            end_idx = indices_runs[i+1]
            tmin = start_idx / raw.info['sfreq']
            tmax = end_idx / raw.info['sfreq']

            run_number = run_numbers[i//2]
            output_file = output_dir / f'run_{run_number}.fif'

            # Crop and save the data for the current run
            raw_crop = raw.copy().crop(tmin=tmin, tmax=tmax)
            raw_crop.save(output_file, overwrite=True)
            print(f'Saved: {output_file}')

## Example usage
PARTICIPANT_DIR = '/home/jb278714/Bureau/LPP_project/data/MEG/meg_distraction/raw/ng_240362/241022'
OUTPUT_DIR = '/home/jb278714/Bureau/LPP_project/data/MEG/meg_distraction/raw/ng_240362/cropped_runs'

detect_and_save_runs(PARTICIPANT_DIR, OUTPUT_DIR)
