#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""argparse and main entrypoint script"""

import argparse
import sys
from logging import getLogger

from cheroot.wsgi import Server as WSGIServer, PathInfoDispatcher

from autotradeweb.common import add_log_parser
from autotradeweb.login_util import create_user
from autotradeweb.server import APP, DEFAULT_SQLITE_PATH

__log__ = getLogger(__name__)


def get_parser() -> argparse.ArgumentParser:
    """Create and return the argparser for flask/cheroot server"""
    parser = argparse.ArgumentParser(
        description="Start the flask/cheroot server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("-d", "--host", default='localhost',
                        help="Hostname to listen on")
    parser.add_argument("-p", "--port", default=8080, type=int,
                        help="Port of the webserver")
    parser.add_argument("--debug", action="store_true",
                        help="Run the server in Flask debug mode")
    parser.add_argument("--database", default=DEFAULT_SQLITE_PATH,
                        help="Path to the SQLITE database to store messages")
    add_log_parser(parser)

    return parser


def main(argv=sys.argv[1:]) -> int:
    """main entry point for the concord server"""
    parser = get_parser()
    args = parser.parse_args(argv)

    __log__.info("starting server: host: {} port: {}".format(args.host, args.port))
    APP.config['SQLALCHEMY_DATABASE_URI'] = args.database
    if args.debug:
        APP.run(
            host=args.host,
            port=args.port,
            debug=True
        )
    else:
        path_info_dispatcher = PathInfoDispatcher({'/': APP})
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
