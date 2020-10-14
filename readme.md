# Bot kit

Создание общего контекста без кнофигурационного файла:

```python
from bot_kit.kit import BotContext
from bot_kit.db import DBManager
from sqlalchemy.ext.declarative import declarative_base

token: str = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
BaseModel = declarative_base()  # базовый класс для моделей БД
db_manager = DBManager('sqlite:///mybase.db', BaseModel)

bot_context = BotContext(token)
bot_context.set_db_manager(db_manager)
```

Создание общего контекста через конфигурационный файл:

```python
from bot_kit.kit import BotContext
from bot_kit.common import ConfigBot, INIConfig
from sqlalchemy.ext.declarative import declarative_base

BaseModel = declarative_base()  # базовый класс для моделей БД
config = ConfigBot(INIConfig('settings.ini'))
bot_context = BotContext.init_form_config(config, BaseModel)
```

Создание простого меню:

```python
from bot_kit.kit import BotCommand, MenuReplyKeyboard, ReplyKeyboardButton, ShowMenuButton
from bot_kit.db import DBManager, ModelManager
from aiogram import types

class FirstCommand(BotCommand):
    async def execute(self, tg_object: types.Message, *args, **kwargs):
        """
        self.db_manager - управление моделями БД
        self.bc - общий контекст
        self.bot - объект бота
        """
        user_manager: ModelManager = self.db_manager.manage(UserModel)
        current_user: UserModel = user_manager.one(chat_id=tg_object.from_user.id)
        await tg_object.answer('first command is finished')


@bot_context.register_menu(text='Меню настройки')
class ConfigMenu(MenuReplyKeyboard):
    COMMAND1 = ReplyKeyboardButton('Команда 1', FirstCommand)

    @classmethod
    def check(cls, tg_object: types.Message) -> bool:
        """Альтернативный метод для проверки вывода меню (если логика довольно сложная для декоратора)"""
        return tg_object.text == '/config'


@bot_context.register_menu(text='Приветствую', commands=['start'])
class MainMenu(MenuReplyKeyboard):
    FIRST_BUTTON = ReplyKeyboardButton('Команда 1', FirstCommand)
    SECOND_BUTTON = ReplyKeyboardButton('Команда 2', FirstCommand)
    SHOW_CONFIG_MENU = ShowMenuButton('Настройки', ConfigMenu)

    @classmethod
    async def before_show(cls, tg_object: types.Message, **kwargs):
        """
        Метод выполняемый перед показом меню
        cls.bc - общий контекст
        """
        db_manager: DBManager = cls.bc.get_db_manager()
        user_manager: ModelManager = db_manager.manage(UserModel)
        user: UserModel = user_manager.one(chat_id=tg_object.from_user.id)
        if not user:
            user_manager.save(UserModel(
                name=tg_object.from_user.first_name,
                last_name=tg_object.from_user.last_name,
                chat_id=tg_object.from_user.id,
            ))
```

Создание Inline меню:

```python
from bot_kit.kit import BotCommand, MenuInlineKeyboard, InlineButton
from aiogram import types


class SomeInlineCommand(BotCommand):
    async def execute(self, tg_object: types.CallbackQuery, *args, **kwargs):
        pass


@bot_context.register_menu(text='Что делаем?')
class ContextMenu(MenuInlineKeyboard):
    FIRST_BUTTON = InlineButton('Кнопка 1', 'some_command_btn', SomeInlineCommand())

    @classmethod
    def check(cls, tg_object: types.Message) -> bool:
        return True
```

Создание фоновой задачи выполняемой через определенный интервал:

```python

from bot_kit.kit import BotTask

@bot_context.register_async_timer(60)   # регистрируем выполнение функции каждую минуту
async def one_more_task():
    pass

class SimpleTask(BotTask):
    async def execute(self, *args, **kwargs):
        """
        self.db_manager - управление моделями БД
        self.bc - общий контекст
        self.bot - объект бота
        """
        pass

bot_context.add_task(SimpleTask(), 600) # запуск задачи раз в 10 минут
```

Запуск бота:

```python
bot_context.start_polling() # на текущий момент работает только через long pooling
```