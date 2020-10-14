from aiogram import types, Dispatcher, Bot, executor
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Tuple, Union, Optional, Dict
from .db import DBManager
from .common import ConfigBot, BotException, TaskQueue
import asyncio
import aiohttp
import logging


class BaseBotContext(ABC):
    def get_loop(self) -> asyncio.AbstractEventLoop:
        return self.loop

    def init_task_queue(self) -> TaskQueue:
        return TaskQueue(self.loop)

    def get_db_manager(self) -> DBManager:
        return self.db_manager

    def get_bot(self):
        return self.bot

    def get_dispatcher(self) -> Dispatcher:
        return self.dp


class Registrator(ABC):
    @abstractmethod
    def register(self, dp: Dispatcher):
        pass


class BotTask(ABC):
    def __init__(self):
        self.bc: BaseBotContext = None
        self.bot: Bot = None
        self.db_manager: DBManager = None

    def register(self, bc: BaseBotContext):
        self.bc: BaseBotContext = bc
        self.bot: Bot = bc.get_bot()
        self.db_manager: DBManager = bc.get_db_manager()

    @abstractmethod
    async def execute(self, *args, **kwargs):
        pass

    async def __call__(self, *args, **kwargs):
        await self.execute(*args, **kwargs)


class BotCommand(Registrator):
    def __init__(self):
        self.bc: BaseBotContext = None
        self.bot: Bot = None
        self.db_manager: DBManager = None

    @abstractmethod
    async def execute(self, tg_object: types.base.TelegramObject, *args, **kwargs):
        pass

    def register(self, bc: BaseBotContext):
        self.bc = bc
        self.bot = bc.get_bot()
        self.db_manager: DBManager = bc.get_db_manager()

    async def __call__(self, *args, **kwargs):
        await self.command.execute(*args, **kwargs)


class BaseButton(Registrator):
    def __init__(self, command: BotCommand):
        self.bc: BaseBotContext = None
        self.command: BotCommand = command

    @abstractmethod
    def get_button(self, *args, **kwargs) -> types.base.TelegramObject:
        """Кнопка для вывода на клавиатуре"""
        pass

    @abstractmethod
    def check_value(self, tg_object: types.base.TelegramObject):
        """Проверка обработчика события"""
        pass

    @abstractmethod
    def __str__(self):
        pass

    def register(self, bc: BaseBotContext):
        self.bc = bc
        if isinstance(self.command, BotCommand):
            self.command.register(self.bc)

    async def __call__(self, *args, **kwargs):
        """Вызов команды"""
        if isinstance(self.command, BotCommand):
            await self.command.execute(*args, **kwargs)

    def set_command(self, command: BotCommand):
        """Задаем новую команду для выполения"""
        self.command = command
        if isinstance(self.bc, BaseBotContext):
            self.command.register(self.bc)


class ReplyKeyboardButton(BaseButton):
    def __init__(self, text: str, command: BotCommand):
        self.value = text
        self.command = command

    def register(self, bc: BaseBotContext):
        super().register(bc)
        bc.get_dispatcher().register_message_handler(self, self.check_value)

    def get_button(self, *args, **kwargs) -> types.KeyboardButton:
        return types.KeyboardButton(text=self.value, *args, **kwargs)

    def check_value(self, msg: types.Message):
        return msg.text == self.value

    def __str__(self):
        return self.value


class InlineButton(BaseButton):
    def __init__(self, text: str, data, command: BotCommand):
        self.value = text
        self.data = data
        self.command = command

    def register(self, bc: BaseBotContext):
        super().register(bc)
        bc.get_dispatcher().register_callback_query_handler(self, self.check_value)

    def get_button(self) -> types.InlineKeyboardButton:
        return types.InlineKeyboardButton(text=self.value, callback_data=self.data)

    def check_value(self, query: types.CallbackQuery):
        return query.data == self.data

    def __str__(self):
        return self.data


