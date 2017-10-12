#-*- coding: utf-8 -*-
"""Классы, описывающие типы полей"""

class Condition(object):
    """Класс, описывающий логические операции

    Параметры:
        left - левый операнд
        op - логическая операция
        right - правый операнд
        unary - унарная опирация
    """

    def __init__(self, left, op, right, unary = False):
        self.left = left
        self.right = right
        self.op = op
        self.unary = unary

    def __and__(self, other):
        return self.__class__(self, 'AND', other)

    def __rand__(self, other):
        return self.__class__(other, 'AND', self)

    def __or__(self, other):
        return self.__class__(self, 'OR', other)

    def __ror__(self, other):
        return self.__class__(other, 'OR', self)

    def __invert__(self):
        return self.__class__(self, 'NOT', None, True)

    def __str__(self):
        """Нормализует операнды и возвращает строковое представление логической операции"""

        if self.unary:
            return '{} {}'.format(self.op, self.normalize(self.left))
        else:
            return '{} {} {}'.format(self.normalize(self.left), self.op, self.normalize(self.right))

    def normalize(self, value):
        """Нормализует операнды"""

        return '({})'.format(value) if isinstance(value, self.__class__) else '{}'.format(value.name) if isinstance(value, BaseType) else ':{}_{}'.format(id(self), id(value))

    def get_values(self):
        """Возвращает словарь параметров"""

        def update_result(result, value):
            if isinstance(value, self.__class__):
                result.update(value.get_values())
            elif not isinstance(value, BaseType):
                result['{}_{}'.format(id(self), id(value))] = value

        result = dict()
        values = [self.left]
        if not self.unary:
            values.append(self.right)

        for value in values:
            update_result(result, value)

        return result

class BaseType(object):
    """Базовый тип

    Параметры строго именованные
        name - имя поля в БД (по усолчанию равно названию переменной в пользовательском классе-таблице)
        required - является ли поле обязательным (не None)
        foreign_key - является ли поле ссылкой на другую таблицу, значение поле класса BaseType
    """

    default = None
    def __init__(self, *, name = None, required = False, foreign_key = None):
        self.name = name
        self.required = required
        if foreign_key and not isinstance(foreign_key, BaseType):
            raise TypeError('Invalid foreign key')

        self.foreign_key = foreign_key

    def check(self, value):
        """Проверка значения на соответствие типу поля"""
        if not self._check_value(value):
            raise TypeError('Value is not a {}'.format(self.__class__.__name__))

    def _check_value(self, value):
        return type(value) is self._type

    def __eq__(self, value):
        return Condition(self, '=', value)

    def __ne__(self, value):
        return Condition(self, '!=', value)

    def __lt__(self, value):
        return Condition(self, '<', value)

    def __le__(self, value):
        return Condition(self, '<=', value)

    def __gt__(self, value):
        return Condition(self, '>', value)

    def __ge__(self, value):
        return Condition(self, '>=', value)

    def sql_type(self, mapper):
        """Возвращает SQL-представление поля для использования в CREATE TABLE"""
        return '{} {}'.format(self.name, mapper(self._type))

    def map_value(self, value):
        """SQL-представление значение поля"""
        return value

class String(BaseType):
    """Текстовый тип

    Параметры:
        length - максимальная длина поля
    """

    _type = str
    def __init__(self, length = None, *, name = None, required = False):
        super().__init__(name=name, required=required)
        self.length = length

    def check(self, value):
        super().check(value)
        if self.length is not None and len(value) > self.length:
            raise ValueError('Value is too big')

class Integer(BaseType):
    """Целочисленный тип"""
    _type = int

class Float(Integer):
    """Дробный тип"""
    _type = float

class Bool(BaseType):
    """Булевый тип"""
    _type = bool
    default = False

    def to_sql(self, value):
        return 1 if value else 0

    def map_value(self, value):
        return value != 0

class ForeignKeyProxy(object):
    """Прокси-класс для поля с внешней ссылкой, позволяет получить доступ к данным таблицы"""
    def __init__(self, value, foreign_field, engine):
        self.orig_value = value
        self.engine = engine
        self.foreign_field = foreign_field
        self.update_value(value)

    def __call__(self):
        return self.value

    def __getattr__(self, name):
        if self.foreign_table:
            return getattr(self.foreign_table, name)

        raise AttributeError('Foreign record not found')

    def update_value(self, value):
        self.foreign_table = None
        foreign_table = self.foreign_field.table_class(self.engine)
        rows = foreign_table.select(cond = self.foreign_field == value, limit = 1)
        if rows:
            self.foreign_table = list(rows)[0]
        self.value = value

    def __eg__(self, value):
        return self.value == value

    def has_changed(self):
        return self.orig_value != value

    def reset(self):
        self.orig_value = self.value

    def __str__(self):
        if self.foreign_table:
            return str(self.foreign_table)

        return 'No Data'
