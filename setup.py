from setuptools import setup, find_packages

import versioneer

setup (name = 'ocs',
       description='Observatory Control System',
       package_dir={'ocs': 'ocs'},
       packages=find_packages(include=['ocs', 'ocs.*']),
       scripts=['bin/ocs-install-systemd'],
       entry_points={
           'console_scripts': [
               'ocsbow=ocs.ocsbow:main',
               'ocs-local-support=ocs.ocsbow:main_local',
               'ocs-client-cli=ocs.client_cli:main',
               ],
       },
       package_data={'': ['support/*json']}, 
       version=versioneer.get_version(),
       cmdclass=versioneer.get_cmdclass())
