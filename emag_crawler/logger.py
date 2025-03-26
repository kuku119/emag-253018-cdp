"""日志"""

from pathlib import Path
from sys import stderr

from loguru import logger
from scraper_utils.utils.time_util import now_str

_cwd = Path.cwd()

logger.remove()
_log_dir = _cwd / 'logs/'
_log_dir.mkdir(exist_ok=True)
_log_file = _log_dir / f'{now_str('%Y_%m_%d-%H_%M_%S')}.log'
logger.add(
    stderr,
    format=(
        '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
        '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] >>> '
        '<level>{message}</level>'
    ),
    filter=lambda record: len(record['extra']) == 0,
)
logger.add(
    _log_file,
    format=(
        '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
        '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] >>> '
        '<level>{message}</level>'
    ),
    filter=lambda record: len(record['extra']) == 0,
    enqueue=True,
)
logger.add(
    stderr,
    format=(
        '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
        '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] '
        '[<green>{extra[category]}</green>] >>> '
        '<level>{message}</level>'
    ),
    filter=lambda record: 'category' in record['extra'],
)
logger.add(
    _log_file,
    format=(
        '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
        '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] '
        '[<green>{extra[category]}</green>] >>> '
        '<level>{message}</level>'
    ),
    filter=lambda record: 'category' in record['extra'],
    enqueue=True,
)
