# Read frost.met.no data into netcdf files

## Installation for playing

```bash
$ virtualenv -ppython3 venv
$ . venv/bin/activate
$ python setup.py 
$ pip install --editable .
```

...and then the next times you want to run:

```bash
$ . venv/bin/activate
```

## Initial run

```bash
$ export FROST_KEY=<my frost key>
$ export DATA_DIR=data/
$ export NC_DIR=data/nc
$ export MMD_DIR=data/mmd
$ export OPENDAP_PATH=https://thredds.met.no/observations
$ export STATIONS="SN99710  SN99720  SN99735  SN99740  SN99752  SN99754  SN99760  SN99765  SN99790  SN99840  SN99880  SN99910  SN99927  SN99935  SN99938"
$ mkdir -p $DATA_DIR
$ frost download elements > $DATA_DIR/elements.json
$ for station in $STATIONS; do mkdir -p $DATA_DIR/$station; done
$ for station in $STATIONS; do frost download source -s$station > $DATA_DIR/$station/source.json; done
$ for station in $STATIONS; do frost download observations -o$DATA_DIR -s$station; done

$ mkdir -p $NC_DIR $MMD_DIR
$ for station in $STATIONS; do frost write netcdf -o$NC_DIR/$station.nc -s$DATA_DIR/$station/source.json -edata/elements.json  $DATA_DIR/$station/*/*.json; done
$ for station in $STATIONS; do frost write mmd -o$MMD_DIR $NC_DIR/$station.nc -l$OPENDAP_PATH/$station.nc; done
```

## Updates

```bash
$ export FROST_KEY=<my frost key>
$ export DATA_DIR=data/
$ export NC_DIR=data/nc
$ export STATIONS="SN99710  SN99720  SN99735  SN99740  SN99752  SN99754  SN99760  SN99765  SN99790  SN99840  SN99880  SN99910  SN99927  SN99935  SN99938"

$ for station in $STATIONS; do 
    frost download observations -o$DATA_DIR -s$station --duration=3 | xargs \
        frost write netcdf --append -o$NC_DIR/$station.nc -s$DATA_DIR/$station/source.json -edata/elements.json
done
```

