from setuptools import setup, find_packages

setup(
    name='starterkits',
    version='0.1.0',
    description='Starter Data Kits for CCG tools',
    author='Camilo Ramirez Gomez',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'pycountry',
        'pygadm',
        # 'osmnx',
        # 'boto3',
        'requests',
        'earthaccess',
    ],
    python_requires='>=3.6',
)
