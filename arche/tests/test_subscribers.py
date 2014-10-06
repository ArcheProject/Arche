from unittest import TestCase

from pyramid import testing

from repoze.folder import Folder
from arche.interfaces import IFolder, IObjectAddedEvent, IObjectWillBeRemovedEvent


class SubobjectEventSubscriberTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.subscribers')
 
    def tearDown(self):
        testing.tearDown()

    def test_adding_with_subobject(self):
        root = Folder()
        folder = Folder()
        folder['1'] = Folder()
        folder['1']['2'] = Folder()
        #Add subscriber
        L = []
        def subscriber(context, event):
            L.append([context, event])
        self.config.add_subscriber(subscriber, [IFolder, IObjectAddedEvent])
        root['f'] = folder
        self.assertEqual(len(L), 3)

    def test_removing_with_subobject(self):
        root = Folder()
        root['1'] = Folder()
        root['1']['2'] = Folder()
        root['1']['2']['3'] = Folder()
        #Add subscriber
        L = []
        def subscriber(context, event):
            L.append([context, event])
        self.config.add_subscriber(subscriber, [IFolder, IObjectWillBeRemovedEvent])
        del root['1']
        self.assertEqual(len(L), 3)
