from setuptools import setup

setup(
    name='canvascli',
    version='1.0',
    py_modules=['canvascli'],
    install_requires=[
        'Click',
        'requests',
        'pandas',
        'openpyxl',
    ],
    entry_points='''
        [console_scripts]
        canvascli=canvascli:cli
    ''',
)
