from setuptools import setup

setup(
    name='lex-analytics',
    version='0.1.0',
    description='Lex Analytics',
    author='Sebastian Russo',
    author_email='russo.sebastian@gmail.com',
    # packages=['lex_analytics'](where='.'), # Automatically find packages
    packages=['lex_analytics'],
    package_dir={'': '.'}, # Root directory for packages
    include_package_data=True, # Include non-code files (e.g. config files)
    zip_safe=True,
    install_requires=[
        'aws-cdk-lib>=2.190.0,<3.0.0',
        'constructs>=10.0.0,<11.0.0',
        'boto3>=1.26.0,<2.0.0',
        'rootpath',
        'pytest==7.2.0',
        'pytest-env',
        'pytest-html',
        'pytest-cov',
        'toml>=0.10.2',
        'ruff>=0.11.10',
        'pluggy>=1.0.0',
    ],
)
