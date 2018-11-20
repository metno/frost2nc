#!/bin/bash

set -euo pipefail

STATIONS="SN99710 SN99720  SN99735  SN99740  SN99752  SN99754  SN99760  SN99765  SN99790  SN99840  SN99880  SN99910  SN99927  SN99935  SN99938"

export FROST_SERVER=frost.met.no

JSON_OUTPUT_DIR=$HOME/json_data
NC_OUTPUT_DIR=/data


if [ -z "$FROST_KEY"]; then 
    echo "Missing FROST_KEY"
    exit 1
fi

echo download elements list

frost download elements > "$JSON_OUTPUT_DIR/elements.json"

echo start loop

for station in $STATIONS; do
    echo "$(date) Extract station $station"
    frost download source -s$station > "$JSON_OUTPUT_DIR/$station.json"
    new_files=$(frost download observations --output="$JSON_OUTPUT_DIR" -s"$station" --duration 3)
    for f in $new_files; do

        month=$(basename "$f" .json)
        year=$(basename $(dirname $f))

        output_dir="$NC_OUTPUT_DIR/$station/$year"
        mkdir -p "$output_dir"
        frost write netcdf \
            -o/tmp/data.nc \
            -s"$JSON_OUTPUT_DIR/$station.json" \
            -e"$JSON_OUTPUT_DIR/elements.json" \
            "$JSON_OUTPUT_DIR/$station/$year/$month.json"
        mv /tmp/data.nc "$output_dir/$month.nc"
    done
    echo "$(date) done"
done

