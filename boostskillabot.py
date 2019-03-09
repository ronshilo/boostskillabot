#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Basic example for a bot that uses inline keyboards.

# This program is dedicated to the public domain under the CC0 license.
"""
import logging
import yaml
import telegram
# noinspection PyPackageRequirements
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import datetime
import dataset
import tabulate

logging.basicConfig(format='[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

UnregisterGroup = 'Unregister group'
RegisterGroup = 'Register group'
ListAllGroups = 'List all groups'
LogOnToday = 'Login today'
WhoElsaIsOnToday = 'Who elsa is on today'
HowToAddGroup = 'How to add a group'
AdminInfo = 'Admin info'
Rules = 'Rules'
MoreInfo = 'MoreInfo'

rules_str = ''


def send_start_keyboard(bot, update: Updater):
    keyboard = [[KeyboardButton('/start', )]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    bot.send_message(text='use the /start key to reload this menu',
                     chat_id=update.effective_chat.id,
                     # reply_to_message_id=update.effective_message.message_id,
                     reply_markup=reply_markup)


# noinspection PyUnusedLocal
def private_talk(bot, update: Updater) -> None:
    """
    this part is used for 1 on 1 talk's with users.
    :param bot:
    :param update:
    :return:
    """
    keyboard = [
        [InlineKeyboardButton(LogOnToday, callback_data=LogOnToday)],
        [InlineKeyboardButton(WhoElsaIsOnToday, callback_data=WhoElsaIsOnToday)],
        [InlineKeyboardButton(ListAllGroups, callback_data=ListAllGroups)],
        [InlineKeyboardButton(HowToAddGroup, callback_data=HowToAddGroup)],
        [InlineKeyboardButton(Rules, callback_data=Rules)],
        [InlineKeyboardButton(MoreInfo, callback_data=MoreInfo)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)

    list_of_admins = config['list_of_admins']

    the_user = update.effective_user.username
    if the_user in list_of_admins:
        keyboard = [[InlineKeyboardButton(AdminInfo, callback_data=AdminInfo)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(f'Hi {the_user}, you can also see admin views', reply_markup=reply_markup)


def is_group_active(chat_id: int) -> bool:
    for group in db['groups']:
        if chat_id == group['chat_id']:
            return group['active']
    return False


def is_group_in_db(chat_id: int) -> bool:
    return any([chat_id == x['chat_id'] for x in db['groups']])


# noinspection PyUnusedLocal
def group_talk(bot, update: Updater) -> None:
    chat_id = update.effective_chat.id
    if is_group_active(chat_id):
        keyboard = [[InlineKeyboardButton(UnregisterGroup, callback_data=UnregisterGroup)]]
    else:
        keyboard = [[InlineKeyboardButton(RegisterGroup, callback_data=RegisterGroup)]]

    keyboard.append([InlineKeyboardButton(LogOnToday, callback_data=LogOnToday)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)


def start(bot, update: Updater) -> None:
    logger.info(f'User: {update.effective_user.name} click /start')
    if update.effective_chat.PRIVATE == update.effective_chat.type:
        private_talk(bot, update)
    else:
        group_talk(bot, update)

    send_start_keyboard(bot, update)


def admin_info(bot, update) -> None:
    str_to_print = 'TODO: BoostSkilla is only 10% of my time.\nLets work on the essentials first'
    bot.send_message(text=str_to_print,
                     chat_id=update.callback_query.message.chat_id,
                     message_id=update.callback_query.message.message_id)


class GroupInfo(object):
    def __init__(self, name: str, link: str, chat_id):
        self.name = name
        self.link = link
        self.description = ''
        self.chat_id = chat_id
        self.ctime = str(datetime.datetime.now())
        self.group_admin = ''

    def group_dict(self) -> dict:
        return {'name': self.name,
                'link': self.link,
                'description': self.description,
                'chat_id': self.chat_id,
                'ctime': self.ctime,
                'group_admin': self.group_admin,
                'active': True}


def get_db(db_file_path: str) -> dataset.connect:
    return dataset.connect(f'sqlite:///{db_file_path}/mydatabase.db')


def set_group_as_active(chat_id: int):
    group_dict = db['groups'].find_one(chat_id=chat_id)
    db_id = group_dict['id']
    group_name = group_dict['name']
    db['groups'].update(dict(id=db_id, active=True), ['id'])
    logger.info(f'the group {group_name} is set as active')


def set_group_as_inactive(chat_id: int):
    group_dict = db['groups'].find_one(chat_id=chat_id)
    db_id = group_dict['id']
    group_name = group_dict['name']
    db['groups'].update(dict(id=db_id, active=False), ['id'])
    logger.info(f'the group {group_name} is set as inactive')


def send_message(text: str, bot, update, reply_markup=None) -> None:
    bot.send_message(text=text,
                     chat_id=update.callback_query.message.chat_id,
                     message_id=update.callback_query.message.message_id,
                     reply_markup=reply_markup)


def unregister_group(bot, update):
    chat_id = update.effective_chat.id
    for group in db['groups']:
        if chat_id == group['chat_id']:
            if is_group_active(chat_id):
                set_group_as_inactive(chat_id)
                send_message("removed group: {}".format(str(update.effective_chat.title)), bot, update)
                return
            else:
                send_message("group {} is not active: ".format(str(update.effective_chat.title)), bot, update)
                return

    send_message("group {} is unknown: ".format(str(update.effective_chat.title)), bot, update)


def register_group(bot, update):
    chat_id = update.effective_chat.id
    try:
        invite_link = bot.export_chat_invite_link(chat_id)
    except telegram.error.BadRequest:
        text_to_send = 'Oops...\nit looks like you\'re group is not setup as a supergroup.\nPlease review how to ' \
                       'setup a group:'
        keyboard = [[InlineKeyboardButton(HowToAddGroup, callback_data=HowToAddGroup)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        send_message(text_to_send, bot, update, reply_markup=reply_markup)
        return

    chat = bot.get_chat(chat_id)
    query = update.callback_query
    if invite_link is None:
        logger.error('cant save group {} the is no link'.format(chat.title))

    else:
        new_group = GroupInfo(name=chat.title, link=invite_link, chat_id=chat_id)
        new_group.description = chat.description
        new_group.group_admin = update.effective_user.name

        if is_group_in_db(chat_id):
            if is_group_active(chat_id):
                logger.info(f'{chat.title} is db as {chat_id}')
            else:
                set_group_as_active(chat_id)
        else:
            db['groups'].insert(new_group.group_dict())

    bot.edit_message_text(text="Register group: {}".format(str(update.effective_chat.title)),
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)


def list_all_groups(bot, update):
    send_message(f'The list of groups is:\n\n', bot, update)
    count = 0
    for group in db['groups']:
        if is_group_active(group['chat_id']):
            count += 1
            chat = bot.get_chat(group['chat_id'])
            admin_user = group['group_admin']
            keyboard = [
                [InlineKeyboardButton(f"join", url=chat.invite_link)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            send_message(f'Name: {chat.title}.\nDescription:'
                         f' {chat.description}.\nGroup POC: {admin_user}',
                         bot, update, reply_markup=reply_markup)

    send_message(f'There are {count} active groups\n\n', bot, update)


def get_date_str() -> str:
    return str(datetime.datetime.today().date()).replace('-', '')


# noinspection PyUnusedLocal
def log_on_today(bot, update):
    today = get_date_str()
    user_name = update.effective_user.name
    topic = update.effective_chat.title
    user_id = update.effective_chat.id
    if topic is None:
        topic = 'Ask Me'

    if db['logins'].find_one(user=user_name) is None:
        db['logins'].insert({'user': user_name, 'user_id': user_id , today: topic})

    else:
        db_id = db['logins'].find_one(user=user_name)['id']
        db['logins'].upsert({'id': db_id, today: topic, 'user_id': user_id}, ['id'])

    send_message(f'You have log in as doing {topic}\n\n', bot, update)


def who_else_is_on_today(bot, update) -> None:
    today = get_date_str()
    list_of_dict = []
    max_len = 0
    for user_login in db['logins']:
        if user_login.get(today) is not None:
            max_len = max(max_len, len(user_login['user']))

    USER = 'User'
    PROJECT = 'Project'
    who_is_on_str = '{:<20s} | {:<34s}\n'.format(USER, PROJECT)
    count_users = 0
    keyboard = []

    for user_login in db['logins']:
        if user_login.get(today) is not None:
            count_users += 1
            user_name = user_login['user']
            user_id = user_login['user_id']
            project = user_login[today]
            list_of_dict.append({'User': '{0}'.format(user_name), 'Project': project})
            keyboard.append([InlineKeyboardButton(user_name), [InlineKeyboardButton(project)]])
            print('{:<20s} | {:<34s}\n'.format(user_name, project))
            who_is_on_str += '{:<20s} | {:<34s}\n'.format(user_name, project)

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(text='fooo',
                     chat_id=update.callback_query.message.chat_id,
                     message_id=update.callback_query.message.message_id,
                     reply_markup=reply_markup)
    who_is_on_str = '{}'.format(who_is_on_str)
    message = tabulate.tabulate(list_of_dict, headers='keys', tablefmt='simple')
    #message = "{}".format(message)
    print(who_is_on_str)
    #who_is_on_str += f'There are {count_users} logged on users'
    who_is_on_str = '`{}`'.format(who_is_on_str)


    bot.send_message(text=who_is_on_str,
                     chat_id=update.callback_query.message.chat_id,
                     message_id=update.callback_query.message.message_id,
                     parse_mode=ParseMode.MARKDOWN)


def button(bot, update):
    query = update.callback_query
    logger.info(f'User: {update.effective_user.name} has hit the <{query.data}> button')
    if query.data == UnregisterGroup:

        unregister_group(bot, update)

    elif query.data == RegisterGroup:

        register_group(bot, update)

    elif query.data == ListAllGroups:

        list_all_groups(bot, update)

    elif query.data == AdminInfo:

        admin_info(bot, update)

    elif query.data == LogOnToday:

        log_on_today(bot, update)

    elif query.data == WhoElsaIsOnToday:

        who_else_is_on_today(bot, update)

    elif query.data == Rules:
        send_rules(bot, update)

    elif query.data == MoreInfo:
        send_more_info(bot, update)

    else:
        bot.send_message(text="you have asked to: {}".format(str(query.data)),
                         chat_id=query.message.chat_id,
                         message_id=query.message.message_id)


# noinspection PyUnusedLocal
def help(bot, update):
    update.message.reply_text("Use /start to run this bot.")


# noinspection PyUnusedLocal,PyShadowingNames
def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def load_config(path_to_config_file: str) -> dict:
    with open(path_to_config_file) as fid:
        config_str = ''.join(fid.readlines())
        logger.info(f'loading config file: {path_to_config_file}:\n{config_str}')
        fid.seek(0)
        # noinspection PyShadowingNames
        config = yaml.load(fid)

        if config.get('bot_token') is None:
            raise KeyError(f'there is no "bot_token" key in {path_to_config_file}')

        if config['bot_token'] == 'add_bot_token':
            raise ValueError(f'you must have a bot_token')

        return config


def get_text_file(path_to_file: str) -> str:
    try:
        logger.info(f'going to open {path_to_file}')
        with open(path_to_file) as fid:
            return ''.join(fid.readlines())
    except FileNotFoundError:
        logger.info(f'there is no file at {path_to_file}')
        return 'there are no rules.'


def send_rules(bot, update):
    send_message(rules, bot, update)


def send_more_info(bot, update):
    send_message(more_info, bot, update)


def main():
    # noinspection PyGlobalUndefined
    global config
    global db
    global rules
    global more_info

    # set set constants
    path_to_config_file = 'boostskillabot_config.yaml'
    config = load_config(path_to_config_file=path_to_config_file)
    db = get_db(db_file_path=config['path_to_db_dir'])
    rules = get_text_file('textfiles/rules.txt')
    more_info = get_text_file('textfiles/moreinfo.txt')

    updater = Updater(token=config['bot_token'])
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()
