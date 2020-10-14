from operator import attrgetter
from typing import List, TypeVar, Generator
from abc import ABC, abstractmethod
from configparser import ConfigParser, NoOptionError
from aiogram import types, Bot
from asyncio import AbstractEventLoop, Task, wait

_T = TypeVar('_T')


class BotMessage(ABC):
    @abstractmethod
    def __str__(self) -> str:
        pass


class TaskQueue:
    def __init__(self, loop: AbstractEventLoop):
        self.loop: AbstractEventLoop = loop
        self.task_list: List[Task] = []

    def add(self, task):
        self.task_list.append(self.loop.create_task(task))

    def execute(self):
        return wait(self.task_list)

    def get_result(self) -> Generator:
        done, _ = wait(self.task_list)
        for item in done:
            yield item.result()


class BotMessageList(list):
    def __init__(self, *args, mode: str = None, split: str = None, loop: AbstractEventLoop = None):
        super().__init__(*args)
        self.block_size = 1
        self.mode = mode or 'markdown'
        self.split = split or '\n'
        self.loop = loop

    # def append(self, __object: _T) -> None:
    #     if isinstance(__object, BotMessage):
    #         super(BotMessageList, self).append(__object)

    def get_block_list(self) -> Generator:
        item_left: int = self.block_size
        message_list: list = []
        for item in self:
            if item_left <= 0:
                data: str = self.split.join(map(str, message_list))
                message_list: list = []
                item_left: int = self.block_size
                yield data
                continue

            message_list.append(item)
            item_left -= 1

        if len(message_list) > 0:
            yield self.split.join(map(str, message_list))

    async def answer_message(self, message: types.Message) -> List[types.Message]:
        if isinstance(self.loop, AbstractEventLoop):
            task_queue: TaskQueue = TaskQueue(self.loop)
            for item in self.get_block_list():
                task_queue.add(
                    message.answer(item, parse_mode=self.mode, disable_web_page_preview=True)
                )

            return sorted(list(task_queue.get_result()), key=attrgetter('message_id'))

        message_list: List[types.Message] = []
        for item in self.get_block_list():
            message = await message.answer(item, parse_mode=self.mode, disable_web_page_preview=True)
            message_list.append(message)

        return message_list

    async def send_user(self, bot: Bot, chat_id: int) -> List[types.Message]:
        if isinstance(self.loop, AbstractEventLoop):
            task_queue: TaskQueue = TaskQueue(self.loop)
            for item in self.get_block_list():
                task_queue.add(
                    bot.send_message(chat_id, item, parse_mode=self.mode, disable_web_page_preview=True)
                )

            return sorted(list(task_queue.get_result()), key=attrgetter('message_id'))

        message_list: List[types.Message] = []
        for item in self.get_block_list():
            message = await bot.send_message(chat_id, item, parse_mode=self.mode, disable_web_page_preview=True)
            message_list.append(message)

        return message_list


class BaseConfig(ABC):
    def __init__(self, config_path: str):
        self.config_path: str = config_path
        self.profile_name: str = 'default'
        self.load(config_path)

    def set_profile(self, profile_name: str):
        self.profile_name = profile_name

    @abstractmethod
    def load(self, config_path: str) -> dict:
        pass

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def set_param(self, key: str, value, **kwargs):
        pass

    @abstractmethod
    def get_param(self, key: str, **kwargs):
        pass


class INIConfig(BaseConfig):
    def __init__(self, config_path: str):
        self.config: ConfigParser = ConfigParser()
        super().__init__(config_path)

    def load(self, config_path: str):
        self.config.read(self.config_path)

    def save(self):
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def set_param(self, key: str, value, section: str = ''):
        if section == '':
            section = self.profile_name
        else:
            section = "%s_%s" % (self.profile_name, section)

        self.config.set(section, key, value)

    def get_param(self, key: str, section: str = ''):
        if section == '':
            section = self.profile_name
        else:
            section = "%s_%s" % (self.profile_name, section)

        try:
            return self.config.get(section, key, raw=True)
        except NoOptionError:
            return None


class LoggingConfig:
    def __init__(self, config: BaseConfig):
        self.config = config
        self.section: str = 'logging'

    def is_empty(self) -> bool:
        return bool(self.config.get_param('use_logging')) is False

    def get_path(self) -> str:
        return self.config.get_param('path', section=self.section)

    def get_format(self) -> str:
        return self.config.get_param('format', section=self.section)

    def get_level(self) -> int:
        return int(self.config.get_param('level', section=self.section))


class ConfigBot:
    def __init__(self, config: BaseConfig):
        self.config = config

    def get_token(self) -> str:
        return self.config.get_param('token')

    def set_token(self, token: str):
        self.config.set_param('token', token)

    def get_db_connect(self) -> str:
        return self.config.get_param('db')

    def set_db_connect(self, db_connect: str):
        self.config.set_param('db', db_connect)

    def get_logging(self) -> LoggingConfig:
        return LoggingConfig(self.config)

    def save(self):
        self.config.save()


class BotException(Exception):
    pass