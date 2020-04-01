#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""argparse and main entrypoint script"""

import argparse
import sys
from logging import getLogger

from cheroot.wsgi import Server as WSGIServer, PathInfoDispatcher
from flask import url_for
from flask_restx import Api

from autotradeweb.common import add_log_parser, init_logging
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

    parser.add_argument("--disable-https", default=False, action="store_true",
                        dest="disable_https",
                        help="Disable HTTPS for swagger docs (useful for local debugging)")
    add_log_parser(parser)

    return parser


def main(argv=sys.argv[1:]) -> int:
    """main entry point for the concord server"""
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
            return url_for(self.endpoint('specs'), _external=True,
                           _scheme='https')
        Api.specs_url = specs_url

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
