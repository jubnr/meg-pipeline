#! /usr/bin/env python

import os

# To set the number of threads
num_threads = '1'
os.environ["OMP_NUM_THREADS"] = num_threads
os.environ["OPENBLAS_NUM_THREADS"] = num_threads
os.environ["MKL_NUM_THREADS"] = num_threads

import nibabel, mne, mne_bids, re, argparse, gc
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from wordfreq import zipf_frequency
import contextlib, dataclasses, functools, hashlib, itertools, warnings
import typing as tp
from mne.preprocessing import find_bad_channels_maxwell


## ----- DEFINE PATHS ----- ##
BASE_PATH = Path('/neurospin/unicog/protocols/IRMf/LePetitPrince_Pallier_2018/MEG/workspace-LPP/data/MEG/LPP/')
subjects_dir = BASE_PATH / 'LPP_MEG_auditory/derivatives/freesurfer/'
metadata = '/home_local/Bonnaire/metadata/' 
cross_talk_file = BASE_PATH / 'calibration_MEG/old_MEG/ct_sparse_nspn.fif'
calibration_file = BASE_PATH / 'calibration_MEG/old_MEG/sss_cal_nspn.dat'
## ----------------------- ##

class NoApproximateMatch(ValueError):
    """Error raised when the function could not fully match the two list
    The error has a 'match' attribute holding the matches so far, for debugging
    """

    def __init__(self, msg: str, matches: tp.Any) -> None:
        super().__init__(msg)
        self.matches = matches

@dataclasses.dataclass
class Tolerance:
    """Convenience tool for check if a value is  within tolerance"""

    abs_tol: float
    rel_tol: float

    def __call__(self, value1: float, value2: float) -> bool:
        diff = abs(value1 - value2)
        tol = max(self.abs_tol, self.rel_tol * min(abs(value1), abs(value2)))
        return diff <= tol

@dataclasses.dataclass
class Sequence:
    """Handle for current information on the sequence matching"""

    sequence: tp.Sequence[float]  # the sequence to match
    current: int  # the current index for next match look-up
    matches: tp.List[int]  # the matches so far in the sequence

    def valid_index(self, shift: int = 0) -> bool:
        return self.current + shift < len(self.sequence)

    def diff(self, shift: int = 0) -> float:
        return self.sequence[self.current + shift] - self.last_value

    @property
    def last_value(self) -> float:
        return self.sequence[self.matches[-1]]

    def diff_to(self, ind: int) -> np.ndarray:
        r = self.matches[-1]
        sub = self.sequence[r : r + ind] if ind > 0 else self.sequence[r + ind : r]
        return np.array(sub) - self.last_value

