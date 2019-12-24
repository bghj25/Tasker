import vk_botting
import credentials as cred
from pymysqlpool.pool import Pool  # Для работы с сервером и БД
import pymysql
import asyncio
import datetime
bot = vk_botting.Bot(vk_botting.when_mentioned_or_pm(), case_insensitive=True)
config = {'host': cred.host, 'user': cred.user, 'password': cred.password, 'db': cred.db, 'autocommit': True, 'charset': cred.charset, 'cursorclass': pymysql.cursors.DictCursor}
try:
    sqlpool = Pool(**config)
    sqlpool.init()
except Exception as exc:
    print(exc)


def sqlfunc(func):

    def wrapper(*args, **kwargs):
        global sqlpool
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(e)
            try:
                sqlpool = Pool(**config)
                sqlpool.init()
            except Exception as e:
                print(e)
            return func(*args, **kwargs)

    return wrapper


def draw_menu():  # Рисуем клавиатуре
    keyboard = vk_botting.Keyboard()
    keyboard.add_button('Новая_задача', vk_botting.KeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Мои_задачи',  vk_botting.KeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Удалить_задачу',  vk_botting.KeyboardColor.SECONDARY)
    return keyboard


@sqlfunc
def table_exist(table_name):  # Проверка существования таблицы
    try:
        con = sqlpool.get_conn()
        if not con.open:
            con.ping(True)
        cursor = con.cursor()
        cursor.execute('SELECT * FROM ' + str(table_name))
    except pymysql.ProgrammingError:
        sqlpool.release(con)
        return False
    else:
        sqlpool.release(con)
        return True


@sqlfunc
def task_to_table(task_description, task_datetime, user_id):
    con = sqlpool.get_conn()
    if not con.open:
        con.ping(True)
    cursor = con.cursor()
    if not table_exist('user' + str(user_id)):  # Если у пользователя нет основной таблицы, создаем ее
        cursor.execute('CREATE TABLE  user' + str(user_id) + ' (id INT auto_increment, '
                                                             'description NVARCHAR(100), '
                                                             'deadline DATETIME, PRIMARY KEY (id))')
    cursor.execute('INSERT INTO user' + str(user_id) + f' (description, deadline) VALUES (%s, %s)',
                   (task_description, task_datetime + '00'))


@bot.command(name='новая_задача')
async def new_task(ctx):
        await ctx.send('Создание нового задания', keyboard=vk_botting.Keyboard.get_empty_keyboard())
        await ctx.send('Отправте описание задания')  # орфография и пункутация автора сохранены

        def verefy(message):
            return message.from_id == ctx.message.from_id
        msg = await bot.wait_for('message_new', check=verefy, timeout=3600)
        if msg.text == '!отмена!':
            return await ctx.send('Создание задания отменено', keyboard=draw_menu())
        task_description = msg.text

        await ctx.send('Теперь введите время в формате ггггммддччмм')  # орфография и пункутация автора сохранены
        not_create = False

        def verefy(message):
            nonlocal not_create
            if message.from_id == ctx.message.from_id:
                if message.text == '!отмена!':
                    bot.loop.create_task(ctx.send('Создание задания отменено', keyboard=draw_menu()))
                    not_create = True
                    return True
                try:
                    datetime.datetime.strptime(message.text, '%Y%m%d%H%M')
                    return True
                except ValueError:
                    bot.loop.create_task(ctx.send('Неправильный формат даты'))
                    return False
            return False
        msg = await bot.wait_for('message_new', check=verefy, timeout=3600)

        if not not_create:
            task_datetime = msg.text
            task_to_table(task_description, task_datetime, ctx.message.from_id)
            await ctx.send('Напоминание добавлено', keyboard=draw_menu())


@sqlfunc
@bot.command(name='изменить')
async def change(ctx):
    if not ctx.message.reply_message:
        return await ctx.send('Ты творишь какюу-то дичь')
    con = sqlpool.get_conn()
    if not con.open:
        con.ping(True)
    cursor = con.cursor()
    change_from = ctx.message.reply_message.text.split(" ")
    change_from = " ".join(change_from[2::])
    await ctx.send('Теперь отправь новое описание')


    def verefy(message):
        return message.from_id == ctx.message.from_id
    change_to = await bot.wait_for('message_new', check=verefy, timeout=3600)
    cursor.execute(f'UPDATE user{ctx.message.from_id} SET description=%s WHERE description=%s', [change_to.text, change_from])
    await ctx.send('изменено')


@sqlfunc
@bot.command(name='мои_задачи')
async def my_tasks(ctx):
    con = sqlpool.get_conn()
    if not con.open:
        con.ping(True)
    cursor = con.cursor()
    cursor.execute('SELECT * FROM user' + str(ctx.message.from_id))
    tasks = cursor.fetchall()
    print(tasks)
    if not tasks:
        await ctx.send('Заданий нет', keyboard=draw_menu())
    for task in tasks:
        print(task['description'])
        message = str(task['deadline']) + ' ' + str(task['description'])
        await ctx.send(message, keyboard=draw_menu())
    sqlpool.release(con)


