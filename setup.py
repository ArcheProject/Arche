import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

requires = ('pyramid',
            'pyramid_mailer',
            'pyramid_tm',
            'pyramid_deform',
            'pyramid_beaker',
            'pyramid_deform',
            'pyramid_zodbconn',
            'pyramid_chameleon',
            'Babel',
            'Pillow',
            'ZODB3',
            'awesome-slugify',
            'betahaus.viewcomponent',
            'colander',
            'deform',
            'deform_autoneed>=0.2.2b',
            'fanstatic',
            'html2text',
            'js.bootstrap',
            'lingua',
            'peppercorn',
            'plone.scale',
            'pytz',
            'repoze.catalog',
            'repoze.folder',
            'repoze.lru',
            'six',
            'zope.component',
            'zope.interface',
            )


setup(name='Arche',
      version='0.1dev',
      description='Arche skeleton CMS and content framework',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Intended Audience :: Developers",
        ],
      author='Robin Harms Oredsson and contributors',
      author_email='robin@betahaus.net',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="arche",
      entry_points = """\
      [paste.app_factory]
      main = arche:main
      [fanstatic.libraries]
      arche = arche.fanstatic_lib:library
      [console_scripts]
      arche = arche.scripts:arche_console_script
      """,
      )
