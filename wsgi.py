from app import create_app
import logging
from logging.handlers import RotatingFileHandler
import os

app = create_app('production')


if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler(
    'logs/bolakin.log', 
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Bolakin Educational Consult startup')

if __name__ == '__main__':
    app.run(host='0.0.0.0')