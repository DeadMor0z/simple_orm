#-*- coding: utf-8 -*-

class BaseEngine(object):
    def execute(self, sql):
        raise NotImplemented

    def map_type(self, _type, length = None):
        raise NotImplemented
