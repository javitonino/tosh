import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="tosh",
    version="0.0.1",
    author="Javier Torres",
    author_email="jtorres@carto.com",
    description=("Overcomplicated asynchronous shell"),
    license="BSD",
    keywords="shell asyncio",
    url="https://github.com/javitonino/tosh",
    packages=find_packages('.'),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Framework :: AsyncIO",
        "Topic :: System :: Shells",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires="""
        aiodns==1.1.1
        aiohttp==2.2.5
        appdirs==1.4.3
        asyncssh==1.11.0
        prompt-toolkit==1.0.15
        pymux==0.14
        PyYAML==3.12
        ply==3.10
    """,
    entry_points={
        'console_scripts': [
            'tosh = tosh.entry_point:run',
        ]
    }
)
