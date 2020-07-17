from setuptools import setup, find_packages

import versioneer

setup (name = 'ocs',
       description='Observatory Control System',
       package_dir={'ocs': 'ocs'},
       packages=find_packages(include=['ocs', 'ocs.*']),
       scripts=['bin/ocsbow'],
       package_data={'': ['support/*json']}, 
       version=versioneer.get_version(),
       cmdclass=versioneer.get_cmdclass())
