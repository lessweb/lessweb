from setuptools import setup, find_packages  # Always prefer setuptools over distutils
from codecs import open  # To use a consistent encoding
import re
import ast

_version_re = re.compile(r'__version__\s+=\s+(.*)')
version = str(ast.literal_eval(
    _version_re.search(
        open('lessweb/__init__.py').read()
    ).group(1)
))


setup(
        name = 'lessweb',
        version=version,
        description='A pythonic web framework',
        long_description='\nREADME: https://github.com/lessweb/lessweb\n\n'
                         'Cookbook: http://www.lessweb.cn',
        url='https://github.com/lessweb/lessweb',
        author='qorzj',
        author_email='goodhorsezxj@gmail.com',
        license='Apache 2',
        platforms=['any'],

        classifiers=[
            ],
        keywords='lessweb web web.py aiohttp',
        packages = ['lessweb',],
        package_data={
            'lessweb': ['py.typed'],
        },
        install_requires=['aiohttp', 'toml', 'orjson', 'lesscli', 'typing_inspect'],
        entry_points={
            'console_scripts': [
                ],
            },
    )
