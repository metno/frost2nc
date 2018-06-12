from jinja2 import Environment, PackageLoader, select_autoescape
import netCDF4
from datetime import datetime, timezone
import os
import sys

def render_metadata(output_folder, nc_file, announced_location):
    '''Generate a metadata document from the given netcdf file'''
    metadata = get_metadata(nc_file)
    render(output_folder, announced_location, **metadata)

def get_metadata(nc_file):
    '''Extract metadata from the given netcdf file'''
    ret = {}
    dataset = netCDF4.Dataset(nc_file, 'r', format='NETCDF4')

    ret['station_name'] = dataset.station_name
    ret['wigos'] = dataset.wigos

    ret['latitude'] = dataset.variables['latitude'][0]
    ret['longitude'] = dataset.variables['longitude'][0]
    times = dataset.variables['time']
    if times:
        ret['start_date'] = datetime.fromtimestamp(times[0], tz=timezone.utc)
    else:
        ret['start_date'] = ''

    return ret



def render(output_folder, announced_location, station_name, wigos, start_date, latitude, longitude):
    '''Generate metadata template'''
    env = Environment(
        loader=PackageLoader('frost_extract', 'templates'),
        autoescape=select_autoescape(['xml'])
    )
    template = env.get_template('mmd.xml')

    with open('%s/%s.xml' % (output_folder, wigos), 'w', encoding='utf-8') as f:
        metadata = template.render(
            announced_location=announced_location, 
            station_name=station_name, 
            wigos=wigos, 
            start_date=start_date, 
            latitude=latitude, 
            longitude=longitude)
        f.write(metadata)

if __name__ == '__main__':
    for nc_file in sys.argv[1:]:
        print(nc_file)
        output_folder = os.path.dirname(nc_file) or '.'
        print('Render to ' + output_folder)
        render_metadata(output_folder, nc_file)
