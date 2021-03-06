import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

requires = ('Babel',
            'ZODB3',
            'awesome-slugify',
            'betahaus.viewcomponent>=0.4.1',
            'colander>=1.4',
            'deform>=2.0.4',
            'deform_autoneed>=0.2.2b',
            'fanstatic',
            'html2text==2019.8.11',  # Last py 2.7 version
            'js.bootstrap>=3.3.4',
            'js.jqueryui',
            'peppercorn',
            'pyramid',
            'pyramid_beaker',
            'pyramid_chameleon',
            'pyramid_deform',
            'pyramid_mailer',
            'pyramid_tm',
            'pyramid_zodbconn',
            'pytz',
            'repoze.catalog',
            'repoze.evolution',
            'repoze.folder',
            'repoze.lru',
            'six',
            'zc.lockfile',
            'zope.component',
            'zope.interface',
            'zope.copy',)

extras_require = {
    'thumbnails': (
        'Pillow',
        'plone.scale',
    ),
}

tests_require = requires + extras_require['thumbnails']


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
      tests_require=tests_require,
      extras_require=extras_require,
      test_suite="arche",
      entry_points = """\
      [paste.app_factory]
      main = arche:main
      [fanstatic.libraries]
      arche = arche.fanstatic_lib:library
      [console_scripts]
      arche = arche.scripting:run_arche_script
      [pyramid.scaffold]
      arche_buildout=arche.scaffolds:BuildoutTemplate
      arche_plugin=arche.scaffolds:PluginTemplate
      """,
      )
