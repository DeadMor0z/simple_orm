#-*- coding: utf-8 -*-
"""Классы описывающие таблицу"""

from .field_types import BaseType, Integer, Condition, ForeignKeyProxy

class TableNamespace(dict):
    """namespace-класс, автоматически преобразующий описания
       полей в классе типа "x = Integer" в "x = Integer(name = 'x')",
       а также устанавливающий аттрибут name тем классам, где он не был задан явно"""

    def __setitem__(self, key, value):
        if not key.startswith('__'):
            if type(value) is type and issubclass(value, BaseType):
                value = value(name=key)
            elif isinstance(value, BaseType) and not value.name:
                value.name = key
        super().__setitem__(key, value)

class TableMeta(type):
    """метакласс для первичной инициализации пользовательского класса-таблицы"""

    @classmethod
    def __prepare__(metacls, name, bases, **kwds):
        return TableNamespace()

    def __new__(cls, name, bases, namespace, **kwds):
        result = type.__new__(cls, name, bases, namespace)
        result.fields = dict()
        result.values = dict()
        result.new_values = dict()
        result.mapped_names = dict()
        for field, _type in namespace.items():
            if field.startswith('__') or callable(_type) or not isinstance(_type, BaseType):
                continue

            _type.table_class = result
            result.fields[field] = _type
            result.values[field] = _type.default
            if field != _type.name:
                result.mapped_names[_type.name] = field

        result._rowid = Integer(name = 'rowid')
        return result

