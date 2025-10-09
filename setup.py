from setuptools import setup

setup(
    name="job-application-bot",
    version="0.1.0",
    packages=["app", "cli"],  # <-- forces explicit selection; bypasses auto-discovery error
)
