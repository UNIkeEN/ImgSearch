import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    uvicorn_logger = logging.getLogger("uvicorn.error")
    if uvicorn_logger.handlers:
        logger.handlers = uvicorn_logger.handlers
        logger.setLevel(uvicorn_logger.level)
        logger.propagate = False
    else:
        logging.basicConfig(level=logging.INFO)
    return logger
