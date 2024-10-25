#!/bin/bash

# si n° run impair = 'task-listen' 
for file in sub-*_task-distraction_run-*_*.{tsv,fif,json}; do
    # Extraire le numéro de run et vérifier s'il est impair
    if (( $(echo "$file" | grep -oP '(?<=run-)\d{2}') % 2 != 0 )); then
        # Renommer si le run est impair
        mv "$file" "${file/task-distraction/task-listen}"
        echo "Renommé : $file -> ${file/task-distraction/task-listen}"
    else
        echo "Pas de changement pour : $file"
    fi
done
