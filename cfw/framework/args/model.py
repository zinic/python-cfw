from cfw.framework.errors import CommandArgumentError


class ArgumentDefinition(object):
    def __init__(self, short_form=None, long_form=None, name=None, help=None):
        self.short_form = short_form
        self.long_form = long_form
        self.name = name
        self.help = help
        self.keyword = None
        self.required = True
        self.default = None
        self.has_default = False

    @property
    def positional(self):
        return False

    def set_default(self, value):
        self.default = value
        self.has_default = True

    def check(self):
        if self.short_form is None and self.long_form is None:
            raise CommandArgumentError('No valid CLI form specified for argument: {}'.format(self.keyword))

    def forms(self):
        """
        Returns a formatted string with the matchable forms for the argument
        :return:
        """
        forms = ''
        if self.short_form is not None:
            forms += self.short_form

        if self.long_form is not None:
            if len(forms) > 0:
                forms += ', '

            forms += self.long_form

        return forms

    def matches(self, arg):
        matches = self.short_form is not None and arg == self.short_form

        if matches is False:
            matches = self.long_form is not None and arg == self.long_form

        return matches

    def __str__(self):
        if self.name is not None:
            return self.name
        return self.forms()


class Argument(ArgumentDefinition):
    pass


class Positional(ArgumentDefinition):
    @property
    def positional(self):
        return True

    def check(self):
        if self.name is None:
            raise CommandArgumentError('Positional arguments require a name.')

    def matches(self, arg):
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
