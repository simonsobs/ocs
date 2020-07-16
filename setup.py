from setuptools import setup, Extension

import versioneer

setup (name = 'ocs',
       description='Observatory Control System',
       package_dir={'ocs': 'ocs'},
       packages=['ocs',
                 'ocs.agent'],
       scripts=['bin/ocsbow'],
       package_data={'': ['support/*json']}, 
       version=versioneer.get_version(),
       cmdclass=versioneer.get_cmdclass())
