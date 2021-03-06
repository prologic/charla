"""Configuration Handling

Supports configuration of options via the command-line
and/or a configuration file. Optiona read form
configuration file override those given via command line options.
"""


from __future__ import print_function

from os import environ
from warnings import warn
from os.path import exists
from ConfigParser import ConfigParser
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


import reprconf
from . import plugins
from .version import version


class Config(reprconf.Config):

    prefix = "CHARLA_"

    def __init__(self, file=None, **kwargs):
        super(Config, self).__init__(file, **kwargs)

        self.parse_environ()
        self.parse_options()
        self.validate()

    def parse_environ(self):
        """Check the environment variables for options."""

        config = {}

        for key, value in environ.iteritems():
            if key.startswith(self.prefix):
                name = key[len(self.prefix):].lower()
                config[name] = value

        self.update(config)

    def parse_options(self):
        parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter,
            version=version,
        )

        add = parser.add_argument

        add(
            "--config", action="store", default=None,
            dest="config", metavar="FILE", type=str,
            help="read configuration from FILE"
        )

        add(
            "--debug", action="store_true", default=False,
            dest="debug",
            help="enable debugging mode"
        )

        add(
            "--daemon", action="store_true", default=False,
            dest="daemon",
            help="run as a background process"
        )

        add(
            "--verbose", action="store_true", default=False,
            dest="verbose",
            help="enable verbose logging"
        )

        add(
            "--logfile", action="store", default=None,
            dest="logfile", metavar="FILE", type=str,
            help="store logging information to FILE"
        )

        add(
            "--pidfile", action="store", default="charla.pid",
            dest="pidfile", metavar="FILE", type=str,
            help="write process id to FILE"
        )

        add(
            "--embedded", action="store_true",
            default=bool(int(environ.get("EMBEDDED", "0"))),
            dest="embedded",
            help="Use an embedded database"
        )

        add(
            "--dbhost", action="store",
            default=environ.get("DBHOST", "localhost"),
            dest="dbhost", metavar="HOST", type=str,
            help="set database host to HOST (Redis)"
        )

        add(
            "--dbport", action="store",
            default=int(environ.get("DBPORT", "6379")),
            dest="dbport", metavar="PORT", type=int,
            help="set database port to PORT (Redis)"
        )

        add(
            "-p", "--plugin",
            action="append", default=plugins.DEFAULTS, dest="plugins",
            help="Plugin to load (multiple allowed)"
        )

        add(
            "-P", "--port",
            action="store", type=str,
            default="6667", dest="port",
            help="Port to listen to (+6667 for SSL)"
        )

        add(
            "--ssl-cert",
            action="store", type=str, default=None,
            metavar="FILE", dest="sslcert",
            help="Path to SSL Certificate to use"
        )

        add(
            "--ssl-key",
            action="store", type=str, default=None,
            metavar="FILE", dest="sslkey",
            help="Path to SSL Key to use"
        )

        namespace = parser.parse_args()

        if namespace.config is not None:
            filename = namespace.config
            if exists(filename):
                config = reprconf.as_dict(str(filename))
                for option, value in config.pop("globals", {}).items():
                    if option in namespace:
                        self[option] = value
                    else:
                        warn("Ignoring unknown option %r" % option)
                self.update(config)

        for option, value in namespace.__dict__.items():
            if option not in self and value is not None:
                self[option] = value

    def validate(self):
        if self["port"][0] == "+" and not self.get("sslcert"):
            print(
                "Binding to secure port {} but no SSL Certificate!".format(
                    self["port"]
                )
            )
            print("Use --ssl-cert=/path/to/cert.crt")
            raise SystemExit(1)

    def reload_config(self):
        filename = self.get("config")
        if filename is not None:
            config = reprconf.as_dict(filename)
            config.pop("global", None)
            self.update(config)

    def save_config(self, filename=None):
        if filename is None:
            filename = self.get("config", "charla.ini")

        parser = ConfigParser()
        parser.add_section("globals")

        for key, value in self.items():
            if isinstance(value, dict):
                parser.add_section(key)
                for k, v in value.items():
                    parser.set(key, k, repr(v))
            else:
                parser.set("globals", key, repr(value))

        with open(filename, "w") as f:
            parser.write(f)
