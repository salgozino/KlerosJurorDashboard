from flask import Flask
import logging


def create_app(settings_module='config.default'):
    # create the app
    app = Flask(__name__)
    app.config.from_object(settings_module)
    # configure the logger
    configure_logging(app)
    # load the database
    # from app.modules import db
    # db.init_app(app)

    return app


def configure_logging(app):
    # Elimina los manejadores por defecto de la app
    del app.logger.handlers[:]
    loggers = [app.logger, ]
    handlers = []
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(verbose_formatter())
    file_handler = logging.FileHandler('flask-log.log')
    file_handler.setFormatter(verbose_formatter())

    if (app.config['APP_ENV'] == app.config['APP_ENV_LOCAL']) or (
            app.config['APP_ENV'] == app.config['APP_ENV_TESTING']) or (
            app.config['APP_ENV'] == app.config['APP_ENV_DEVELOPMENT']):
        console_handler.setLevel(logging.DEBUG)
        file_handler.setLevel(logging.DEBUG)
        handlers.append(console_handler)
        handlers.append(file_handler)
    elif app.config['APP_ENV'] == app.config['APP_ENV_PRODUCTION']:
        console_handler.setLevel(logging.INFO)
        file_handler.setLevel(logging.INFO)
        handlers.append(console_handler)
        handlers.append(file_handler)
    for logger in loggers:
        for handler in handlers:
            logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(logging.DEBUG)


def verbose_formatter():
    return logging.Formatter(
        '[%(asctime)s.%(msecs)d]\t %(levelname)s'
        + ' \t[%(name)s.%(funcName)s:%(lineno)d]\t %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S'
    )
