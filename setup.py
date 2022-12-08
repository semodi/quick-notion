from setuptools import setup, find_packages

setup(
    name='quick_notion',
    version='0.0.1',
    url='https://github.com/semodi/quick-notion',
    author='Sebastian Dick',
    author_email='sebastiandick42@gmail.com',
    description='Add quick entries to my Notion databases',
    packages=find_packages(),    
    install_requires=[],
    scripts=['qn']
)
