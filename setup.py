from distutils.core import setup, Extension

import versioneer

setup (name = 'ocs',
       description='Observatory Control System',
       package_dir={'ocs': 'ocs'},
       packages=['ocs'],
       version=versioneer.get_version(),
       cmdclass=versioneer.get_cmdclass())
