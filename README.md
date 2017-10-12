# simple_orm
Пример простейшего ORM

orm.**Table** - основной класс-описание таблицы данных.
orm.**Integer**, orm.**Float**, orm.**String**, orm.**Bool** - классы типов полей в таблице

orm.**SQLiteEngine** - класс для доступа к БД SQLite.

### Code example - simple_orm_app.py

```python
#-*- coding: utf-8 -*-

from orm import *

#Описание таблицы Users (имя таблицы в БД - users)
class User(Table):
    __tablename__ = 'user'

    id = Integer #Тип поля int, имя в таблице 'id'
    name = String(256, name='my_name') #Тип поля TEXT (varchar), длиной 256 символов и с именем в таблице 'my_name'

#Описание таблицы Users (имя таблицы в БД - user_posts)
class Posts(Table):
    __tablename__ = 'user_posts'

    id = Integer
    user_id = Integer(foreign_key = User.id) #Тип поля Integer, ссылка на таблицу Users по полю users.id
    text = String

engine = SQLiteEngine('test.db') #Создаем подключение к БД
user = User(engine)
posts = Posts(engine)

user.drop() #Удаляем таблицу users, если она есть
user.create() # Созздаем таблицу users

posts.drop() #Удаляем таблицу user_posts
posts.create() #Создаем таблицу user_posts

#Задаем значения
user.id = 1
user.name = 'Vasya'
user.add() #Добавляем запись

user.id = 2
user.name = 'Petya'
user.add()

user.id = 3
user.name = 'Vanya'
user.add()

#Печатаем все записи из таблицы users
for row in user.select():
    print(row)

#Удаляем последнюю добавленнную запись
user.delete()

for row in user.select():
    print(row)

posts.id = 1
posts.user_id = 1 #Ссылка на запись в таблице users c id = 1
posts.text = 'Vasya post'
posts.add()

posts.id = 2
posts.user_id = 2 #Ссылка на запись в таблице users c id = 2
posts.text = 'Petya post'
posts.add()

#Печатаем все записи из таблицы user_posts, а также имя пользователя из таблицы users, полученное по ссылке
for row in posts.select():
    print(row)
    print(row.user_id.name)
```