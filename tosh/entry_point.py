"""Carto.sh entry point and argument parsing."""
import argparse
import appdirs
import os
import sys

from .tosh import Tosh
from .config import Config

def run():
    parser = argparse.ArgumentParser(prog="carto.sh")
    parser.add_argument("-c", "--config", default=appdirs.user_config_dir('tosh') + "/config.yml", type=open, help="path to alternative config.yml")
    args = parser.parse_args(sys.argv[1:])

    data_dir = appdirs.user_data_dir('tosh')
    os.makedirs(data_dir, exist_ok=True)

    Tosh(data_dir, Config(args.config)).run()
