import sys
import logging

class BotLogger():
    class __BotLogger: # pylint: disable=invalid-name, attribute-defined-outside-init

        def initialize(self, path):
            self.stdout_enabled = False
            self.level = logging.INFO

            self.logger = logging.getLogger('wowdkpbot-{0}'.format(path))
            self.file_handler = logging.FileHandler('{0}/bot.log'.format(path), encoding='utf-8')
            self.formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')          
            self.file_handler.setFormatter(self.formatter)

            self.logger.addHandler(self.file_handler)
            self.stdout_handler = logging.StreamHandler(sys.stdout)

            self.set_level(logging.INFO)

        def get(self):
            return self.logger

        def stdout(self, enable: bool):
            if self.stdout_enabled != enable:
                if enable:
                    self.logger.addHandler(self.stdout_handler)
                else:
                    self.logger.removeHandler(self.stdout_handler)
                self.stdout_enabled = enable

        def set_level(self, level):
            if logging._levelToName.get(level) is not None:
                self.level = level
            elif logging._nameToLevel.get(level) is not None:
                self.level = logging._nameToLevel.get(level)
            else:
                self.logger.warning("Invalid log level {0}".format(level))
                return False

            self.logger.warning("Setting log level %s", self.get_level_name())
            self.logger.setLevel(self.level)
            return True

        def get_level(self):
            return self.level

        def get_level_name(self):
            return logging._levelToName.get(self.level)

    instance = None

    def __new__(cls):  # __new__ always a classmethod
        if not BotLogger.instance:
            BotLogger.instance = BotLogger.__BotLogger()
        return BotLogger.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, value):
        return setattr(self.instance, name, value)
