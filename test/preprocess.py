#!/usr/bin/env python

import os, yaml
from pathlib import Path
import mne
import numpy as np
import pandas as pd
import typing as tp
import dataclasses, itertools
from wordfreq import zipf_frequency
from mne.preprocessing import find_bad_channels_maxwell
import gc

# Load configuration file
with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

# Set the number of threads
NUM_THREADS = str(config["num_threads"])
os.environ["OMP_NUM_THREADS"] = NUM_THREADS
os.environ["OPENBLAS_NUM_THREADS"] = NUM_THREADS
os.environ["MKL_NUM_THREADS"] = NUM_THREADS

# Load general parameters of the study
STUDY = config["study"]
TASK = config["task"]
SESSION = config["session"]
MEG_DIR = config["meg_dir"]

# Define paths from config
BASE_PATH = Path(config["base_path"])
SUBJECTS_DIR = BASE_PATH / config["subjects_dir"]
METADATA = config["metadata"]
CROSS_TALK_FILE = BASE_PATH / config["cross_talk_file"]
CALIBRATION_FILE = BASE_PATH / config["calibration_file"]

# Preprocessing parameters
MIDDLE_RUN = config["middle_run"]
FILTER_LOW = config["filter_low"]
FILTER_HIGH = config["filter_high"]
EPOCH_TMIN = config["epoch_tmin"]
EPOCH_TMAX = config["epoch_tmax"]
BASELINE = tuple(config["baseline"])
RUNS = config["runs"]

