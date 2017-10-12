#-*- coding: utf-8 -*-
"""Класс доступа к БД SQLite"""

import sqlite3
from .base_engine import BaseEngine

class SQLiteEngine(BaseEngine):
    def __init__(self, conn):
        self.db = sqlite3.connect(conn)
        self.db.row_factory = sqlite3.Row
        self.last_row_id = None
        self.last_row_count = 0

    def execute(self, sql , values):
        with self.db:
            if values is None:
                cur = self.db.execute(sql)
            else:
                cur= self.db.execute(sql, values)

            self.last_row_id = cur.lastrowid
            self.last_row_count = cur.rowcount
            return cur

    def row_id(self):
        return self.last_row_id

    def row_count(self):
        return self.last_row_count

    def map_type(self, _type):
        if _type == str:
            result = 'TEXT'
        elif _type in [int, bool]:
            result = 'INTEGER'
        elif _type == float:
            result = 'REAL'
        else:
            raise TypeError('Unsupported type {}'.format(str(_type)))

        return result
