import pandas as pd

# Read the passation.csv file
passation_df = pd.read_csv("passation.csv")

# Create the participants_to_import.tsv DataFrame
participants_df = pd.DataFrame({
    "participant_id": passation_df["Subject"],
    "NIP": passation_df["NIP"],
    "infos_participant": "{}",  # Default empty dictionary
    "session_label": "{}",  # Empty by default
    "acq_date": passation_df["acq_date"],  
    "acq_label": "{}",  # Empty by default
    "location": "prisma",  # Default location
    "to_import": ""  # Empty by default (will be updated later)
})

# Save the DataFrame to a TSV file
participants_df.to_csv("participants_to_import.tsv", sep="\t", index=False)
print("participants_to_import.tsv created successfully!")