import credentials as cred
import vk_botting
from pymysqlpool.pool import Pool  # Для работы с сервером и БД
import pymysql
import datetime
bot = vk_botting.Bot(vk_botting.when_mentioned_or_pm(), case_insensitive=True)
config = {'host': cred.host, 'user': cred.user, 'password': cred.password, 'db': cred.db, 'autocommit': True, 'charset': cred.charset, 'cursorclass': pymysql.cursors.DictCursor}
try:
    sqlpool = Pool(**config)
    sqlpool.init()
except Exception as exc:
    print(exc)


def sex_transform(sex):
    if int(sex) == 1:
        return 'м'
    else:
        return 'ж'
    
def mainmenu():
    keyboard = vk_botting.Keyboard()
    keyboard.add_button('Искать', vk_botting.KeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Заполнить заново', vk_botting.KeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Инфо', vk_botting.KeyboardColor.SECONDARY)
    return keyboard


def like_menu():
    keyboard = vk_botting.Keyboard()
    keyboard.add_button('Топчег', vk_botting.KeyboardColor.PRIMARY)
    keyboard.add_button('Нахуй', vk_botting.KeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Стоп', vk_botting.KeyboardColor.SECONDARY)
    return keyboard


def answer_menu():
    keyboard = vk_botting.Keyboard()
    keyboard.add_button('НраВ', vk_botting.KeyboardColor.PRIMARY)
    keyboard.add_button('НаХ', vk_botting.KeyboardColor.PRIMARY)
    return keyboard


def your_sex_menu():
    keyboard = vk_botting.Keyboard()
    keyboard.add_button('Мужской', vk_botting.KeyboardColor.PRIMARY)
    keyboard.add_button('Женский', vk_botting.KeyboardColor.PRIMARY)
    return keyboard


def search_sex_menu():
    keyboard = vk_botting.Keyboard()
    keyboard.add_button('Парня', vk_botting.KeyboardColor.PRIMARY)
    keyboard.add_button('Девушку', vk_botting.KeyboardColor.PRIMARY)
    return keyboard


async def user_registration(ctx):
    user_info = dict(user_id=None, user_name=None, user_sex=None, search_sex=None, description=None)
    user_info['user_id'] = ctx.from_id
    await ctx.send('Для начала представься', keyboard=vk_botting.Keyboard.get_empty_keyboard())

    def verefy(message):
        return message.from_id == ctx.from_id

    msg = await bot.wait_for('message_new', check=verefy, timeout=3600)
    user_info['user_name'] = msg.text

    await ctx.send('Теперь скажи какого ты пола', keyboard=your_sex_menu())
    msg = await bot.wait_for('message_new', check=verefy, timeout=3600)
    if msg.text.lower() == 'мужской':
        user_info['user_sex'] = 1
    elif msg.text.lower() == 'женский':
        user_info['user_sex'] = 2

    await ctx.send('Кого ищешь?', keyboard=search_sex_menu())
    msg = await bot.wait_for('message_new', check=verefy, timeout=3600)
    if msg.text.lower() == 'парня':
        user_info['search_sex'] = 1
    elif msg.text.lower() == 'девушку':
        user_info['search_sex'] = 2

    await ctx.send('Пару слов о тебе', keyboard=vk_botting.Keyboard.get_empty_keyboard())
    msg = await bot.wait_for('message_new', check=verefy, timeout=3600)
    user_info['description'] = msg.text
    cursor = con.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id=%s', [user_info['user_id']])
    users = cursor.fetchall()
    if users != ():
        cursor.execute(f'DELETE FROM users WHERE user_id=%s', [user_info['user_id']])
    #print(user_info)
    cursor.execute(f'INSERT INTO users (user_id, user_name, user_sex, search_sex, description) '
                           f'VALUES (%s, %s, %s, %s, %s)',
                           [user_info['user_id'], user_info['user_name'], user_info['user_sex'],
                            user_info['search_sex'], user_info['description']])
    cursor.close()
    await show_user_form(ctx)


async def show_user_form(ctx):
    cursor = con.cursor()
    cursor.execute(f'SELECT * FROM users WHERE user_id =%s', [ctx.from_id])
    user_form = cursor.fetchall()
    cursor.close()
#     if user_form[0]['user_sex'] == 1:
#         us = 'м'
#     else:
#         us = 'ж'
#     if user_form[0]['user_sex'] == 1:
#         ss = 'м'
#     else:
#         ss = 'ж'
    await ctx.send('Вот твоя анкета: \n' + user_form[0]['user_name'] + '\nЯ: ' + sex_transform(user_form[0]['user_sex']) +
                   '\nИщу: ' + sex_transform(user_form[0]['search_sex']) + '\n' + str(user_form[0]['description']),
                   keyboard=mainmenu())  # тут надо расписать красивую отправку сообщений


@bot.command(name='заполнить заново', has_spaces=True)
async def reregister(ctx):
    good_user = await bot.vk_request('groups.isMember', group_id=cred.muecyl_id, user_id=ctx.from_id)
    if good_user['response'] == 0:
        await ctx.send('Ты не муецилист')
    else:
        await user_registration(ctx)


@bot.command(name='начать')
async def begin(ctx):
    good_user = await bot.vk_request('groups.isMember', group_id=cred.muecyl_id, user_id=ctx.from_id)
    # print(good_user)
    if good_user['response'] == 0:
        await ctx.send('Ты не муецилист')
    else:
        cursor = con.cursor()
        cursor.execute(f'SELECT * FROM users WHERE user_id =%s', [ctx.from_id])
        user_form = cursor.fetchall()
        cursor.close()
        if user_form == ():
            await user_registration(ctx)
        else:
            await show_user_form(ctx)


async def suggest(ctx):
    cursor = con.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id={}'.format(ctx.from_id))
    user = cursor.fetchone()
    cursor.execute('SELECT * FROM users WHERE user_sex={} AND search_sex={}'.format(user['search_sex'], user['user_sex']))
    possible_users = cursor.fetchall()
    if user['suggested_users'] is not None:
        already_suggested = user['suggested_users'].split('s')
    else:
        already_suggested = list()
    done = False
    for possible_user in possible_users:
        print(str(possible_user['user_id'])) 
        print(ctx.from_id)
        if (str(possible_user['user_id']) not in already_suggested) and (str(possible_user['user_id']) != ctx.from_id):
            await ctx.send('Нашел для тебя:\n{}\n{}'.format(possible_user['user_name'], possible_user['description']), keyboard=like_menu())
            already_suggested.append(str(possible_user['user_id']))
            already_suggested = 's'.join(already_suggested)
            cursor.execute('UPDATE users SET suggested_users = \'{}\' WHERE user_id = {}'.format(already_suggested, ctx.from_id))
            cursor.execute('UPDATE users SET last_suggestion = {} WHERE user_id = {}'.format(possible_user['user_id'], ctx.from_id))
            done = True
            break
    if not done:
        cursor.execute('UPDATE users SET last_suggestion = -1 WHERE user_id = {}'.format(ctx.from_id))
        await ctx.send('Нет подходящих', keyboard=mainmenu())
    cursor.close()


@bot.command(name='искать')
async def search(ctx):
    cursor = con.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id={}'.format(ctx.from_id))
    user = cursor.fetchone()
    print(user)
    if user is None:
        ctx.send('Для начала зарегистрируйся')
        await user_registration(ctx)
    else:
        await suggest(ctx)


@bot.command(name='топчег')
async def topcheg(ctx):
    cursor = con.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id={}'.format(ctx.from_id))
    user = cursor.fetchone()
    if user['last_suggestion'] == -1:
        await ctx.send('Вероятно, тебе никого не предлагали, или предложение уже не актуально')
    else:
        #рассматриваем два случая: пустая и непустая очередь у найденного юзера
        cursor.execute('SELECT * FROM users WHERE user_id = {}'.format(user['last_suggestion']))
        suggestion = cursor.fetchone()
        print(suggestion['queue']) 
        print ('hi') 
        if suggestion['queue'] != '':
            queue = suggestion['queue'].split('s')
        else:
            queue = list()
        print(queue) 
        if len(queue) == 0:
            print('sendind...')
            await bot.send_message(peer_id=user['last_suggestion'], message='Тебя оценили\n{}\n{}'.format(user['user_name'], user['description']), keyboard=answer_menu())
        if str(ctx.from_id) not in queue:
            queue.append(str(user['user_id']))
            queue = 's'.join(queue)
            cursor.execute('UPDATE users SET queue = \'{}\' WHERE user_id={}'.format(queue, user['last_suggestion']))
    cursor.close()
    await suggest(ctx)


@bot.command(name='нахуй')
async def nahui(ctx):
    await suggest(ctx)


@bot.command(name='стоп')
async def restart(ctx):
    cursor = con.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id={}'.format(ctx.from_id))
    user = cursor.fetchone()
    if user['suggested_users']!='' and user['suggested_users'] is not None:
        suggested = user['suggested_users'].split('s')
        suggested.pop()
        suggested = 's'.join(suggested)
        print('UPDATE users SET suggested_users =\'{}\' WHERE user_id = {}'.format(suggested, ctx.from_id))
        cursor.execute('UPDATE users SET suggested_users =\'{}\' WHERE user_id = {}'.format(suggested, ctx.from_id))
    cursor.execute('UPDATE users SET last_suggestion =-1 WHERE user_id = {}'.format(ctx.from_id))
    cursor.close()
    await show_user_form(ctx)


@bot.command(name='нрав')
async def like(ctx):
    cursor = con.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id={}'.format(ctx.from_id))
    user = cursor.fetchone()
    if user['queue'] is not None and user['queue'] != '':
        queue = user['queue'].split('s')
        await bot.send_message(peer_id=queue[0], message='Добавляйся, vk.com/id{}'.format(ctx.from_id))
        await ctx.send('Добавляйся, vk.com/id{}'.format(queue[0]))
        queue.pop(0)
        queue = 's'.join(queue)
        cursor.execute('UPDATE users SET queue = \'{}\' WHERE user_id = {}'.format(queue, user['user_id']))
        cursor.close()
        await next_suggestion(ctx)
    else:
        cursor.close()
        await ctx.send('информация не акутальна', keyboard=mainmenu())
        await show_user_form(ctx)


@bot.command(name='нах')
async def nah(ctx):
    cursor = con.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id={}'.format(ctx.from_id))
    user = cursor.fetchone()
    if user['queue'] is not None and user['queue'] != '':
        queue = user['queue'].split('s')
        queue.pop(0)
        queue = 's'.join(queue)
        cursor.execute('UPDATE users SET queue = \'{}\' WHERE user_id = {}'.format(queue, user['user_id']))
        cursor.close()
        await next_suggestion(ctx)
    else:
        cursor.close()
        await ctx.send('информация не акутальна', keyboard=mainmenu())
        await show_user_form(ctx)


async def next_suggestion(ctx):
    cursor = con.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id={}'.format(ctx.from_id))
    user = cursor.fetchone()
    print(user['queue'])
    if user['queue'] is None or user['queue'] == '':
        cursor.close()
        await ctx.send('Больше нет заявок')
        await show_user_form(ctx)
    else:
        queue = user['queue'].split('s')
        print(queue)
        cursor.execute('SELECT * FROM users WHERE user_id={}'.format(queue[0]))
        suggestion = cursor.fetchone()
        await ctx.send('Тебя оценили\n{}\n{}'.format(suggestion['user_name'], suggestion['description']), keyboard=answer_menu())
        cursor.close()


@bot.command(name='инфо')
async def info(ctx):
    await ctx.send('v1.0.6 \n так же здесь будет инутрукция')
# async def reset_suggestions():
#     cursor = con.cursor()
#     cursor.execute('UPDATE users SET suggested_users = \'\'')
#     cursor.execute('UPDATE users SET last_suggestion = -1')
#     cursor.close()
#     print(datetime.datetime.now())
#
#
# @bot.listen()
# async def on_ready():
#     bot.loop.create_task(reset_suggestions())
#
con = sqlpool.get_conn()
if not con.open:
    con.ping(True)

bot.run(cred.token)

