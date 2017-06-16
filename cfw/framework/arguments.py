from .errors import CommandArgumentError


class ArgumentDefinition(object):
    def __init__(self, short_form=None, long_form=None, help=None):
        self.short_form = short_form
        self.long_form = long_form
        self.help = help
        self.keyword = None
        self.required = True
        self.default = None
        self.has_default = False

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

    def gather(self, argv, idx):
        raise NotImplementedError()


class Argument(ArgumentDefinition):
    def gather(self, argv, idx):
        idx += 1
        return idx, argv[idx]


class WildcardArgument(ArgumentDefinition):
    def gather(self, argv, idx):
        idx += 1
        return len(argv), argv[idx:]


class ListArgument(ArgumentDefinition):
    def gather(self, argv, idx):
        raise NotImplementedError()


class Flag(ArgumentDefinition):
    def gather(self, argv, idx):
        return idx, True
