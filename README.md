# simple_orm
Пример простейшего ORM

orm.**Table** - основной класс-описание таблыцы данных.
orm.**Integer**, orm.**Float**, orm.**String**, orm.**Bool** - классы типов полей в таблице

orm.**SQLiteEngine** - класс для доступа к БД SQLite.

### Code example - simple_orm_app.py

```python
#-*- coding:utf-8 -*-

from router import BasicRouter, HttpException
from http import HTTPStatus

application = BasicRouter()

@application.route(r'/')
def index(environ, start_response):
    return 'Hello, world!!!'

@application.route(r'^/[1-5][1-3]\.test')
def index(environ, start_response):
    return dict(hello='Hello', world='World')

@application.route(r'^/[1-5][1-3]\.test/xyz')
def index(environ, start_response):
    raise HttpException(HTTPStatus.FORBIDDEN)
```