@bot.command(name='привет')
async def hello(ctx):
    await ctx.send('Пока', keyboard=draw_menu())


@sqlfunc
@bot.command(name='удалить_задачу')
async def delete_task(ctx):
    if not ctx.message.reply_message:
        return await ctx.send('Ты творишь какюу-то дичь')
    con = sqlpool.get_conn()
    if not con.open:
        con.ping(True)
    cursor = con.cursor()
    delete = ctx.message.reply_message.text.split(" ")
    delete = " ".join(delete[2::])
    cursor.execute(f'DELETE FROM user{ctx.message.from_id} WHERE description = %s', [delete])
    await ctx.send('Удалено', keyboard=draw_menu())


@sqlfunc
async def send_notifications():  # Отправака уведомлений пользователю
    while True:
        try:
            con = sqlpool.get_conn()
            if not con.open:
                con.ping(True)
            cursor = con.cursor()
            cursor.execute('SHOW TABLES IN tasks')
            tables = cursor.fetchall()
            for table in tables:
                cursor.execute('SELECT * FROM ' + table['Tables_in_tasks'] + ' WHERE deadline < NOW()')
                tasks = cursor.fetchall()
                for task in tasks:
                    notification = 'Напоминание №' + str(task['id']) + ' \n' + str(task['description'])
                    await bot.send_message(str(table['Tables_in_tasks']).replace('user', ''), notification)
                    cursor.execute('DELETE FROM ' + table['Tables_in_tasks'] + ' WHERE description = \'' +
                                   str(task['description']) + '\'')  # Запись об отправленном напоминании удаляем из БД
                print(tasks)
            sqlpool.release(con)
        except Exception as e:
            try:
                await bot.send_message(173427551, str(e), keyboard=draw_menu())
            except Exception as e1:
                print(e)
                print(e1)
        finally:
            await asyncio.sleep(60)


@bot.listen()
async def on_ready():
    bot.loop.create_task(send_notifications())

# @sqlfunc
# def parse_message(user_id, text):  # Парсит сообщение от пользователя
#     con = sqlpool.get_conn()
#     if not con.open:
#         con.ping(True)
#     cursor = con.cursor()
#     if text == '!отмена!':
#         cancel(user_id)
#     elif table_exist('_' + str(user_id)):  # Если временна таблица суещствует, заполняем ее
#         cursor.execute('SELECT * FROM _' + str(user_id))
#         row = cursor.fetchone()
#         if row['stage'] == 1:  # Если находимся на этапе добавления описания, добавляем описание
#             cursor.execute('UPDATE _' + str(user_id) + ' SET description = \'' + str(text) + '\''
#                                                                                              ''
#                                                                                              ', stage = 2 '
#                                                                                              'WHERE stage = 1')
#             write_msg(user_id, 'Теперь введите время в формате ггггммддччмм')
#         elif row['stage'] == 2:  # Вводим дату и время до тех пор, пока пользователь не отправит их в нужном формате
#             try:
#                 cursor.execute('UPDATE _' + str(user_id) + ' SET deadline = ' + str(text) + '00 WHERE stage = 2')
#             except Exception:
#                 write_msg(user_id, 'Неверный формат даты')
#             else:  # После того как все поля временной таблицы заполнены. переносим данные в основную
#                 if not table_exist('user' + str(user_id)):  # Если у пользователя нет основной таблицы, создаем ее
#                     cursor.execute('CREATE TABLE  user' + str(user_id) + ' (id INT auto_increment, '
#                                                                          'description NVARCHAR(100), '
#                                                                          'deadline DATETIME, PRIMARY KEY (id))')
#                 cursor.execute('INSERT INTO user' + str(user_id) + '(description, deadline) '
#                                                                    'SELECT description, deadline FROM _' + str(user_id))
#                 cursor.execute('DROP TABLE _' + str(user_id))
#                 write_msg(user_id, 'Напоминание добавлено', keyboard.get_keyboard())
#              # Различные частные случаи сообщений от пользователя
#     elif text == 'Привет':
#         write_msg(user_id, 'Привет', keyboard.get_keyboard())
#     elif text == 'Новая задача':
#         create_new_task(user_id)
#     elif text == 'Мои задачи':
#         show_my_tasks(user_id)
#     elif text == 'Начать' or text == 'Start':
#         write_msg(user_id, 'Новая задача - добавить новое напоминание\n'
#                             'Мои задачи - просмотреть и редактировать мои напоминания', keyboard.get_keyboard())
#     else:
#         write_msg(user_id, 'Я не понимаю твоей команды', keyboard.get_keyboard())
#     sqlpool.release(con)

bot.run(cred.vkCommunityToken)
