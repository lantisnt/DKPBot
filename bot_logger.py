import sys
import logging
import inspect, functools


class BotLogger:
    class __BotLogger:  # pylint: disable=invalid-name, attribute-defined-outside-init
        stdout_enabled = False
        trace_enabled = False

        def initialize(self, path):
            self.stdout_enabled = False
            self.trace_enabled = False
            # self.level = logging.INFO
            self.level = logging.DEBUG

            self.logger = logging.getLogger("wowdkpbot-{0}".format(path))
            self.file_handler = logging.FileHandler(
                "{0}/bot.log".format(path), encoding="utf-8"
            )
            self.formatter = logging.Formatter(
                "[%(asctime)s %(levelname)8s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )

            self.file_handler.setFormatter(self.formatter)

            self.logger.addHandler(self.file_handler)
            self.stdout_handler = logging.StreamHandler(sys.stdout)
            self.stdout_handler.setFormatter(self.formatter)

            self.set_level(self.level)

        def get(self):
            return self.logger

        def config_stdout(self, enable: bool):
            if self.stdout_enabled != enable:
                if enable:
                    self.logger.addHandler(self.stdout_handler)
                else:
                    self.logger.removeHandler(self.stdout_handler)
                self.stdout_enabled = enable

        def config_trace(self, enable: bool):
            if self.trace_enabled != enable:
                if enable:
                    self.logger.setLevel(logging.DEBUG)
                else:
                    self.__set_level_internal()
                self.trace_enabled = enable

        def __set_level_internal(self):
            self.logger.warning("Setting log level %s", self.get_level_name())
            self.logger.setLevel(self.level)

        def set_level(self, level):
            if logging._levelToName.get(level) is not None:
                self.level = level
            elif logging._nameToLevel.get(level) is not None:
                self.level = logging._nameToLevel.get(level)
            else:
                self.logger.warning("Invalid log level {0}".format(level))
                return False

            if self.trace_enabled:
                self.logger.warning(
                    "Skipping log level setting due to Trace. New level (%s) will be set on Trace disable.",
                    self.get_level_name(),
                )
                return

            self.__set_level_internal()

            return True

        def get_level(self):
            return self.level

        def get_level_name(self):
            return logging._levelToName.get(self.level)

        def is_trace_enabled(self):
            return self.trace_enabled

    instance = None

    def __new__(cls):  # __new__ always a classmethod
        if not BotLogger.instance:
            BotLogger.instance = BotLogger.__BotLogger()
        return BotLogger.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, value):
        return setattr(self.instance, name, value)


def _sat(input, width=1024):
    return str(input)[:width]


# https://stackoverflow.com/questions/3589311/get-defining-class-of-unbound-method-object-in-python-3/25959545#25959545
def _get_class_that_defined_method(meth):
    if isinstance(meth, functools.partial):
        return get_class_that_defined_method(meth.func)
    if inspect.ismethod(meth) or (
        inspect.isbuiltin(meth)
        and getattr(meth, "__self__", None) is not None
        and getattr(meth.__self__, "__class__", None)
    ):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, "__func__", meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(
            inspect.getmodule(meth),
            meth.__qualname__.split(".<locals>", 1)[0].rsplit(".", 1)[0],
            None,
        )
        if isinstance(cls, type):
            return cls
    return getattr(meth, "__objclass__", None)  # handle special descriptor objects


def trace(func):
    def tracer(*args, **kwargs):
        if BotLogger().is_trace_enabled():
            BotLogger().get().debug(
                "%s : %s : %s", _sat(func.__name__), _sat(args), _sat(kwargs)
            )
        return func(*args, **kwargs)

    return tracer


def trace_func_only(func):
    def tracer(*args, **kwargs):
        if BotLogger().is_trace_enabled():
            class_name = _get_class_that_defined_method(func)
            BotLogger().get().debug(
                "%s%s",
                _sat(func.__name__),
                (" " + str(class_name)) if class_name is not None else "",
            )
        return func(*args, **kwargs)

    return tracer


# https://stackoverflow.com/questions/6307761/how-to-decorate-all-functions-of-a-class-without-typing-it-over-and-over-for-eac
def for_all_methods(decorator=trace, decorator_internal_methods=trace_func_only):
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)):
                if attr in ["__init__", "__str__", "__repr__", "__hash__"]:
                    setattr(cls, attr, decorator_internal_methods(getattr(cls, attr)))
                else:
                    setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate