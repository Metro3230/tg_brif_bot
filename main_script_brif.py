import chat_processing as chat
from pathlib import Path
from dotenv import load_dotenv
import os
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import telegramify_markdown #библитека преобразования markdown в телеграммный markdown_n2
from datetime import datetime
import logging
import asyncio
import shutil
import configparser
import json

script_dir = Path(__file__).parent  # Определяем путь к текущему скрипту
data_dir = script_dir / 'data'
log_file = data_dir / 'log.log'
env_file = data_dir / '.env'
data_zip = script_dir / 'data.zip'
admins_file = data_dir / 'admins.txt'
config_file_name = 'config_brif.ini'
config_file = data_dir / config_file_name

config = configparser.ConfigParser()  # настраиваем и читаем файл конфига
config.read(config_file)

load_dotenv(env_file)
tg_token = os.getenv('TG_TOKEN')    # читаем token ai c .env
bot = AsyncTeleBot(tg_token)  #токен тг

# -----настройка логгера------
#  логгер для моего скрипта
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  #  уровень логов для моего скрипта

#  обработчик для записи в файл
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)  # Уровень для файлового обработчика
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

#  логгер для сторонних библиотек
logging.getLogger().setLevel(logging.WARNING)


temp_spam_text = None


#-------------------------------------\/-сервисные команды-\/----------------------------------------------------

def user_admin(chat_id):   # #---проверка, админ ли пользователь (true если да, false если нет)-------------------------------------+
    with open(admins_file, 'r', encoding='utf-8') as file:
            for line in file:
                if str(chat_id) in line:        # проверка на админа
                    return True
    return False



async def handle_dw_data(chat_id): #---скачивание папки данных-------------------------------------+
    try:
        if user_admin(chat_id):
            shutil.make_archive(str(data_zip).replace('.zip', ''), 'zip', data_dir)
            with open(data_zip, 'rb') as file:
                await bot.send_document(chat_id, file)
            os.remove(data_zip)
            logger.info('data скачен пользователем ' + str(chat_id))
        else:
            text = telegramify_markdown.markdownify(config['mainconf']['noadmin_text']) #если не залогинен
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')  

    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка: {e}")
        logger.error(f"Ошибка скачивания данных - {e}")



async def handle_dw_config(chat_id): #---скачивание конфига-------------------------------------+
    try:
        if user_admin(chat_id):
            with open(config_file, 'rb') as file:
                await bot.send_document(chat_id, file)
            text = 'Аккуратно отредактируй файл и закинь обратно в этот чат, не меняя названия'
            text = telegramify_markdown.markdownify(text)      # чистим markdown
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')
            logger.info('config скачен пользователем ' + str(chat_id))
        else:
            text = telegramify_markdown.markdownify(config['mainconf']['noadmin_text']) #если не залогинен
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')  
        

    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка: {e}")
        logger.error(f"Ошибка скачивания данных - {e}")



async def handle_set_config(chat_id, msg_file_id): #---обновление конфига-------------------------------------+
    try:
        if user_admin(chat_id):
            file_path = (await bot.get_file(msg_file_id)).file_path
            downloaded_file = await bot.download_file(file_path)
            with open(config_file, 'wb') as new_file:            # Сохраняем файл на сервере, заменяя старый
                new_file.write(downloaded_file)
            config.read(config_file)
            await bot.send_message(chat_id, "Файл настроек успешно обновлён, надеюсь он адекватный и Вы ничего не сломали")
            logger.info(f'{config_file_name} заменён пользователем ' + str(chat_id))
        else:
            text = telegramify_markdown.markdownify(config['mainconf']['noadmin_text']) #если не залогинен
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')  

    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка: {e}")
        logger.error(f"Ошибка скачивания данных - {e}")



async def get_stat(chat_id): #---вывод статистики-------------------------------------+
    try:
        if user_admin(chat_id):
            active_users = chat.get_active_users()
            departed_users = chat.get_departed_users()
            text = (f'Активных пользователей: {active_users}\n'+
                    f'Удаливших чат с ботом: {departed_users}')
            text = telegramify_markdown.markdownify(text)      # чистим markdown
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')                  # Отправка сообщение с ссылкой
        else:
            text = telegramify_markdown.markdownify(config['mainconf']['noadmin_text']) #если не залогинен
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')  

    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка: {e}")
        logger.error(f"Ошибка скачивания данных - {e}")



