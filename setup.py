from setuptools import setup, find_packages

setup(
    name="plume_tracker",
    version="0.1",
    packages=find_packages(),
    package_data={
        'plume_tracker': ['templates/*', 'static/*']
    },
    install_requires=[
        'flask',
        'aiohttp',
        'pandas',
        'nest-asyncio'
    ],
    python_requires='>=3.7'
)