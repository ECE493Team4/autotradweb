#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""argparse and main entrypoint script"""

import argparse
import logging
import os
import sys
from logging import getLogger
from logging.handlers import TimedRotatingFileHandler

import graypy
from cheroot.wsgi import Server as WSGIServer, PathInfoDispatcher
from flask import url_for
from flask_restx import Api

from autotradeweb.server import APP, DEFAULT_SQLITE_PATH

__log__ = getLogger(__name__)

LOG_LEVEL_STRINGS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


def log_level(log_level_string: str):
    """Argparse type function for determining the specified logging level"""
    if log_level_string not in LOG_LEVEL_STRINGS:
        raise argparse.ArgumentTypeError(
            "invalid choice: {} (choose from {})".format(
                log_level_string, LOG_LEVEL_STRINGS
            )
        )
    return getattr(logging, log_level_string, logging.INFO)


def add_log_parser(parser):
    """Add logging options to the argument parser"""
    group = parser.add_argument_group(title="Logging")
    group.add_argument(
        "--log-level",
        dest="log_level",
        default="INFO",
        type=log_level,
        help="Set the logging output level",
    )
    group.add_argument(
        "--log-dir",
        dest="log_dir",
        help="Enable TimeRotatingLogging at the directory " "specified",
    )
    group.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    group.add_argument(
        "--graylog-address",
        dest="graylog_address",
        help="Enable graylog for TCP log forwarding at the IP address specified.",
    )
    group.add_argument(
        "--graylog-port",
        dest="graylog_port",
        default=12201,
        help="Port for graylog TCP log forwarding.",
    )


def init_logging(args, log_file_path):
    """Intake a argparse.parse_args() object and setup python logging"""
    # configure logging
    handlers_ = []
    log_format = logging.Formatter(fmt="[%(asctime)s] [%(levelname)s] - %(message)s")
    if args.log_dir:
        os.makedirs(args.log_dir, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            os.path.join(args.log_dir, log_file_path),
            when="d",
            interval=1,
            backupCount=7,
            encoding="UTF-8",
        )
        file_handler.setFormatter(log_format)
        file_handler.setLevel(args.log_level)
        handlers_.append(file_handler)
    if args.verbose:
        stream_handler = logging.StreamHandler(stream=sys.stderr)
        stream_handler.setFormatter(log_format)
        stream_handler.setLevel(args.log_level)
        handlers_.append(stream_handler)

    if args.graylog_address:
        graylog_handler = graypy.GELFTCPHandler(args.graylog_address, args.graylog_port)
        handlers_.append(graylog_handler)

    logging.basicConfig(handlers=handlers_, level=args.log_level)


def get_parser() -> argparse.ArgumentParser:
    """Create and return the argparser for flask/cheroot server"""
    parser = argparse.ArgumentParser(
        description="Start the flask/cheroot server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-d", "--host", default="localhost", help="Hostname to listen on"
    )
    parser.add_argument(
        "-p", "--port", default=8080, type=int, help="Port of the webserver"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Run the server in Flask debug mode"
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_SQLITE_PATH,
        help="Path to the SQLITE database to store messages",
    )
    parser.add_argument(
        "--disable-https",
        default=False,
        action="store_true",
        dest="disable_https",
        help="Disable HTTPS for swagger docs (useful for local debugging)",
    )
    add_log_parser(parser)

    return parser


def main(argv=sys.argv[1:]) -> int:
    """main entry point for the autotradeweb server"""
    parser = get_parser()
    args = parser.parse_args(argv)
    init_logging(args, "autotradeweb.log")

    # monkey patch courtesy of
    # https://github.com/noirbizarre/flask-restplus/issues/54
    # so that /swagger.json is served over https
    if not args.disable_https:

        @property
        def specs_url(self):
            """Monkey patch for HTTPS"""
            return url_for(self.endpoint("specs"), _external=True, _scheme="https")

        Api.specs_url = specs_url

    __log__.info("starting server: host: {} port: {}".format(args.host, args.port))
    APP.config["SQLALCHEMY_DATABASE_URI"] = args.database
    if args.debug:
        APP.run(host=args.host, port=args.port, debug=True)
    else:
        path_info_dispatcher = PathInfoDispatcher({"/": APP})
        server = WSGIServer((args.host, args.port), path_info_dispatcher)
        try:
            server.start()
        except KeyboardInterrupt:
            __log__.info("stopping server: KeyboardInterrupt detected")
            server.stop()
            return 0
        except Exception:
            __log__.exception("stopping server: unexpected exception")
            raise


if __name__ == "__main__":
    sys.exit(main())