async def handle_new_admin_pass(chat_id, message): #---------- обновление пароля --------------+
    try:
        old_pass = os.getenv('ADMIN_PASS')       # пишем в лог старый файл на всякий
        logger.info('попытка смены пароля: "' + old_pass + '" на новый...')

        command_parts = message.split(maxsplit=2)         # Разделяем текст команды на части

        if len(command_parts) < 3:         # Проверяем, что есть и пароль, и новый токен
            await bot.send_message(chat_id, "Ошибка: формат команды /new_admin_pass текущий_пароль новый_пароль")
            return
        
        input_password = command_parts[1]
        new_pass = command_parts[2]

        if input_password == os.getenv('ADMIN_PASS'):        # Проверяем правильность старого  пароля
            update_env_variable('ADMIN_PASS', new_pass)
            await bot.send_message(chat_id, "Сервисный пароль успешно обновлён!")
            logger.info('новый пароль установлен: ' + new_pass)
        else:
            await bot.send_message(chat_id, "Неверный пароль.")

    except Exception as e:
        logger.error(f"Произошла ошибка обновления сервисного пароля - {e}")
        await bot.send_message(chat_id, f"Произошла ошибка: {e}")



def update_env_variable(key, value): #---функция обновления параметра в файле .env-----------+

    if os.path.exists(env_file):    # Считаем текущие данные из .env файла
        with open(env_file, 'r') as file:
            lines = file.readlines()
    else:
        lines = []

    key_found = False    # Флаг, чтобы понять, был ли ключ найден
    new_lines = []

    for line in lines:    # Проходим по каждой строке и ищем ключ
        if line.startswith(f'{key}='):        # Если строка начинается с нужного ключа, заменяем его
            new_lines.append(f'{key}={value}\n')
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:    # Если ключ не найден, добавляем его в конец
        new_lines.append(f'{key}={value}\n')

    with open(env_file, 'w') as file:    # Записываем обновленные данные обратно в .env файл
        file.writelines(new_lines)
    
    load_dotenv(env_file, override=True)    # повторно загружаем значения из env с перезаписью



async def login(chat_id, message): #---логин в админы-------------------------------------+
    try:
        command_parts = message.split(maxsplit=2)         # Разделяем текст команды на части

        if len(command_parts) < 2:         # Проверяем, что есть и пароль
            await bot.send_message(chat_id, "Ошибка: формат команды /login пароль")
            return
        
        input_password = command_parts[1]
        
        if input_password == os.getenv('ADMIN_PASS'):        # Проверяем правильность пароля
            with open(admins_file, 'a+') as file:  # Открываем файл в режиме дозаписи (если нет, он создастся)
                file.seek(0)  # Перемещаем указатель на начало файла для чтения
                lines = file.readlines()
                if str(chat_id) + '\n' not in lines:  # Проверяем, есть ли уже такая строка в файле
                    file.write(str(chat_id) + '\n')  # Если строки нет, добавляем её в конец
                    text = telegramify_markdown.markdownify("Вы стали администратором. Теперь заполненные анекты будут приходить Вам. `/admin` - администрирование бота.") #если не залогинен
                    await bot.send_message(str(chat_id), text, parse_mode='MarkdownV2')
                    logging.info(str(chat_id) + ' подписался')
                else:
                    await bot.send_message(chat_id, "Вы уже подписаны")                    
        else:
            await bot.send_message(chat_id, "Неверный пароль.")

    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка: {e}")
        logger.error(f"Ошибка логина в админы - {e}")
        

async def unlogin(chat_id): #---разлогин из админов-------------------------------------+
    try:        
        if user_admin(chat_id):
            with open(admins_file, 'r') as file:    # Читаем содержимое файла
                lines = file.readlines()
            with open(admins_file, 'w') as file:    # Отфильтровываем строки, которые не совпадают с ids
                for line in lines:
                    if line.strip() != str(chat_id):
                        file.write(line)                    
            await bot.send_message(chat_id, "Вы отписались от заполненых анкет.")
        else:
            text = telegramify_markdown.markdownify("Вы не админ.") #если не залогинен
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')  
        
    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка: {e}")
        logger.error(f"Ошибка разлогина из админов - {e}")
        
#----------------------------------------------------------------------------------------------------------

#----------------------------------------------\/-СПАМ-\/---------------------------------------------------
        
