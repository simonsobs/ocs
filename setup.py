from setuptools import setup, find_packages

import versioneer

with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

so3g_etxras = ["so3g"]
dev_extras = ["pytest", "pytest-twisted", "pytest-docker-compose", "pytest-cov", "coverage", "docker"]
dev_extras.extend(so3g_etxras)

setup(name='ocs',
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
               'ocs-agent-cli=ocs.agent_cli:main',
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
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: 3.10",
          "Programming Language :: Python :: 3.11",
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
          'numpy<2.0',  # pin until 2.0 is supported in so3g
          'importlib_metadata;python_version<"3.10"',
          'setproctitle',
      ],
      extras_require={
          "so3g": so3g_etxras,
          "dev": dev_extras,
      },
      )
