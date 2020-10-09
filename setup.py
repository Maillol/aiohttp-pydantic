from setuptools import setup


setup(
    name='aiohttp_pydantic',
    version='0.0.1',
    description='Aiohttp View using pydantic to validate request body and query sting regarding method annotation',
    keywords='aiohttp pydantic annotation unpack inject validate',
    author='Vincent Maillol',
    author_email='vincent.maillol@gmail.com',
    url='https://github.com/Maillol/aiohttp-pydantic',
    license='MIT',
    packages=['aiohttp_pydantic'],
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: MIT License'
    ],
    python_requires='>=3.6',
    install_requires=['aiohttp', 'pydantic']
)
