import logging

# noinspection SpellCheckingInspection
FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT)
formatter = logging.Formatter(FORMAT)
logger = logging.getLogger('fit_tool')
logger.setLevel(logging.INFO)