async def new_spam(chat_id, message): #---создание СПАМ рассылки ------------------------------------+
    try:
        if user_admin(chat_id):
            text = ('*Следующим сообщением отпарвь то, что хочешь отправить всем пользователям БОТа*\n' +
                    '* к сообщению может быть прикреплена ссылка, 1 картинка, 1 документ\n' +
                    '* можно использовать форматирование\n' +
                    '* опросы и викторины *не* поддерживаются\n')
            text = telegramify_markdown.markdownify(text)      # чистим markdown
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')
            chat.spam_flag(chat_id, 1)    #присваиваем флагу ожидания сообщения со спам рассылкой статус 1 для этого пользователя
        else:
            text = telegramify_markdown.markdownify(config['mainconf']['noadmin_text']) #если не залогинен
            await bot.send_message(chat_id, text, parse_mode='MarkdownV2')         

    except Exception as e:
        logger.error(f"Ошибка создания СПАМ рассылки - {e}")


async def spam_processing(chat_id, message_id, message_text): #--обработка СПАМ рассылки-------------+
    global temp_spam_text
    try:
        if (message_text == "Отпрaвить всeм"):
            await bot.send_message(chat_id, "Идёт рассылка...\nничего не отправляйте в чат", reply_markup=types.ReplyKeyboardRemove())
            actual_users = chat.get_actual_ids() #получаем список актуальных пользователей
            await sent_spam(actual_users, chat_id, message_id-2) #рассылаем, копируя пред-предидущее сообщение
            temp_spam_text = None   # удаляем временный текст рассылки
            chat.spam_flag(chat_id, 0)   #опускание флага

        elif (message_text == "Oтменa"):   
            await bot.send_message(chat_id,"Рассылка отменена",reply_markup=types.ReplyKeyboardRemove())
            temp_spam_text = None   # удаляем временный текст рассылки
            chat.spam_flag(chat_id, 0)   #опускание флага

        else:
            await bot.copy_message(   #отправка сообщения на проверку самому себе
                chat_id=chat_id,  # Кому отправляем
                from_chat_id=chat_id,  # Откуда берем сообщение
                message_id=message_id  # ID сообщения для копирования
            )
            temp_spam_text = message_text
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)    # Создаем объект клавиатуры
            markup_1 = types.KeyboardButton("Отпрaвить всeм")     # Добавляем кнопки
            markup_2 = types.KeyboardButton("Oтменa")
            keyboard.row(markup_1)
            keyboard.row(markup_2)
            await bot.send_message(chat_id, "⬆ Так будет выглядеть рассылка в чатах пользователей.\n" +
                                            "Если что-то не так, пришли новое сообщение. Если всё хорошо или передумал, воспользуйся кнопками ⬇", reply_markup=keyboard)       # Отправляем сообщение с клавиатурой
    except Exception as e:
        logger.error(f"Ошибка обработки СПАМ рассылки - {e}")


async def sent_spam(users, chat_id, message_id):#---рассылка спама (users кому слать (массив), chat_id из какого чата, message_id ид сообщения)---+
    try:
        luck_sends = 0 #счётчик удачных отпрвлений
        interval = 1 / int(config['mainconf']['requests_per_second'])
        next_request_time = asyncio.get_event_loop().time()
        i = 0 
        
        while i < len(users):           # цикл по всем пользователям
            current_time = asyncio.get_event_loop().time()
            if current_time >= next_request_time:
                try:
                    await bot.copy_message(     # ---рассылаем ---
                        chat_id=users[i],  # Кому отправляем
                        from_chat_id=chat_id,  # Откуда берем сообщение
                        message_id=message_id  # ID сообщения для копирования
                    )
                    luck_sends += 1
                except Exception as e: # в архив, если ошибка отправки от сервера тг = 403 или 400 (отписался или неизвестен вообще)
                    if(e.error_code == 403 or e.error_code == 400):
                        try:
                            chat.arch_chat(users[i])  #пользователя в архив
                        except Exception as e:
                            logger.error(f"Ошибка добавления чата {users[i]} в архив - {e}")
                
                i += 1  # Переход к следующему получателю
                next_request_time += interval
            else:                                              # игнорим отправку, если слишком быстро отправляем
                await asyncio.sleep(next_request_time - current_time)
            
        await bot.send_message(chat_id, f"Отправлено {luck_sends} пользователям.\n")
        
    except Exception as e:
        logger.error(f"Ошибка рассылки спама - {e}")
        await bot.send_message(chat_id, f"Ошибка рассылки - {e}. Сообщите разработчику.")


