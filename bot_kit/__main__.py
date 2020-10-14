import argparse
from configparser import ConfigParser

parser = argparse.ArgumentParser(description='Bot-kit cli')
subparsers = parser.add_subparsers(help='List of commands')
config_parser = subparsers.add_parser('config', help='generate default config')
config_parser.add_argument('--filename', default='settings.ini', help='config filename')

args = parser.parse_args()

if len(args.__dict__) == 0:
    parser.print_help()


def init_config(filename: str):
    config = ConfigParser()
    config.add_section('default')
    config.add_section('default_logging')
    config.set('default', 'token', '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')
    config.set('default', 'db', 'sqlite:///bot.db')
    config.set('default', 'use_logging', '1')
    config.set('default_logging', 'path', 'bot.log')
    config.set('default_logging', 'level', '20')
    config.set('default_logging', 'format', '%(asctime)s	%(levelname)s	%(message)s')

    with open(filename, 'w') as configfile:
        config.write(configfile)


if 'filename' in args:
    init_config(args.filename)

