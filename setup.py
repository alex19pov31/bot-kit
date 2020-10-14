from setuptools import setup, find_packages
import bot_kit

install_requires = []
with open('requirements.txt') as f:
    install_requires = f.read().replace('==', '>=').split()

with open('readme.md') as f:
    long_description = f.read()

setup(
    name="bot_kit",
    url="https://github.com/alex19pov31/bot-kit",
    version=bot_kit.__version__,
    packages=find_packages(),
    description="Telegram bot kit",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Alexander Nesterov",
    author_email="alex19pov31@gmail.com",
    license="MIT",
    install_requires=install_requires,
    python_requires='>=3.6'
)