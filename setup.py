"""Setup configuration for Promptheus."""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'Promptheus - AI-powered prompt engineering CLI tool'

# Read requirements
with open(os.path.join(this_directory, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='promptheus',
    version='0.1.0',
    description='AI-powered prompt engineering CLI tool',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Promptheus Contributors',
    author_email='',
    url='https://github.com/abhichandra21/Promptheus',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={'promptheus': ['*.json']},
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'promptheus=promptheus.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.8',
    keywords='ai prompt-engineering cli gemini llm',
)
