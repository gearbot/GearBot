import argparse
from typing import Text, NoReturn, Optional


# make my own version so it doesn't kill GearBot everyone someone screws up the syntax
class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: Text) -> NoReturn:
        raise ValueError(message)

    # no you are not killing the bot
    def exit(self, status: int = ..., message: Optional[Text] = ...) -> NoReturn:
        pass
