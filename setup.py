from setuptools import setup, find_packages
import bot_kit

install_requires = []
with open('requirements.txt') as f:
    install_requires = f.read().replace('==', '>=').split()

setup(
    name="bot_kit",
    version=bot_kit.__version__,
    packages=find_packages(),
    author="Alexander Nesterov",
    author_email="alex19pov31@gmail.com",
    license="MIT",
    install_requires=install_requires,
    python_requires='>=3.6',
)