#----------------------------------------------------------------------------------------------------------


# -----------------------------------Основной обработчик всех сообщений------------------------------------

@bot.message_handler(content_types=['web_app_data']) #---обработчик данных из веб-апп---
async def answer(webAppMes):
    try:
        chat_id = webAppMes.chat.id
        if int(chat.get_brif_count_all(chat_id)) < int(config['mainconf']['brif_limit']):  # если пользователь не дудосит 
            
            
            tg_first_name = webAppMes.from_user.first_name
            tg_last_name = webAppMes.from_user.last_name
            tg_username = webAppMes.from_user.username
            
            tg_first_name = "" if tg_first_name is None else tg_first_name #проверка на пусто
            tg_last_name = "" if tg_last_name is None else tg_last_name
            tg_username = "" if tg_username is None else tg_username

            brif = json.loads(webAppMes.web_app_data.data)

            hist = chat.get_last_messages_str(chat_id)  
            
            text = (f"Пользователь {tg_first_name} {tg_last_name} @{tg_username}\n" +
                    f"Написал:\n" +
                    f"{hist}\n\n" +
                    "И запросил ОС:\n")
            for key, value in brif.items():
                text += f"{key} - {value}\n"    
                
            err_text = ('Ошибка отправки, бот не настроен.\n' +
                        'Если Вы администратор - введите команду `/login пароль`')
            err_text = telegramify_markdown.markdownify(err_text)      # чистим markdown
                
            #---рассылка админам при заполнении анкеты---
            # Проверка на существование файла
            if not os.path.exists(admins_file):
                await bot.send_message(chat_id, err_text, parse_mode='MarkdownV2')  #  при отсутствии файла с id админов
            else:
                with open(admins_file, 'r') as f:
                    admin_lines = f.readlines()

                # Проверка на пустоту файла
                if not admin_lines:
                    await bot.send_message(chat_id, err_text, parse_mode='MarkdownV2')  #  при пустом файле с id админов
                else:
                    #отправка с разделением длинных сообщений 
                    for admin_id in admin_lines:
                        admin_id = admin_id.strip()
                        if admin_id != '':
                            max_msg_length = config['mainconf']['max_msg_length']
                            text_lines = text.split('\n')
                            current_message = ''
                            for line in text_lines:
                                if len(current_message) + len(line) + 1 > int(max_msg_length):
                                    await bot.send_message(admin_id, current_message)
                                    current_message = line
                                else:
                                    if current_message:
                                        current_message += '\n' + line
                                    else:
                                        current_message = line
                            if current_message:
                                await bot.send_message(admin_id, current_message)   
                    chat.remove_brif_count_and_context(chat_id) #чистим историю сообщений и плюсуем бриф в счётчик после отправки 
        else:
            text = 'Вы привысили лимит заполнений анкеты. ☹️ Попробуйте связаться другим способом.'
            await bot.send_message(chat_id, text)
        
    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка: {e}, свяжитесь с {config['mainconf']['admin_link']}")
        logger.error(f"Ошибка обработчика данных из веб-апп - {e}")

        
        
