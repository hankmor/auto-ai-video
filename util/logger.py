import logging
import sys

def setup_logger():
    logger = logging.getLogger("auto_maker")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

logger = setup_logger()

def traceback():
    import traceback

    logger.error(traceback.format_exc())


def traceback_and_raise(e):
    traceback()
    raise e