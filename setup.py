from setuptools import setup, find_packages

setup(
    name='frost_extract',
    version='0.1',
    # packages=find_packages(),
    install_requires=[
        'Click',
        'netCDF4',
        'python-dateutil',
        'cf_units',
        'jinja2',
        'pyyaml',
    ],
    packages=['frost_extract'],
    package_dir={'frost_extract': 'frost_extract'},
    package_data={
        'frost_extract': ['templates/mmd.xml', 'templates/global_attributes.yaml']
        },
    entry_points='''
        [console_scripts]
        frost=frost_extract.__main__:cli
    ''',
)