class SQLMapper(metaclass=TableMeta):
    """Основной базовый класс для доступа к таблице данных (внутренний)

    Параметры:
        engine - класс доступа к БД
    """

    def __init__(self, engine = None):
        super().__setattr__('engine', engine)

    def __getattribute__(self, name):
        found = False
        value = None
        for values_name in ['new_values', 'values', 'fields']:
            values = super().__getattribute__(values_name)
            if name in values:
                value = values[name]

                if values_name == 'fields':
                    value = value.default
                found = True
                break

        if found:
            return value

        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in ['rowid', 'new_values']:
            return super().__setattr__(name, value)

        if name not in self.fields:
            raise AttributeError('No such column: {}'.format(name))

        field = self.fields[name]
        value = field.map_value(value)
        self.check_required(name, value)
        field.check(value)

        if not self.rowid:
            if field.foreign_key:
                value = ForeignKeyProxy(value, field.foreign_key, self.engine)
            self.values[name] = value
        elif self.values[name] != value:
            if field.foreign_key:
                self.values[name].update_value(value)
            else:
                self.new_values[name] = value

    def __delattr__(self, name):
        if name in self.new_values:
            del self.new_values[name]

        if name in self.values:
            del self.values[name]

    def check_required(self, field, value):
        """Проверка значения на соответствие типу поля, возвращает имя поля в таблице"""

        if field not in self.fields:
            raise AttributeError('No such column: {}'.format(field))

        if value is None and self.fields[field].required:
            raise ValueError('Required field \'{}\' can not be None'.format(field))

        return self.fields[field].name

    def check_required_values(self, values):
        """Проверка словаря значений на соответствие типам полей"""

        result = dict()
        for field,value in values.items():
            result[self.check_required(field, value)] = value

        return result

    def get_all_values(self):
        """Получение всех текущих значений полей"""

        result = dict()
        for field_name, field in self.fields.items():
            if field.foreign_key:
                result[field_name] = self.values[field_name]()
            else:
                result[field_name] = self.new_values.get(field_name, self.values[field_name])

        return result

    def execute(self, sql, values):
        """Выполнение запроса в БД"""
        if not self.engine:
            return sql, values

        return self.engine.execute(sql, values)

    def add_cond(self, sql, cond):
        """Добавление фильтра к SQL-запросу

        Параметры:
            sql - SQL-запрос
            cond - фильтр

        Возвращает sql-запрос с фильтром и словарь значений, использованных в фильтре
        """

        if cond:
            sql += ' WHERE {}'.format(cond)

        cond_dict = dict()
        if isinstance(cond, Condition):
            cond_dict = cond.get_values()

        return (sql, cond_dict)

    def reset_new_values(self):
        for field_name, field in self.fields.items():
            if field.foreign_key:
                self.values[field_name].reset()

        self.values.update(self.new_values)
        self.new_values = dict()

    def add(self):
        """Добавить запись в таблицу"""

        values = self.get_all_values()
        values = self.check_required_values(values)
        sql = 'INSERT into {} ({}) VALUES ({})'.format(self.__tablename__, ','.join(values), ','.join(':{}'.format(name) for name in values))
        self.execute(sql, values)
        if self.engine:
            self.rowid = self.engine.row_id()

        self.reset_new_values()
        return 'Ok'

    def save(self):
        """Сохранить(обновить, если существующая или добавить, если новая) запись в таблице."""

        if not self.rowid:
            return self.add()

        changed_list = dict()
        for field in self.fields.values():
            if field.foreign_key and self.values[field.name].has_changed():
                changed_list[field.name] = self.values[field.name]()
            elif field.name in self.new_values:
                changed_list[field.name] = self.new_values[field.name]

        changed_list = self.check_required_values(changed_list)
        sql = 'UPDATE {} SET {}'.format(self.__tablename__, ','.join('{0}=:{0}'.format(x) for x in changed_list))
        sql, cond_values = self.add_cond(sql, Condition(self._rowid, '=', self.rowid))
        changed_list.update(cond_values)
        self.execute(sql, changed_list)
        self.reset_new_values()
        return 'Ok'

    def delete(self):
        """Удалить существующую запись из таблицы"""

        if not self.rowid:
            return 'Record was not inserted'

        sql = 'DELETE from {}'.format(self.__tablename__)
        sql, cond_values = self.add_cond(sql, Condition(self._rowid, '=', self.rowid))
        return self.execute(sql, cond_values)

    def drop(self):
        """Удалить таблицу"""

        sql = 'DROP TABLE IF EXISTS {}'.format(self.__tablename__)
        return self.execute(sql, None)

    def create(self):
        """Создать таблицу"""

        fields_list = ','.join(field.sql_type(self.engine.map_type if self.engine else str) for field in self.fields.values())
        sql = 'CREATE TABLE {} ({})'.format(self.__tablename__, fields_list)
        return self.execute(sql, None)

    def __str__(self):
        """Текстовое представление записи"""

        results = ['Table \'{}\' row {}:'.format(self.__tablename__, self.rowid)]
        for field in self.fields:
            value = self.new_values.get(field, self.values.get(field, self.fields[field].default))
            results.append('{}: {}'.format(field, value))

        return '\n'.join(results)

    def select(self, fields = None, cond = None, limit = None):
        """Произвести выборку данных из таблицы

        Параметры:
            fields - Поле или список полей для выборки
            cond - фильтр для выборки
            limit - ограничитель выборки

        Возвращает генератор по списку классов типа SQLMapper
        """

        if fields and not isinstance(fields, (list, tuple)):
            fields = list(fields)
        elif fields is None:
            fields = []

        names = []
        for field in fields:
            if not isinstance(field, (str, BaseType)):
                raise TypeError('Invalid field')

            name = field if isinstance(field, str) else field.name
            if name not in self.fields or name not in self.mapped_names:
                raise AttributeError('No such column {}'.format(name))

            names.append(name)

        if not names:
            names.append('*')

        names.append('rowid')

        field_list = ','.join(names)
        sql = 'SELECT {} from {}'.format(field_list, self.__tablename__)
        sql, cond_values = self.add_cond(sql, cond)
        if limit:
            sql += ' LIMIT {}'.format(limit)

        if not self.engine:
            return sql, cond_values

        for row in self.engine.execute(sql, cond_values):
            table_row = self.__class__(self.engine)
            for row_name in row.keys():
                field_name = self.mapped_names.get(row_name, row_name)
                setattr(table_row, field_name, row[row_name])

            yield table_row


class Table(SQLMapper):
    """Базовый класс для описания таблиц"""
    rowid = None
