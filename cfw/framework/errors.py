class CommandError(Exception):

    def __init__(self, msg: str = "") -> None:
        super(CommandError, self).__init__()
        self.msg = msg

    def __str__(self) -> str:
        return self.msg


class CommandArgumentError(CommandError):
    pass


class CommandNotFoundError(CommandError):
    pass


class CommandDependencyError(CommandError):

    def __str__(self) -> str:
        return "Command Dependency Error: {}".format(self.msg)
