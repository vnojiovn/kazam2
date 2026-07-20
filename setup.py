#!/usr/bin/env python3

import os
import re
import glob

from setuptools import setup

here = os.path.dirname(os.path.realpath(__file__))

#
# DistUtilsExtra provides the i18n/help/icon build steps used by distro
# packaging.  It is optional: a plain "pip install ." works without it,
# translations and the localized .desktop file are then not built.
#
try:
    from DistUtilsExtra.command import build_extra, build_i18n, build_help, build_icons
    CMDCLASS = {'build': build_extra.build_extra,
                'build_i18n': build_i18n.build_i18n,
                'build_help': build_help.build_help,
                'build_icons': build_icons.build_icons}
    HAVE_DISTUTILS_EXTRA = True
except ImportError:
    CMDCLASS = {}
    HAVE_DISTUTILS_EXTRA = False

try:
    with open(os.path.join(here, "kazam", "version.py")) as fh:
        VERSION = re.search(r"VERSION = '(.*)'", fh.read()).group(1)
except (OSError, AttributeError):
    VERSION = "1.0.0"

data_files = [('share/kazam/ui/', glob.glob('data/ui/*ui')),
              ('share/kazam/sounds/', glob.glob('data/sounds/*ogg')),
              ('share/icons/gnome/scalable/apps/', glob.glob('data/icons/scalable/*svg')),
              ]

if HAVE_DISTUTILS_EXTRA:
    # The original project carried this in setup.cfg (dropped by the fork):
    # build_i18n merges data/kazam.desktop.in with the translations in po/.
    OPTIONS = {'build_i18n': {
        'domain': 'kazam',
        'desktop_files': '[("share/applications", ("data/kazam.desktop.in",))]',
    }}
else:
    # Without build_i18n, install the pre-generated .desktop file instead.
    data_files.append(('share/applications/', ['data/kazam.desktop']))
    OPTIONS = {}

setup(name='kazam',
      version=VERSION,
      description='A screencasting program created with design in mind.',
      author='Henry Fuheng Wu, David Klasinc',
      author_email='wufuheng@gmail.com',
      long_description=open(os.path.join(here, "README.md"), "r", encoding="utf-8").read(),
      long_description_content_type="text/markdown",
      # Runtime dependencies only.  PyGObject, pycairo and dbus-python are
      # best satisfied by distribution packages (python3-gi, python3-cairo,
      # python3-dbus); pip builds them from source only if they are missing.
      install_requires=[
          'python-xlib',
          'dbus-python',
          'PyGObject',
          'pyxdg',
          'pycairo',
          'distro',
      ],
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Environment :: X11 Applications :: GTK',
                   'Intended Audience :: End Users/Desktop',
                   'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 3',
                   'Topic :: Multimedia :: Graphics :: Capture :: Screen Capture',
                   'Topic :: Multimedia :: Sound/Audio :: Capture/Recording',
                   'Topic :: Multimedia :: Video :: Capture',
                   ],
      keywords='screencast screenshot capture audio sound video recorder kazam OCR webcam',
      url='https://github.com/henrywoo/kazam',
      license='GPL-3.0-or-later',
      scripts=['bin/kazam'],
      packages=['kazam',
                'kazam.pulseaudio',
                'kazam.backend',
                'kazam.frontend',
                ],
      data_files=data_files,
      options=OPTIONS,
      cmdclass=CMDCLASS,
      )
