# setup.py
from setuptools import find_packages, setup

setup(
    name='casing_trainer',
    version='1.0',
    packages=find_packages(),
    include_package_data=True,
    description='Auralis Casing Pressure Trainer Package',
    install_requires=[
        'tensorflow>=2.8',
        'pandas',
        'scikit-learn',
        'gcsfs'  # Permite leer archivos desde Google Cloud Storage
    ]
)