# Optional: List of specific subjects to process
SPECIFIC_SUBJECTS = config.get("subjects", None)  # Default to an empty list if "subjects" is missing
if isinstance(SPECIFIC_SUBJECTS, str):  # Handle case where "subjects" is a single string
    SPECIFIC_SUBJECTS = [SPECIFIC_SUBJECTS]

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
    """
    Approximate sample sequence matching
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

# Matching tolerances
TOL_MISSING_DICT = {tuple(k): tuple(v) for k, v in config["tolerances"].items()}

def preprocessing(SUBJECT):
    evo_diff_all = []

    for i in RUNS:
        
        raw_fname = SUBJECTS_DIR / f"{SUBJECT}/{MEG_DIR}/{SUBJECT}_{SESSION}task-{TASK}_run-0{i}_meg.fif"
        raw = mne.io.read_raw_fif(raw_fname, allow_maxshield=True)
        raw_ref = mne.io.read_raw_fif(SUBJECTS_DIR / f"{SUBJECT}/{MEG_DIR}/{SUBJECT}_{SESSION}task-{TASK}_{MIDDLE_RUN}_meg.fif", allow_maxshield=True)

        raw.load_data().filter(FILTER_LOW, FILTER_HIGH)

        # ------------- Finding bad channels automatically ------------- #
        raw.info["bads"] = []
        auto_noisy_chs, auto_flat_chs = find_bad_channels_maxwell(
            raw, cross_talk=CROSS_TALK_FILE, calibration=CALIBRATION_FILE)
        bads = raw.info["bads"] + auto_noisy_chs + auto_flat_chs
        raw.info["bads"] = bads

        # ------------- Applying Maxwell filter ------------- #
        destination = raw_ref.info["dev_head_t"]
        raw_sss = mne.preprocessing.maxwell_filter(
            raw, cross_talk=CROSS_TALK_FILE, calibration=CALIBRATION_FILE, destination=destination
        )

        del raw_ref
        gc.collect()

        os.makedirs(SUBJECTS_DIR / f"/derivatives/preprocessed_data/{SUBJECT}", exist_ok=True)
        raw_sss.save(SUBJECTS_DIR / f"/derivatives/preprocessed_data/{SUBJECT}/{SUBJECT}_{SESSION}task-{TASK}_run-0{i}_meg_raw_sss.fif", overwrite=True)

        # ------------- Loading metadata with onsets, words, and duration ------------- #
        words = pd.read_csv(METADATA + f"{SUBJECT}_{SESSION}task-{TASK}_run-0{i}_events.tsv", sep="\t")
        words["word"] = words["trial_type"].apply(lambda x: eval(x)["word"] if type(eval(x)) == dict else np.nan)

        # ------------- Getting triggers with the right timing ------------- #
        word_triggers = mne.find_stim_steps(raw, stim_channel="STI008")
        word_triggers = word_triggers[word_triggers[:, 2] == 0]
        run = i
        SUBJECT_ = {SUBJECT}.split("-")[1]
        abs_tol, max_missing = TOL_MISSING_DICT.get((int(SUBJECT_), int(run)), (10, 5))
        i, j = approx_match_samples(
            (words.onset * 1000).tolist(), word_triggers[:, 0], abs_tol=abs_tol, max_missing=max_missing
        )
        print(f"Found {len(i)/len(words)} of the words in the triggers")

        words = words.iloc[i, :]
        words.loc[:, "unaligned_start"] = words.loc[:, "onset"]
        words.loc[words.index, "onset"] = word_triggers[j, 0] / raw.info["sfreq"]

        # ------------- Epoching based on frequent/rare words ------------- #
        n_words = len(words)
        events = np.ones((n_words, 3), dtype=int)
        events[:, 0] = words.onset * raw.info["sfreq"]
        events[:, 2] = np.arange(n_words)

        words["freq"] = words.word.apply(get_wordfreq)
        words["is_rare"] = words.freq < np.median(words.freq)

        epochs_run = mne.Epochs(
            raw_sss, events, tmin=EPOCH_TMIN, tmax=EPOCH_TMAX, baseline=BASELINE, metadata=words)

        del raw
        gc.collect()

        epochs_run.load_data()

        evo_rare = epochs_run["is_rare"].average(method="median")
        evo_freq = epochs_run["~is_rare"].average(method="median")

        evo_diff = evo_rare.copy()
        evo_diff.data -= evo_freq.data

        evo_diff_all.append(evo_diff)

    evo_diff_average = mne.grand_average(evo_diff_all)
    return evo_diff_average

# Process specific subjects or all subjects
if SPECIFIC_SUBJECTS:
    print("Processing specific subjects:", SPECIFIC_SUBJECTS)  # Debugging statement
    for SUBJECT in SPECIFIC_SUBJECTS:
        SUBJECT = SUBJECT.strip()  # Remove trailing spaces
        print("Current SUBJECT:", SUBJECT)  # Debugging statement
        preprocessed_dir = SUBJECTS_DIR / "derivatives/preprocessed_data"
        if (preprocessed_dir / SUBJECT).exists():
            print(f"Skipping {SUBJECT} (already processed)")
            continue

        evo_diff_average = preprocessing(SUBJECT)
        os.makedirs(SUBJECTS_DIR / f"derivatives/preprocessed_data/{SUBJECT}", exist_ok=True)
        evo_diff_average.save(SUBJECTS_DIR / f"derivatives/preprocessed_data/{SUBJECT}/{SUBJECT}_evo_diff-ave.fif", overwrite=True)
else:
    print("Processing all subjects in the subjects directory.")  # Debugging statement
    for subject_folder in SUBJECTS_DIR.iterdir():
        SUBJECT = subject_folder.name
        if not SUBJECT.startswith("sub-"):
            continue

        print("Current SUBJECT:", SUBJECT)  # Debugging statement
        preprocessed_dir = SUBJECTS_DIR / "derivatives/preprocessed_data"
        if (preprocessed_dir / SUBJECT).exists():
            print(f"Skipping {SUBJECT} (already processed)")
            continue

        evo_diff_average = preprocessing(SUBJECT)
        os.makedirs(SUBJECTS_DIR / f"derivatives/preprocessed_data/{SUBJECT}", exist_ok=True)
        evo_diff_average.save(SUBJECTS_DIR / f"derivatives/preprocessed_data/{SUBJECT}/{SUBJECT}_evo_diff-ave.fif", overwrite=True)