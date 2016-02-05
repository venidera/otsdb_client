from setuptools import setup, find_packages
__version__ = '0.0.2'

try:
    from pypandoc import convert

    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()

if __name__ == '__main__':
    project_name = "otsdb_client"
    setup(
        name=project_name,
        version=__version__,
        author="Andre E Toscano",
        author_email="andre@venidera.com",
        description=("A Python client for OpenTSDB based in a simple socket for writing and fast urllib3 http client for reading"),
        license="GNU GPL",
        keywords="opentsdb, tsdb, time series",
        url="http://github.com/venidera/otsdb_client",
        packages=find_packages(),
        install_requires=['urllib3>=1.14'],
        long_description=read_md('README.md'),
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Intended Audience :: System Administrators",
            "Operating System :: Unix",
            "Topic :: Utilities",
        ],
        test_suite=project_name + '.tests',
    )
