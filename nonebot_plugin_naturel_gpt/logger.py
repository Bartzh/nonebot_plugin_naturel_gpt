#import nonebot
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loguru import Record


def __path(record: "Record"):
    record["name"] = "NG聊天"

class logger:
    def info(t):
        print('[Info]:'+t)

    def warning(t):
        print('[Warning]:'+t)

    def error(t):
        print('[Error]:'+t)
#logger = nonebot.logger.bind()
#logger = logger.patch(__path)
