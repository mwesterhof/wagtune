from setuptools import setup, find_packages


with open('README.rst') as readme_file:
    readme = readme_file.read()


with open('HISTORY.rst') as history_file:
    history = history_file.read()


requirements = [
    'cryptography==40.0.1',
    'wagtail>4.0,<5.1',
    'html2text==2020.1.16',

]
test_requirements = ['pytest>=3']


setup(
    author="Marco Westerhof",
    author_email='m.westerhof@lukkien.com',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    description="Simplified A/B testing for wagtail",
    install_requires=requirements,
    license="BSD license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='wagtune',
    name='wagtune',
    packages=find_packages(include=['wagtune', 'wagtune.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/mwesterhof/wagtune',
    version='0.1.0',
    zip_safe=False,
)
