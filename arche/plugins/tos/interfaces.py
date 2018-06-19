# -*- coding: utf-8 -*-
from pyramid.interfaces import IDict
from zope.interface import Interface

from arche.interfaces import IContent
from arche.interfaces import ITrackRevisions
from arche.interfaces import IIndexedContent


class ITOS(IContent, IIndexedContent, ITrackRevisions):
    pass


class ITOSManager(Interface):
    pass


class IAgreedTOS(IDict):
    pass
