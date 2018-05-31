from typing import Optional, Any

from cfw.framework.errors import CommandArgumentError


class ArgumentDefinition(object):

    def __init__(
        self,
        short_form: Optional[str] = None,
        long_form: Optional[str] = None,
        name: Optional[str] = None,
        help: Optional[str] = None,
    ) -> None:
        self.short_form = short_form
        self.long_form = long_form
        self.name = name
        self.help = help
        self.keyword: str = ""
        self.required = True
        self.default: Optional[Any] = None
        self.has_default = False

    @property
    def positional(self) -> bool:
        return False

    def set_default(self, value: Any) -> None:
        self.default = value
        self.has_default = True

    def check(self) -> None:
        if self.short_form is None and self.long_form is None:
            raise CommandArgumentError("No valid CLI form specified for argument: {}".format(self.keyword))

    def forms(self) -> str:
        """
        Returns a formatted string with the matchable forms for the argument
        :return:
        """
        forms = ""
        if self.short_form is not None:
            forms += self.short_form

        if self.long_form is not None:
            if len(forms) > 0:
                forms += ", "

            forms += self.long_form

        return forms

    def matches(self, arg: str) -> bool:
        matches = self.short_form is not None and arg == self.short_form

        if matches is False:
            matches = self.long_form is not None and arg == self.long_form

        return matches

    def __str__(self) -> str:
        if self.name is not None:
            return self.name
        return self.forms()


class Argument(ArgumentDefinition):
    pass


class Positional(ArgumentDefinition):

    @property
    def positional(self) -> bool:
        return True

    def check(self) -> None:
        if self.name is None:
            raise CommandArgumentError("Positional arguments require a name.")

    def matches(self, arg: str) -> bool:
        return True


class ListPositional(Positional):
    pass


class WildcardPositional(Positional):
    pass


class WildcardArgument(ArgumentDefinition):
    pass


class ListArgument(ArgumentDefinition):
    pass


class Flag(ArgumentDefinition):
    pass
