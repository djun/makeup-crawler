# coding=utf-8

import logging.config
from logging.handlers import RotatingFileHandler
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG
import os
import json


# 2018-5-28：优化get_logger()获取同个logger并行使用的情况

# 2018-3-27：去掉外层的Utils类，使之能import后直接用

# 2018-3-13：增加可选log level
def get_logger(name=None, stream_log_level=INFO, file_log_level=DEBUG, encoding='utf-8', log_dir=''):
    """获取日志记录器
    参数：
        -

    返回值：
        -

    错误反馈：
        -
    """

    logger = getLogger(name)
    # if not logger.hasHandlers():
    if len(logger.handlers) <= 0:
        stream_handler = StreamHandler()
        stream_handler.setLevel(stream_log_level)
        log_path = os.path.abspath(os.path.join(log_dir, r'log.txt' if name is None else r'log_' + name + '.txt'))
        rotate_handler = RotatingFileHandler(log_path, 'a', maxBytes=1024 * 1024 * 10, backupCount=99,
                                             encoding=encoding)
        rotate_handler.setLevel(file_log_level)

        datefmt_str = '%Y-%m-%d %H:%M:%S'
        format_str = '[%(asctime)s][%(levelname)s][%(filename)s - %(lineno)d]%(message)s'
        format_simple_str = '[%(asctime)s][%(levelname)s]%(message)s'
        formatter = Formatter(format_str, datefmt_str)
        formatter_simple = Formatter(format_simple_str, datefmt_str)
        rotate_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter_simple)

        logger.addHandler(stream_handler)
        logger.addHandler(rotate_handler)
        logger.setLevel(DEBUG)

    return logger


def get_logger2(name=None, stream_log_level=INFO, file_log_level=DEBUG, encoding='utf-8'):
    log_path = os.path.abspath(r'log.txt' if name is None else r'log_'+name+'.txt')
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'verbose': {
                'format': "[%(asctime)s][%(levelname)s][%(filename)s - %(lineno)d]%(message)s",
                'datefmt': "%Y-%m-%d %H:%M:%S"
            },
            'simple': {
                'format': '[%(asctime)s][%(levelname)s] %(message)s'
            },
        },
        'handlers': {
            # 'null': {
            #     'level': 'DEBUG',
            #     'class': 'logging.NullHandler',
            # },
            'console': {
                'level': stream_log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'verbose'
            },
            'file': {
                'level': file_log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'maxBytes': 1024 * 1024 * 10,
                'backupCount': 99,
                # If delay is true,
                # then file opening is deferred until the first call to emit().
                'delay': False,
                'filename': log_path,
                'formatter': 'verbose',
                'encoding': encoding
            }
        },
        'loggers': {
            '': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
            },
        }
    })

    return getLogger(name)


def load_config(file_name, encoding='utf-8'):
    """从文件加载配置信息（json，默认约定根为dict）
    参数：
        -

    返回值：
        -

    错误反馈：
        -
    """

    with open(file_name, 'r', encoding=encoding) as fp:
        config = json.load(fp)
    if isinstance(config, dict):
        return config
    else:
        return dict()


def save_config(config, file_name, encoding='utf-8'):
    """保存配置信息到文件（json，默认约定根为dict）
    参数：
        -

    返回值：
        -

    错误反馈：
        -
    """

    if isinstance(config, dict):
        with open(file_name, 'w+', encoding=encoding) as fp:
            # 2018-3-26：新增sort_keys=True、indent=2
            json.dump(config, fp, ensure_ascii=False, sort_keys=True, indent=2)
