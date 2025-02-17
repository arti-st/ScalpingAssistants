import logging
import colorlog
import os

def setup_logger(path):
    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Global logger level

    # Check if the logger already has handlers to prevent adding duplicates
    if not logger.hasHandlers():
        path_to_log = os.path.join(path, '.log')

        # Create handlers
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(path_to_log, encoding='utf-8')

        # Set levels for handlers
        console_handler.setLevel(logging.DEBUG)
        file_handler.setLevel(logging.DEBUG)

        LIGHT_GRAY = '\033[38;5;245m'
        # Create formatters and add them to handlers
        color_formatter = colorlog.ColoredFormatter(
            f'{LIGHT_GRAY}%(asctime)s %(levelname)s %(filename)s : %(name)s : %(funcName)s : %(lineno)d\n'
            '%(log_color)s%(message)s',
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'bold_red',
            },
        )

        file_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(filename)s : %(name)s : %(funcName)s : %(lineno)d\n'
            '- %(message)s',
        )

        console_handler.setFormatter(color_formatter)
        file_handler.setFormatter(file_formatter)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # Add a filter to exclude specific messages
        def filter_out_proactor(record):
            return 'Using proactor: IocpProactor' not in record.getMessage()

        console_handler.addFilter(filter_out_proactor)
        file_handler.addFilter(filter_out_proactor)

        # Suppress debug logs from libraries
        for lib_logger in logging.Logger.manager.loggerDict.values():
            if isinstance(lib_logger, logging.Logger):
                lib_logger.setLevel(logging.WARNING)