def approx_match_samples(
    s1: tp.Sequence[float],
    s2: tp.Sequence[float],
    abs_tol: float,
    rel_tol: float = 0.003,
    max_missing: int = 3,
    first_match: tp.Tuple[int, int] | None = None,
) -> tp.Tuple[np.ndarray, np.ndarray]:
    """Approximate sample sequence matching
    Eg:
    seq0 = [1100, 2300, 3600]
    seq1 = [0, 1110, 3620, 6500]
    will match on 1100-1110 with tolerance 10,
    and then on 3600-3620 (as the diffs match with tolerance 10)

    Returns
    -------
    tuple of indices which match on the first list and the second list
    """
    if first_match is None:
        # we need to figure out the first match:
        # let's try on for several initial matches,
        # and pick the one that matches the most
        success: tp.Tuple[np.ndarray, np.ndarray] | None = None
        error: tp.Any = None
        for offsets in itertools.product(range(max_missing + 1), repeat=2):
            try:
                out = approx_match_samples(
                    s1, s2, abs_tol=abs_tol, rel_tol=rel_tol, max_missing=max_missing, first_match=offsets  # type: ignore
                )
                if success is None or len(out[0]) > len(success[0]):  # type: ignore
                    success = out
            except NoApproximateMatch as e:
                if error is None or error.matches[0][-1] < e.matches[0][-1]:
                    error = e
        if success is not None:
            return success
        raise error
    tolerance = Tolerance(abs_tol=abs_tol, rel_tol=rel_tol)
    seqs = (
        Sequence(s1, first_match[0] + 1, [first_match[0]]),
        Sequence(s2, first_match[1] + 1, [first_match[1]]),
    )
    while all(s.valid_index() for s in seqs):
        # if we match within the tolerance limit, then move on
        # otherwise move the pointer for the less advanced sequence
        if tolerance(seqs[0].diff(), seqs[1].diff()):
            for k, s in enumerate(seqs):
                s.matches.append(s.current)
                s.current += 1
        else:
            # move one step
            seqs[1 if seqs[1].diff() < seqs[0].diff() else 0].current += 1
        # allow for 1 extra (absolute) step if getting closer
        for k, seq in enumerate(seqs):
            other = seqs[(k + 1) % 2]
            if seq.valid_index(shift=1) and other.valid_index():
                # need to check 2 tolerance so that we can match farther
                # if it is closer
                if abs(seq.diff(1) - seq.diff()) <= 2 * abs_tol:
                    if abs(seq.diff(1) - other.diff()) < abs(seq.diff() - other.diff()):
                        seq.current += 1
        # if we are over the limit for matching, then abort
        if any(m.current - m.matches[-1] > max_missing + 1 for m in seqs):
            msg = f"Failed to match after indices {[s.matches[-1] for s in seqs]} "
            msg += f"(values {[s.last_value for s in seqs]}, {first_match=})\n"
            msg += f"(follows:\n {seqs[0].diff_to(10)}\n {seqs[1].diff_to(10)}"
            msg += f"(before:\n {seqs[0].diff_to(-10)}\n {seqs[1].diff_to(-10)}"
            out = tuple(np.array(s.matches) for s in seqs)  # type: ignore
            raise NoApproximateMatch(msg, matches=out)
    return tuple(np.array(s.matches) for s in seqs)  # type: ignore

def get_wordfreq(word:str):
    return zipf_frequency(word, 'fr')

TOL_MISSING_DICT = {
    (9, 6): (30, 5),  # Works
    (10, 6): (30, 5),  # Works
    (12, 5): (30, 5),  # Works
    (13, 3): (5, 30),  # Yes
    (13, 7): (5, 30),  # Yes
    (14, 9): (30, 5),  # Yes
    (21, 6): (200, 5),  # Yes
    (21, 8): (30, 5),  # No this is fked up: decided to toss sub21 run 8...
    (22, 4): (30, 5),  # Yes
    (33, 2): (40, 40),  # Yes (big shift so only 72% matched..)
    (39, 5): (45, 5),  # Yes
    (40, 2): (80, 5),  # Yes
    (41, 1): (40, 5),  # Yes
    (43, 4): (200, 5),  # Yes
    (43, 5): (110, 5),  # Yes
    (44, 9): (30, 5),
    (24, 2): (10, 20),
}


