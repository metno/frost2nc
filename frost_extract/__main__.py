import click
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import frost_extract.metadata
import frost_extract.read_frost
from frost_extract.write_netcdf import NetcdfWriter
import json
import logging
import os
import sys


@click.group()
@click.option('--loglevel', type=click.Choice(['debug', 'info', 'warn', 'error', 'critical']), default='warn')
def cli(loglevel):
    '''Process observations from a frost server, possibly generating netcdf files and such from them.'''
    logging.getLogger().setLevel(loglevel.upper())


@click.group()
@click.pass_context
@click.option('--server', default='frost.met.no', envvar='FROST_SERVER', help='name of frost server to connect to')
@click.option('--key', prompt=True, hide_input=True, envvar='FROST_KEY', help='API key for frost')
def download(ctx, server, key):
    '''Download data from a frost server. Note that you may use environment variables FROST_SERVER and FROST_KEY for parameters here.'''
    ctx.obj = {}
    ctx.obj['frost'] = frost_extract.read_frost.FrostApi('https://' + server, key)

default_elements = [
    'air_temperature', 
    'air_pressure_at_sea_level',
    'air_pressure_at_sea_level_qnh',
    'relative_humidity',
    'surface_air_pressure',
    'wind_from_direction',
    'wind_speed',
    'mean(surface_downwelling_longwave_flux_in_air PT1H)',
    'mean(surface_downwelling_shortwave_flux_in_air PT1H)'
]
@download.command()
@click.pass_context
@click.option('--output', '-o', 'output_folder', default='.', type=click.Path(writable=True), help='Name of base folder to write files into.')
@click.option('--element', '-e', 'elements', multiple=True, default=default_elements, help='Parameters to get from frost. Specify multiple times to get several parameters')
@click.option('--station', '-s', 'stations', multiple=True, help='Stations to fetch data for. Use frost notation, such as SN18700. May be specified multiple times')
@click.option('--until', '-t', help='Latest year and month to get data for. Use format YYYY-MM. Will be current month if not specified')
@click.option('--duration', type=int, help='Duration back in time to get data for, in months')
def observations(ctx, output_folder, elements, stations, until, duration):
    '''Store observations into a set of files. Will print a list of all written files to stdout.'''
    time_range = _get_time_range(until, duration)
    frost = ctx.obj['frost']
    files = []
    for s in stations:
        logging.info('Reading station ' + s)
        files += frost_extract.read_frost.save(frost, s, elements, time_range, output_folder)
    print(' '.join(files))


def _get_time_range(until, duration):
    if until:
        datetime.strptime(until, '%Y-%m')
    else:
        until = date.today()
        until = date(until.year, until.month, 1) + relativedelta(months=1)
    if not duration:
        duration = 12*150
    return (until - relativedelta(months=duration), until)


@download.command()
@click.pass_context
def elements(ctx):
    '''Print information about all available frost elements to stdout.'''
    frost = ctx.obj['frost']
    print(json.dumps(frost.get_elements()))


@download.command()
@click.pass_context
@click.option('--station', '-s', 'station', help='Station to fetch data for. Use frost notation, such as SN18700')
def source(ctx, station):
    '''Print information about the given source (station) to stdout.'''
    frost = ctx.obj['frost']
    print(json.dumps(frost.get_source(station)))


@click.group()
def write():
    '''Process data downloaded via frost download, and generate various outputs.'''
    pass

@write.command()
@click.option('--output', '-o', 'output_file', type=click.Path(writable=True), help='Name of netcdf file to write.')
@click.option('--source', '-s', type=click.Path(), help='Name of file to read frost sources information from')
@click.option('--elements', '-e', type=click.Path(), help='Name of file to read frost elements information from')
@click.option('--append', '-a', is_flag=True, help='Append to an existing file instead of creating a new one')
@click.argument('input_files', nargs=-1)
def netcdf(output_file, source, elements, append, input_files):
    '''Write or append to a netcdf file'''
    w = NetcdfWriter()
    w.add_observations(input_files)
    w.write(output_file, source, elements, append)

@write.command()
@click.option('--output', '-o', 'output_folder', type=click.Path(writable=True), help='Name of folder to write mmd files into. File name will be determined by wigos id')
@click.option('--location', '-l', help='The announced opendap location to use in documents')
@click.argument('nc_file', nargs=-1)
def mmd(output_folder, location, nc_file):
    '''Write mmd metadata file, based on the given netcdf file'''
    for f in nc_file:
        loc = location
        frost_extract.metadata.render_metadata(output_folder, f, loc)


download.add_command(observations)
download.add_command(elements)
download.add_command(source)
write.add_command(netcdf)
cli.add_command(download)
cli.add_command(write)


if __name__ == '__main__':
    cli()
