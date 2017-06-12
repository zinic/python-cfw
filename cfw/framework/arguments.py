class ArgumentDefinition(object):
    def __init__(self, short_form, long_form=None, help=None):
        self.short_form = short_form
        self.long_form = long_form
        self.help = help
        self.keyword = None
        self.required = True
        self.default = None

        self._matchers = (self.short_form, self.long_form,)

    def matches(self, arg):
        return arg in self._matchers

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