def get_evo_diff(subject):

    evo_diff_all = []

    for i in range(1, 10):        
        raw_fname = BASE_PATH / f'LPP_MEG_auditory/{subject}/ses-01/meg/{subject}_ses-01_task-listen_run-0{i}_meg.fif'

        raw = mne.io.read_raw_fif(raw_fname, allow_maxshield=True)
        raw_ref = mne.io.read_raw_fif(BASE_PATH / f'LPP_MEG_auditory/{subject}/ses-01/meg/{subject}_ses-01_task-listen_run-05_meg.fif', allow_maxshield=True)

        raw.load_data().filter(0.5, 20)

        # ------------- Finding bad channels automatically ------------- #
        
        raw.info["bads"] = []
        auto_noisy_chs, auto_flat_chs = find_bad_channels_maxwell(raw, 
            cross_talk=cross_talk_file,
            calibration=calibration_file) # duration = 20, min_count = 3
        bads = raw.info["bads"] + auto_noisy_chs + auto_flat_chs
        raw.info["bads"] = bads
        
        # ------------- Applying Maxwell filter ------------- #

        destination = raw_ref.info["dev_head_t"]

        raw_sss = mne.preprocessing.maxwell_filter(raw,cross_talk=cross_talk_file,
                                                   calibration=calibration_file,
                                                   destination=destination)

        del raw_ref
        gc.collect()
        
        os.makedirs(BASE_PATH / f'LPP_MEG_auditory/derivatives/preprocessed_data/{subject}', exist_ok=True)
        raw_sss.save(BASE_PATH / f'LPP_MEG_auditory/derivatives/preprocessed_data/{subject}/{subject}_ses-01_task-listen_run-0{i}_meg_raw_sss.fif', overwrite=True)

        # ------------- Loading metadata with onsets, words and duration ------------- #

        words = pd.read_csv(metadata + f"sub-1_ses-01_task-listen_run-0{i}_events.tsv", sep='\t')
        words["word"] = words["trial_type"].apply(lambda x: eval(x)["word"] if type(eval(x)) == dict else np.nan)

        # ------------- Getting triggers with the right timing ------------- #

        # Get the word triggers from STI008, as a step so we can get the offset
        word_triggers = mne.find_stim_steps(raw, stim_channel="STI008")
        # Offsets of the step function: allows us to match
        word_triggers = word_triggers[word_triggers[:, 2] == 0]
        run = i
        subject_ = subject.split('-')[1]
        # New match
        abs_tol, max_missing = TOL_MISSING_DICT.get(
            (int(subject_), int(run)), (10, 5)
        )
        i, j = approx_match_samples(
            (words.onset * 1000).tolist(),
            word_triggers[:, 0],
            abs_tol=abs_tol,
            max_missing=max_missing,
        )
        print(f"Found {len(i)/len(words)} of the words in the triggers")

        words = words.iloc[i, :]

        words.loc[:, "unaligned_start"] = words.loc[:, "onset"]
        words.loc[words.index, "onset"] = word_triggers[j, 0] / raw.info["sfreq"]
    
        # ------------- Epoching based on frequent/rare words ------------- #

        n_words = len(words)
        events = np.ones((n_words, 3), dtype=int)
        events[:,0] = words.onset * raw.info['sfreq']
        events[:,2] = np.arange(n_words)

        words['freq'] = words.word.apply(get_wordfreq) 
        words['is_rare'] = words.freq < np.median(words.freq)

        epochs_run = mne.Epochs(raw_sss, events, 
                            tmin = -0.500,
                            tmax = 0.800,
                            baseline = (-0.500,0),
                            metadata = words)
            
        del raw
        gc.collect()
        
        epochs_run.load_data()
        
        evo_rare = epochs_run['is_rare'].average(method='median')
        evo_freq = epochs_run['~is_rare'].average(method='median')

        evo_diff = evo_rare.copy()
        evo_diff.data -= evo_freq.data

        evo_diff_all.append(evo_diff)

    evo_diff_average = mne.grand_average(evo_diff_all)

    return evo_diff_average

for subject_folder in subjects_dir.iterdir():
    subject = subject_folder.name
    if not subject.startswith('sub-'):
        continue

    preprocessed_dir = BASE_PATH / 'LPP_MEG_auditory/derivatives/preprocessed_data'

    if (preprocessed_dir / subject).exists():
        continue

    evo_diff_average = get_evo_diff(subject)

    os.makedirs(BASE_PATH / f'LPP_MEG_auditory/derivatives/preprocessed_data/{subject}', exist_ok=True)
    evo_diff_average.save(BASE_PATH / f'LPP_MEG_auditory/derivatives/preprocessed_data/{subject}/{subject}_evo_diff-ave.fif', overwrite=True)

### ###