@bot.message_handler(content_types=['text', 'photo', 'document', 'video', 'voice', 'audio', 'contact', 'location', 'sticker', 'animation']) #---обработчик любых сообщений---
async def handle_message(message):
    try:
        message_text = message.text if message.text is not None else message.caption #текст или описание = текст
        chat_id = message.chat.id
        username = message.from_user.username
        message_id = message.message_id

        if (message_text):
            if message_text.startswith('/'): #обработка сервисных команд----+-+
                if message_text == "/start":
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)    # Создаем объект клавиатуры                
                    webApp = types.WebAppInfo(config['mainconf']['webapp_url']) #создаем webappinfo - формат хранения url
                    markup_1 = types.KeyboardButton(text=config['mainconf']['bttn_text'], web_app=webApp) #создаем кнопку типа webapp 
                    keyboard.row(markup_1)
                    await bot.send_message(chat_id, config['mainconf']['start_message'], reply_markup=keyboard)       # Отправляем сообщение с клавиатурой
                    
                elif message_text == "/service":
                    if user_admin(chat_id):
                        text = ('`/admin` - администрирование\n' +
                                '`/dw_data пароль` - скачать папку с данными\n')
                        text = telegramify_markdown.markdownify(text)      # чистим markdown
                        await bot.send_message(chat_id, text, parse_mode='MarkdownV2')   
                    else:
                        text = telegramify_markdown.markdownify(config['mainconf']['noadmin_text']) #если не залогинен
                        await bot.send_message(chat_id, text, parse_mode='MarkdownV2')  
                    
                elif message_text == "/admin":
                    if user_admin(chat_id):
                        text = ('/spam - рассылка всем пользователям бота\n' +
                                '/stat - статистика\n\n' +
                                '/dw_config - скачать текущий файл настроек\n' +
                                '`/new_admin_pass старый_пароль новый_пароль` - замена сервисного пароля\n' +
                                '/unlogin - разлогинится (и не получать заполненные формы)\n')
                        text = telegramify_markdown.markdownify(text)      # чистим markdown
                        await bot.send_message(chat_id, text, parse_mode='MarkdownV2')
                    else: 
                        text = telegramify_markdown.markdownify(config['mainconf']['noadmin_text']) #если не залогинен
                        await bot.send_message(chat_id, text, parse_mode='MarkdownV2')  
                        
                    
                elif message_text == "/dw_data":
                    await handle_dw_data(chat_id)
                    
                elif message_text == "/spam":
                    await new_spam(chat_id, message_text)         
                    
                elif message_text.startswith('/new_admin_pass'):
                    await handle_new_admin_pass(chat_id, message_text)
                    
                elif message_text == "/stat":
                    await get_stat(chat_id)
                    
                elif message_text == "/dw_config":
                    await handle_dw_config(chat_id)
                    
                elif message_text.startswith('/login'):
                    await login(chat_id, message_text) 
                    
                elif message_text == "/unlogin":
                    await unlogin(chat_id)            


            else:                            #обработка текста (не команд)
                
                if chat.spam_flag(chat_id):         #если у пользователя поднят флаг ожидания спам сообщения                
                    await spam_processing(chat_id, message_id, message_text)     
                    
                elif chat.get_msg_count_all(chat_id) >= int(config['mainconf']['msgs_limit_all']): # проверка на лимит сообщений всего (защита от спама)
                    await bot.delete_message(chat_id, message_id) #просто удаляем сообщение
                    
                elif (chat.get_msg_count(chat_id) + 1) >= int(config['mainconf']['msgs_limit']): # проверка на количество сообщений (каждые которые отправлять кнопку)
                    chat.save_message_to_json(chat_id=chat_id, role="user", sender_name=username, message=message_text)   #записываем текст сообщения от ЮЗЕРА в историю сообщений
                    # last_messages = chat.get_last_messages(chat_id)
                    chat.remove_limit(chat_id)   #вызываем чистку лимита для чата
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)    # Создаем объект клавиатуры                
                    webApp = types.WebAppInfo(url=config['mainconf']['webapp_url']) #создаем webappinfo - формат хранения url
                    markup_1 = types.KeyboardButton(text=config['mainconf']['bttn_text'], web_app=webApp) #создаем кнопку типа webapp 
                    keyboard.row(markup_1)                
                    await bot.send_message(chat_id, config['mainconf']['limit_msg'], reply_markup=keyboard)       # Отправляем сообщение с клавиатурой
                    
                else:                              #просто запись вопроса в архив вопросов
                    chat.save_message_to_json(chat_id=chat_id, role="user", sender_name=username, message=message_text)   #записываем текст сообщения от ЮЗЕРА в историю сообщений    
                    
                    
        elif message.document.file_name == config_file_name:  # если пришел файл с настройками
            logger.info("ok")                    
            await handle_set_config(chat_id, message.document.file_id) 
                    
    except Exception as e:
        await bot.send_message(chat_id, f"Произошла ошибка: {e}, свяжитесь с {config['mainconf']['admin_link']}")
        logger.error(f"Ошибка обработчика любых сообщений - {e}")





#-------------------------------------------------------------------------------------------------------------



logger.info(f"Скрипт запущен")

# Запуск бота
async def main():
    await bot.polling()
    

if __name__ == "__main__":
    asyncio.run(main())







# ПЛАН - 
#  доделать рассылку  ok
#  переносить чаты в архив ,если не удалось сделать на них рассылку ok
#  вопрос чату без его роли  ok  
#  кнопки при приветствии
#  
# 
# 
#  биллинг токенов для каждого и суммарный
# статистика (кол-во пользователей, кол-во сообщений всего , кол-во сообщений сегодня...)  хз надо ли
# отправлять в архив после 2 неудачных попыток отправки
#  ???
# Профит
