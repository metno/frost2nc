# Read frost.met.no data into netcdf files

This contains a command-line utility for reading data from [frost](https://frost.met.no), and converting that data to netcdf format. It has been created to provide an easier way of access to observation data for scientists who prefer using the netcdf format over json. Non-scientists should use the frost api directly instead of going through his program.


## Installation

This has been tested on ubuntu xenial and bionic, and runs using python3. One of our pip requirements need access to the debian package `libudunits2-dev`. Install that one before you do a normal install, using `sudo pip3 install -r requirements.txt && sudo pip3 install .`

After having installed, you should have a frost executable in your path. Run `frost --help` for usage instructions.

#### Special considerations

Installation of requirements currently fail unless you also have said `pip3 install numpy==1.15.4` before you start installing `requirements.txt`.

### Continous updates

Keeping an updated set of netcdf files is partly provided by the `frost-extract-all` script, and the provided systemd scripts. Installation of this is not automated, but you can install like this:

```bash
$ export FROST_KEY=<my key from https://frost.met.no>
$ sudo cp frost-extract-all /usr/local/bin
$ sudo cp systemd/frost-extract-all.* /etc/systemd/system/
$ sudo mkdir /etc/systemd/system/frost-extract-all.service.d/
$ printf "[Service]\nEnvironment=FROST_KEY=$FROST_KEY\n" | sudo tee /etc/systemd/system/frost-extract-all.service.d/custom.conf
$ sudo adduser obs2nc
$ sudo -u obs2nc mkdir /home/obs2nc/json_data
$ sudo systemctl daemon-reload
$ sudo systemctl start frost-extract-all.timer
```

This will run an hourly job, creating and maintaining a list of all data for a set of stations for the last three months.
