from setuptools import setup, find_packages
import versioneer


setup(
    name="trio_inotify",
    description="Async inotify interface implemented on Trio",
    author="Alex Boag-Munroe",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    include_package_data=True,
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires='~=3.6',
    setup_requires=[
        "cffi",
    ],
    cffi_modules=["build/inotify.py:ffi","build/ioctl.py:ffi"],
    install_requires=[
        "trio >=0.11.0",
        "attrs",
        "cffi",
    ],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
