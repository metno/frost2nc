import click
import dateutil.parser
from datetime import datetime, timezone
import json
import logging
import netCDF4
import os
import sys
import cf_units
import yaml
import pkgutil

class NetcdfWriter(object):
    def __init__(self):
        self._observations = {}
        self._unit_conversions = {}

    def get_obs_name(self, obs):
        obs_name = obs['elementId']
        if 'level' in obs:
            lvl = obs['level']
            obs_name += '_%d%s' % (lvl['value'], lvl['unit'])
        return obs_name

    def select_obs(self, timestep):
        ret = []
        params = {}
        for obs in timestep['observations']:
            instances = params.setdefault(self.get_obs_name(obs), [])
            instances.append(obs)
        found_all = True
        for name, observations in params.items():
            if len(observations) > 1:
                selected = self._select_obs(observations)
                if selected:
                    ret.append(selected)
                else:
                    found_all = False
            else:
                ret.append(observations[0])
        if not found_all:
           logging.warning('Failed to find suitable candidates for at least some ' + name)

        return ret

    def _select_obs(self, candidates):
        selected = [ o for o in candidates if o.get('timeOffset', 'PT00H') == 'PT00H' ]
        if not selected:
            return None
        elif len(selected) == 1:
            return selected[0]
        return self._get_best_time_resolution(selected)

    def _get_best_time_resolution(self, candidates):
        selected = [ o for o in candidates if o.get('timeResolution', 'PT1H') == 'PT1H' ]
        if len(selected) > 1:
            return None
        return selected[0]

    def add_observations(self, obs_files):
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        for f in obs_files:
            with open(f) as j:
                data = json.loads(j.read()) or []
            for timestep in data:
                reference_time = dateutil.parser.parse(timestep['referenceTime'])
                seconds = (reference_time - epoch).total_seconds()

                ts = self._observations.setdefault(seconds, {})

                for obs in self.select_obs(timestep):
                    data_key = self.get_obs_name(obs)

                    if data_key in ts:
                        logging.warning(data_key + ' already exists in ' + timestep['referenceTime'])
                    ts[data_key] = obs

    def write(self, file_name, sources_file, elements_file, append=False):
        with open(sources_file) as f:
            source = json.load(f)

        if not file_name:
            if 'wigosId' not in source:
                raise RuntimeError('Unable to generate output file name')
            file_name = source['wigosId'] + '.nc'

        logging.info('Generating ' + file_name)
    
        mode = 'w'
        if append:
            mode = 'a'
        nc = netCDF4.Dataset(file_name, mode, format='NETCDF4')

        logging.debug('Opened file')

        elements = {}
        with open(elements_file) as f:
            for e in json.load(f):
                elements[e['id']] = e

        if not append:
            self._add_time_variable(nc)
            self._add_location(nc, source)
            logging.debug('added time and location')


        time_indexes = {}
        times = nc.variables['time']
        idx = 0
        for t in times:
            # print(float(t), dir(t))
            time_indexes[float(t)] = idx
            idx += 1

        new_times = list(self._observations.keys())
        new_times.sort()


        for t in new_times:
            if t not in time_indexes:
                times[idx] = t
                time_indexes[t] = idx
                idx += 1

        logging.debug('times updated')

        for t in new_times:
            params = self._observations[t]
            for p, value in params.items():
                element = elements.get(value['elementId'], {})
                var = self._get_variable(nc, p, element)
                convert = self._get_conversion(nc, p, element)
                idx = time_indexes[t]
                var[idx] = convert(value['value'])
        logging.debug('added new data')

        self._add_metadata(nc, source)
        logging.debug('added metadata')

        nc.close()

    def _get_variable(self, nc, name, element_information):
        if name not in nc.variables:
            logging.debug('Adding variable: ' + name)
            var = nc.createVariable(name, 'f4', ('time',), zlib=True)
            var.long_name = element_information.get('name', name)
            var.coverage_content_type = 'coordinate'
            if 'cfConvention' in element_information:
                cf = element_information['cfConvention']
                var.standard_name = cf.get('standardName', name)
                var.units = cf.get('unit', '1')
                if 'cellMethod' in cf:
                    var.cell_methods = cf['cellMethod']
            else:
                var.standard_name = name
                var.units = element_information.get('unit', '1')
            return var
        else:
            return nc.variables[name]

    def _get_conversion(self, nc, variable_name, element_information):
        if not variable_name in self._unit_conversions:
            from_unit = element_information.get('unit', '1')
            to_unit = from_unit
            if 'cfConvention' in element_information:
                cf = element_information['cfConvention']
                to_unit = cf.get('unit', '1')
            if from_unit == to_unit:
                logging.debug('Simple conversion for variable ' + variable_name)
                self._unit_conversions[variable_name] = lambda x: x
            else:
                logging.debug('Converting %s -> %s for variable %s' % (from_unit, to_unit, variable_name))
                self._unit_conversions[variable_name] = get_conversion_function(from_unit, to_unit)
        return self._unit_conversions[variable_name]

    def _add_time_variable(self, nc):
        nc.createDimension('time', None)
        time = nc.createVariable('time', 'double', ('time',), zlib=True)
        time.standard_name = 'time'
        time.long_name     = 'Time of measurement'
        time.calendar      = 'standard'
        time.units         = 'seconds since 1970-01-01 00:00:00 UTC'
        time.axis          = 'T'
        return time
    
    def _add_metadata(self, nc, source):
        source['now'] = datetime.now(tz=timezone.utc).isoformat()
        longitude, latitude = tuple(source['geometry']['coordinates'])
        source['longitude'] = longitude
        source['latitude'] = latitude
        source['program_args'] = ' '.join(sys.argv)
        if 'wigosId' not in source:
            source['wigosId'] = 'unknown'
        times = nc.variables['time']
        source['time_start'] = datetime.fromtimestamp(times[0]).isoformat()
        source['time_end'] = datetime.fromtimestamp(times[-1]).isoformat()

        config = pkgutil.get_data('frost_extract', 'templates/global_attributes.yaml')
        for entry in yaml.load(config):
            for key, raw in entry.items():
                value = raw % source
                setattr(nc, key, value)

    def _add_location(self, nc, source):
        longitude, latitude = source['geometry']['coordinates']
        
        lat = nc.createVariable('latitude', 'float', zlib=True)
        lat.standard_name = 'latitude'
        lat.long_name     = 'latitude'
        lat.units         = 'degree_north'
        lat.assignValue(latitude)
          
        lon = nc.createVariable('longitude', 'float', zlib=True)
        lon.standard_name = 'longitude'
        lon.long_name     = 'longitude'
        lon.units         = 'degree_east'
        lon.assignValue(longitude)

def get_conversion_function(unit_from, unit_to):
    f = cf_units.Unit(unit_from)
    t = cf_units.Unit(unit_to)
    if not f.is_convertible(t):
        logging.warning('Units are not convertible: %s -> %s' % (unit_from, unit_to))
        return lambda x: x
    return lambda x: f.convert(x, t)