class Menu(Enum):
    @classmethod
    async def show(cls, tg_object: types.base.TelegramObject, text: str = None, **kwargs):
        """Показать клавиатуру"""
        await cls.before_show(tg_object=tg_object, **kwargs)

    @classmethod
    async def before_show(cls, tg_object: types.base.TelegramObject, **kwargs):
        pass

    @classmethod
    def register(cls, bc: BaseBotContext, *custom_filters, text='', row_width: int = 2, commands=None,
                 regexp=None, content_types=None, state=None, run_task=None, **kwargs):
        """Регистрируем обработчик для вывода клавиатуры по заданному событию"""
        dp: Dispatcher = bc.get_dispatcher()
        if not custom_filters and commands is None and regexp is None:
            dp.register_message_handler(cls.show, cls.check, commands=commands, regexp=regexp,
                                        content_types=content_types, state=state, run_task=run_task, **kwargs)
        else:
            dp.register_message_handler(cls.show, *custom_filters, commands=commands, regexp=regexp,
                                        content_types=content_types, state=state, run_task=run_task, **kwargs)
        cls.text = text
        cls.row_width = row_width
        cls.bc: BaseBotContext = bc
        for button in cls._list():
            if isinstance(button.value, Registrator):
                button.value.register(bc)

    @classmethod
    def _list(cls) -> list:
        """Список кнопок"""
        for _, item in cls.__dict__.items():
            if isinstance(item, Menu):
                yield item

    @classmethod
    @abstractmethod
    def init_empty_keyboard(cls, *args, **kwargs) -> Union[types.ReplyKeyboardMarkup, types.InlineKeyboardMarkup]:
        """Создаем пустую клавиатуру"""
        pass

    @classmethod
    def get_keyboard(cls, row_width: int = 2) -> Union[types.ReplyKeyboardMarkup, types.InlineKeyboardMarkup]:
        """Объект клавиатуры для передачи в сообщение"""
        buttons = [item.value.get_button() for item in cls._list()]
        keyboard = cls.init_empty_keyboard()
        rows_count = (len(buttons) // (row_width * -1) * -1)
        for i in range(rows_count):
            start = i * row_width
            limit = (i + 1) * row_width
            keyboard.row(*buttons[start:limit])

        return keyboard

    def __str__(self):
        return str(self.value)

    def __eq__(self, value):
        return self is value or self.value == value

    @classmethod
    def check(cls, tg_object: types.base.TelegramObject) -> bool:
        return False

    @classmethod
    def has_value(cls, value) -> bool:
        for item in cls._list():
            if item.value == value:
                return True

        return False


class MenuReplyKeyboard(Menu):
    """Reply клавиатура"""

    @classmethod
    async def show(cls, tg_object: types.Message, text: str = None, **kwargs):
        await super().show(tg_object=tg_object, **kwargs)
        await tg_object.answer(text or cls.text, reply_markup=cls.get_keyboard(cls.row_width))

    @classmethod
    def init_empty_keyboard(cls, *args, **kwargs) -> types.ReplyKeyboardMarkup:
        return types.ReplyKeyboardMarkup(*args, resize_keyboard=True, **kwargs)


class MenuInlineKeyboard(Menu):
    """Inline клавиатура"""

    @classmethod
    async def show(cls, tg_object: types.Message, text: str = None, **kwargs):
        await super().show(tg_object=tg_object, **kwargs)
        await tg_object.reply(text or cls.text, reply_markup=cls.get_keyboard(cls.row_width))

    @classmethod
    def init_empty_keyboard(cls, *args, **kwargs) -> types.InlineKeyboardMarkup:
        return types.InlineKeyboardMarkup(*args, **kwargs)


class ShowMenuButton(BaseButton):
    def __init__(self, text: str, menu: Menu, text_menu: str):
        super().__init__(None)
        self.value: str = text
        self.menu: Menu = menu
        self.text_menu: str = text_menu

    def register(self, bc: BaseBotContext):
        self.bc = bc
        super().register(bc)
        bc.get_dispatcher().register_message_handler(self, self.check_value)

    def get_button(self, *args, **kwargs) -> types.KeyboardButton:
        return types.KeyboardButton(text=self.value, *args, **kwargs)

    def check_value(self, msg: types.Message):
        return msg.text == self.value

    def __str__(self):
        return self.value

    async def __call__(self, *args, **kwargs):
        menu = self.menu
        if not isinstance(menu, Menu):
            menu = self.bc.menu_list.get(self.menu.__name__)
            if not menu:
                return

        await menu.show(*args, text=self.text_menu, **kwargs)


class BotContext(BaseBotContext):
    def __init__(
            self,
            token: str,
            loop: Optional[Union[asyncio.BaseEventLoop, asyncio.AbstractEventLoop]] = None,
            connections_limit: Optional[int] = None,
            proxy: Optional[str] = None,
            proxy_auth: Optional[aiohttp.BasicAuth] = None,
            validate_token: Optional[bool] = True,
            parse_mode: Optional[str] = None,
            timeout: Optional[Union[int, float, aiohttp.ClientTimeout]] = None
    ):
        self.bot: Bot = Bot(
            token,
            loop=loop,
            connections_limit=connections_limit,
            proxy=proxy,
            proxy_auth=proxy_auth,
            validate_token=validate_token,
            parse_mode=parse_mode,
            timeout=timeout
        )
        self.dp: Dispatcher = Dispatcher(self.bot)
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.task_list: List[Tuple[BotTask, float]] = []
        self.menu_list: Dict[str, Menu] = {}
        self.db_manager: DBManager = None

    @classmethod
    def init_form_config(cls, config: ConfigBot, base_model_class=None):
        token = config.get_token()
        if not token:
            raise BotException('Не найден токен telegram bot')
        bc: BotContext = cls(token)

        if config.get_db_connect():
            db_connect = DBManager(config.get_db_connect(), base_model_class)
            db_connect.init_models()
            bc.set_db_manager(db_connect)

        logging_config = config.get_logging()
        if not logging_config.is_empty():
            print(logging_config.get_format())
            logging.basicConfig(
                filename=logging_config.get_path(),
                filemode='w',
                format=logging_config.get_format(),
                level=logging_config.get_level())

        return bc

    def register_menu(self, *custom_filters, text='', row_width: int = 2, commands=None,
                      regexp=None, content_types=None, state=None, run_task=None, **kwargs):
        """Регистрация меню"""

        def __(cls: Menu):
            cls.register(self, *custom_filters, text=text, row_width=row_width, commands=commands,
                         regexp=regexp, content_types=content_types, state=state, run_task=run_task, **kwargs)
            self.menu_list[cls.__name__] = cls
            return cls

        return __

    def set_db_manager(self, db_manager: DBManager):
        self.db_manager: DBManager = db_manager

    def register_async_timer(self, interval: float):
        """Регистрация периодических задач"""

        def decorator(func):
            self.task_list.append((func, interval))

            def wrapper(*args, **kwargs):
                asyncio.ensure_future(func(*args, **kwargs), loop=self.loop)
                self.loop.call_later(interval, wrapper, *args, **kwargs)

            return wrapper

        return decorator

    def __run_task(self, task, interval, *args, **kwargs):
        """Запуск задачи"""
        asyncio.ensure_future(task(*args, **kwargs), loop=self.loop)
        self.loop.call_later(interval, self.__run_task, task, interval, *args, **kwargs)

    def add_task(self, task: BotTask, interval: float):
        """Добавляем периодическое задание"""
        task.register(self)
        self.register_async_timer(interval)(task)

    def start_polling(self):
        """Запускаем бота"""
        for task, interval in self.task_list:
            self.__run_task(task, interval)
        executor.start_polling(self.dp, loop=self.loop)
