import sys
import logging

class BotLogger():
    class __BotLogger: #pylint: disable=invalid-name, attribute-defined-outside-init

        def initialize(self, path):
            self.logger = logging.getLogger('wowdkpbot-{0}'.format(path))
            self.file_handler = logging.FileHandler('{0}/bot.log'.format(path), encoding='utf-8')
            self.formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            self.file_handler.setFormatter(self.formatter)
            self.logger.addHandler(self.file_handler)
            self.logger.setLevel(logging.INFO)
            self.handler = logging.StreamHandler(sys.stdout)
            self.logger.addHandler(self.handler)
            #self.logger.setLevel(logging.DEBUG)

        def get(self):
            return self.logger

    instance = None

    def __new__(cls):  # __new__ always a classmethod
        if not BotLogger.instance:
            BotLogger.instance = BotLogger.__BotLogger()
        return BotLogger.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, value):
        return setattr(self.instance, name, value)
