from setuptools import setup, find_packages

import versioneer

with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup (name = 'ocs',
       description='Observatory Control System',
       long_description=long_description,
       long_description_content_type="text/x-rst",
       package_dir={'ocs': 'ocs'},
       packages=find_packages(include=['ocs', 'ocs.*']),
       scripts=[],
       entry_points={
           'console_scripts': [
               'ocsbow=ocs.ocsbow:main',
               'ocs-local-support=ocs.ocsbow:main_local',
               'ocs-client-cli=ocs.client_cli:main',
               'ocs-install-systemd=ocs.ocs_systemd:main',
               ],
           'ocs.plugins': [
               'ocs = ocs.plugin',
               ],
       },
       package_data={'': ['support/*json']}, 
       version=versioneer.get_version(),
       cmdclass=versioneer.get_cmdclass(),
       url="https://github.com/simonsobs/ocs",
       project_urls={
           "Source Code": "https://github.com/simonsobs/ocs",
           "Documentation": "https://ocs.readthedocs.io/",
           "Bug Tracker": "https://github.com/simonsobs/ocs/issues",
       },
       classifiers=[
           "Programming Language :: Python :: 3",
           "License :: OSI Approved :: BSD License",
           "Intended Audience :: Science/Research",
           "Topic :: Scientific/Engineering :: Astronomy",
           "Framework :: Twisted",
       ],
       python_requires=">=3.7",
       install_requires=[
           'autobahn',
           'twisted',
           'deprecation',
           'PyYAML',
           'influxdb',
           'numpy',
       ],
       extras_require={
           "so3g": ["so3g"],
       },
)
