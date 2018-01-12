# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import argparse

from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import render
from pyramid.response import Response

from arche.scripting import default_parser


class TakedownView(object):
    def __init__(self, message, template):
        self.message = message
        self.template = template

    def __call__(self, request):
        return Response(render(self.template, {'msg': self.message}, request=request))


def _waitress_console_logging():
    import logging
    logger = logging.getLogger('waitress')
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)


def takedown_app(env, parsed_ns):
    try:
        from waitress import serve
    except ImportError:
        print "Waitress needed to run this script"
        raise
    _waitress_console_logging()
    config = Configurator()
    config.include('pyramid_chameleon')
    msg = "We'll be back shortly. Sorry for the inconvenience!"
    if parsed_ns.message:
        msg = parsed_ns.message.decode('utf-8')
    #Figure out template path
    if ':' in parsed_ns.template or parsed_ns.template.startswith('/'):
        tpl = parsed_ns.template
    else:
        #Expect relative path
        tpl = os.path.join(os.getcwd(), parsed_ns.template)
        view = TakedownView(msg, tpl)
        #Test rendering to cause exception early
        view(env['request'])
        print ("Serving template from: %s" % tpl)
    takedown_view = TakedownView(msg, tpl)
    config.add_view(takedown_view, context=HTTPNotFound)
    print("Takedown app running... press ctrl+c to quit")
    app = config.make_wsgi_app()
    #Figure out port or socket
    kwargs = {}
    if ':' in parsed_ns.listen:
        kwargs['listen'] = parsed_ns.listen
    else:
        kwargs['unix_socket'] = parsed_ns.listen
        kwargs['unix_socket_perms'] = '666'
    serve(app, **kwargs)


def includeme(config):
    parser = argparse.ArgumentParser(parents=[default_parser])
    parser.add_argument("listen", help="Unix socket or host:port to listen to. Specify as: "
                                       "<path_to_socket> OR "
                                       "<host>:<port> OR *:<port>")
    parser.add_argument("-m", dest='message',
                        help="Message, default: "
                             "We'll be back shortly. Sorry for the inconvenience!")
    parser.add_argument("-t", dest='template',
                        help="Template, specify with package name or relative path. "
                                   "default: arche:templates/content/takedown.pt",
                        default="arche:templates/content/takedown.pt")
    config.add_script(
        takedown_app,
        name='takedown',
        title="Temp takedown site",
        argparser=parser,
        can_commit=False,
    )
