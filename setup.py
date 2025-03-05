from setuptools import setup, find_packages

setup(
    name='CVFrameLabeler',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'PyQt5==5.15.9',
        'opencv-python==4.8.1.78',
        'numpy==1.24.4',
    ],
    entry_points={
        'console_scripts': [
            'cvframelabeler=main:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.ui', '*.qss', '*.png', '*.ico'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    description='CV Frame Labeler - A tool for video frame labeling and navigation (Beta Version)',
) 