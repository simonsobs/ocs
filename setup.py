from distutils.core import setup, Extension

VERSION = '0.1'

setup (name = 'ocs',
       version = VERSION,
       description = 'Observatory Control System',
       package_dir = {'ocs': 'ocs'},
       packages = ['ocs',
                   ])
