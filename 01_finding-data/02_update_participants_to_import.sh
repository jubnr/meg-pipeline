#!/bin/bash

# Path to the participants_to_import.tsv file
participants_tsv="participants_to_import.tsv"

# Destination directory for copied files
destination_dir="Destination_folder"

# Create the destination directory if it doesn't exist
mkdir -p "$destination_dir"

# Temporary file to store the updated TSV content
temp_tsv=$(mktemp)

# Add the header to the temporary file
head -n 1 "$participants_tsv" > "$temp_tsv"

# Process each line in the TSV file (skip the header row)
tail -n +2 "$participants_tsv" | while IFS=$'\t' read -r participant_id nip infos_participant session_label acq_date acq_label location to_import; do
    echo "Processing Participant ID: $participant_id, NIP: $nip, Acquisition Date: $acq_date"

    # Check if the acquisition date is valid (e.g., matches YYYY-MM-DD format)
    if [[ ! "$acq_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "Invalid acquisition date: $acq_date. Skipping participant $participant_id."
        continue
    fi

    # Construct the path to the MRI anatomy folder
    mri_dir="/neurospin/acquisition/database/Prisma_fit/${acq_date:0:4}*/${nip}*/*mprage*/"

    # Initialize scan count
    scan_count=0

    # Find and count mprage files
    if [ -d "$(dirname "$mri_dir")" ]; then
        scan_count=$(find "$mri_dir" -type f -name "*mprage*" 2>/dev/null | wc -l)
        echo "Found $scan_count mprage files for NIP: $nip in $mri_dir"
    else
        echo "Directory $mri_dir does not exist or is inaccessible."
    fi

    # Update the to_import column
    to_import="(('$scan_count', 'anat', 'T1w'))"

    # Append the updated line to the temporary file
    echo -e "$participant_id\t$nip\t$infos_participant\t$session_label\t$acq_date\t$acq_label\t$location\t$to_import" >> "$temp_tsv"
done

# Replace the original TSV file with the updated one
mv "$temp_tsv" "$participants_tsv"
echo "participants_to_import.tsv updated successfully!"