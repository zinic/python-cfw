import inspect
import itertools
import sys

from collections import defaultdict

from cfw.framework.args import *
from cfw.framework.formatting import format_two_column_output, format_one_column_output
from cfw.framework.errors import CommandError, CommandArgumentError
from cfw.framework.util import GREEDY_WHITESPACE_RE

_EXEC_OK = 'OK'
_PRINT_HELP = 'PRINT_HELP'

_PRIVATE_NAME_PREFIX = '__'
_HELP_ARGUMENTS = ('-h', '-?', '--help',)


def command_stub(name, path=None, help=''):
    def _stub_closure():
        return _PRINT_HELP

    return CommandWrapper(_stub_closure, name=name, path=path, help=help)


class CommandTrie(object):
    def __init__(self, cli_call_name, help=None):
        # This name is passed to us so that our output is accurate according to what the user typed in or
        # calls the program we're processing arguments for.
        self.cli_call_name = cli_call_name

        # Root commands are nameless
        self._root_cmd = CommandNode(command_stub('', help=help), is_root=True)

    def dispatch(self, argv=None):
        """
        Attempts to dispatch to the correct command function given a set of argdefs. If no argdefs are
        specified then sys.argv is used instead.

        :param argv:
        :return: True if the command dispatched successfully, False otherwise.
        """

        # If we weren't given any argdefs simply assume the user wanted to operate on sys.argv
        if argv is None:
            argv = sys.argv

        # No argdefs usually means the user is hunting for the help output, otherwise
        # if the first argument is a help argument, print help as well.
        if len(argv) <= 1 or argv[1] in _HELP_ARGUMENTS:
            self.print_help()
            return False

        # List for capturing anything that looks like a CLI argument and not part of the command path
        args_list = list()

        # Always start at argv[1] for the command path
        cursor = self._root_cmd
        for arg in argv[1:]:
            # Attempt to match the argument against our path - anything that doesn't match
            # gets added to the argument list
            potential_next = cursor.get(arg)
            if potential_next is not None:
                cursor = potential_next
            else:
                args_list.append(arg)

        # If the cursor is still pointing at our root dictionary then no command parts matched
        if cursor is self._root_cmd:
            print('Unknown command: {}\n'.format(' '.join(argv)))

            self.print_help()
            return False

        cursor.exec(self.cli_call_name, args_list)
        return True

    def print_help(self):
        self._root_cmd.print_help(self.cli_call_name)

    def find(self, path):
        # Find the root CN first
        root_path = path[0]

        # Track what we matched
        matched_path = [root_path]

        cursor = self._root_cmd.get(root_path)
        if cursor is not None:
            # Look up descendants till we exhaust the path
            for path_part in path[1:]:
                # Track where we are
                matched_path.append(path_part)

                # Check to see if the next part has a matching command
                cursor = cursor.get(path_part)

                # If there's no matching command at this part of the path, return where we
                # left off in the path
                if cursor is None:
                    break

        return cursor, matched_path

    def insert(self, command):
        if command.depth == 0:
            self._root_cmd.append(CommandNode(command))

        else:
            target, last_path = self.find(command.path)
            while target is None:
                # Get the name of the command we choked on
                missing_cmd = last_path[len(last_path) - 1]

                # Recreate the path string for insertion
                path_str = None
                if len(last_path) > 1:
                    path_str = ' '.join(last_path[:len(last_path) - 1])

                # Create a command stub - this may be overwritten by further, more specific inserts
                self.insert(command_stub(missing_cmd, path=path_str))

                # Attempt to resolve our path again
                target, last_path = self.find(command.path)

            target.append(CommandNode(command))

        return True


class CommandNode(object):
    def __init__(self, cmd, is_root=False):
        self.cmd = cmd
        self.is_root = is_root
        self.descendants = dict()

    def append(self, cmd):
        self.descendants[cmd.name] = cmd

    def get(self, name):
        return self.descendants.get(name)

    def print_help(self, cli_call_name):
        cmd_path = '{} {}'.format(' '.join(self.cmd.path), self.name) if self.cmd.depth > 0 else self.name
        cmd_spec = 'Usage: {} {}'.format(cli_call_name, cmd_path)

        # Building an arg spec string is important for things like positional arguments where the order
        # of the argument determines where it is slotted in the target function
        cmd_arg_spec = ''
        for argdef in self.cmd.argdefs:
            if argdef.positional is True:
                # If this isn't the first positional arg added to the cmd_arg_spec then we need as space
                if len(cmd_arg_spec) > 0:
                    cmd_arg_spec += ' '

                cmd_arg_spec += '<{}>'.format(argdef.name)

        # If there were positional arguments we need to append the cmd_arg_spec to the cmd_spec for output
        if len(cmd_arg_spec) > 0:
            cmd_spec += ' {}'.format(cmd_arg_spec)

        # Usage line first with the name we were called by on the CLI
        print('{}\n'.format(cmd_spec))

        # Only output the help info if we have a help specified that is of non-zero length
        if self.help is not None and len(self.help) > 0:
            print('{}\n'.format(format_one_column_output(self.help)))

        # List subcommands if any
        if len(self.descendants) > 0:
            self._print_subcmd_help()

            # Extra newline
            print('')

        # Any arguments from the command it self should be printed now
        self.cmd.print_help()

    def _print_subcmd_help(self):
        output = 'Available Commands:\n'

        for name, subcmd in self.descendants.items():
            output += '{}\n'.format(format_two_column_output(name, subcmd.help))

        print(output)

    @property
    def help(self):
        return self.cmd.help if self.cmd.help is not None else 'No help output specified.'

    @property
    def name(self):
        return self.cmd.name

    def exec(self, cli_call_name, argv):
        result = self.cmd(argv)

        if result == _PRINT_HELP:
            self.print_help(cli_call_name)

    def __str__(self):
        return 'CommandNode({})'.format(self.name)


class ArgumentIterator(object):
    def __init__(self, argv):
        self._idx = 0
        self._argv = argv

    def finish(self):
        self._idx = len(self._argv)

    def advance(self, steps=1):
        self._idx += steps

    def get(self):
        return self._argv[self._idx]

    def get_rest(self):
        return self._argv[self._idx:]

    @property
    def on_last(self):
        return self._idx + 1 == len(self._argv)

    @property
    def empty(self):
        return self._idx >= len(self._argv)


class ArgumentMapper(object):
    def __init__(self, arg_defs):
        # Track different argument types to make searching more deterministic
        self.positionals = list()
        self.non_positionals = list()

        for argdef in arg_defs:
            if argdef.positional is True:
                self.positionals.append(argdef)
            else:
                self.non_positionals.append(argdef)

    def _match_arg(self, arg):
        # Search non-positional argument definitions first
        for argdef in self.non_positionals:
            if argdef.matches(arg):
                return argdef
        return None

    def _prepare_kwargs(self):
        kwargs = defaultdict(list)

        # Map all flags first as False
        for arg_def in itertools.chain(self.positionals, self.non_positionals):
            if arg_def.default is not None:
                # Function argument defaults beat out our typing
                kwargs[arg_def.keyword] = arg_def.default

        return kwargs

    def map_to_kwargs(self, argv):
        arg_source = ArgumentIterator(argv)
        kwargs = self._prepare_kwargs()

        while arg_source.empty is False:
            # Get the next argument
            arg = arg_source.get()

            # Try to match the arg against non-positional argdefs first
            argdef = self._match_arg(arg)
            if argdef is None:
                # If there are no positional arguments remaining then this argument is unknown
                if len(self.positionals) == 0:
                    raise CommandError('Unknown argument: {}'.format(arg))

                # Select the first positional argument
                argdef = self.positionals[0]

            # Attempt to gather up the value that's represented by the argument
            if isinstance(argdef, Flag):
                kwargs[argdef.keyword] = True
                arg_source.advance()

            elif isinstance(argdef, ListArgument):
                arg_source.advance()
                kwargs[argdef.keyword].append(arg_source.get())
                arg_source.advance()

            elif isinstance(argdef, WildcardArgument):
                arg_source.advance()
                kwargs[argdef.keyword].extend(arg_source.get_rest())
                arg_source.finish()

            elif isinstance(argdef, Argument):
                arg_source.advance()
                kwargs[argdef.keyword] = arg_source.get()
                arg_source.advance()

            elif isinstance(argdef, ListPositional):
                # First remove this positional argdef from our list of positional arg defs
                self.positionals.pop(0)

                # Add the arg as our value
                kwargs[argdef.keyword].append(arg_source.get())
                arg_source.advance()

                # Continue consuming arguments until the next match or until we reach a point
                # where other positional arguments expect to be filled in
                while not arg_source.on_last and not arg_source.empty:
                    # If an argument definition matches then we're done with this list
                    if self._match_arg(arg_source.get()) is not None:
                        break

                    arg_source.advance()

            elif isinstance(argdef, WildcardPositional):
                # First remove this positional argdef from our list of positional arg defs
                self.positionals.pop(0)

                kwargs[argdef.keyword].extend(arg_source.get_rest())
                arg_source.finish()

            elif isinstance(argdef, Positional):
                # First remove this positional argdef from our list of positional arg defs
                self.positionals.pop(0)

                kwargs[argdef.keyword] = arg_source.get()
                arg_source.advance()

        return kwargs


class CommandWrapper(object):
    def __init__(self, func, name=None, path=None, help=None, arguments=None):
        self.func = func
        self.name = name
        self.path = list()
        self.path_spec = path
        self.help = help
        self.argdefs = arguments

        self._func_argspec = inspect.getfullargspec(self.func)

        if self.name is None:
            # If there's no name specified then use the name of the fuction
            # instead
            self.name = self.func.__name__

        if self.path_spec is not None:
            # If there's a path_spec, parse it into our path array
            self.path.extend(GREEDY_WHITESPACE_RE.split(self.path_spec))

        if self.help is None and self.func.__doc__ is not None:
            # If there's a valid docstring for the function but no help output
            # provided then use the docstring instead
            self.help = self.func.__doc__

        if self.argdefs is None:
            # Make sure that self.argdefs is never None
            self.argdefs = list()

        # Process our definitions and do some sanity checks
        self._process_arg_defs()

    def _process_arg_defs(self):
        # Iterator to track our position in the arg keyword list in reverse
        arg_kw_iter = reversed(self._func_argspec.args)

        # We create the arg_defaults iterator with an empty list first to avoid any weird
        # special-case checks while popping off default values
        arg_default_iter = iter(list())
        if self._func_argspec.defaults is not None:
            # If there is a set of defaults in the argspec, iterate through them in reverse
            arg_default_iter = reversed(self._func_argspec.defaults)

        for arg_def in reversed(self.argdefs):
            # Check the annotation for hygiene first
            if arg_def.short_form in _HELP_ARGUMENTS or arg_def.long_form in _HELP_ARGUMENTS:
                raise CommandArgumentError('Arguments may not carry the signature of: {}'.format(_HELP_ARGUMENTS))

            # Assign the matching function keyword
            try:
                arg_def.keyword = next(arg_kw_iter)
            except StopIteration:
                raise CommandArgumentError('CLI argument {} defined but function {} has no answering argument.'.format(
                    arg_def, self.func.__name__)) from None

            # Map the default if any
            next_default = next(arg_default_iter, None)
            if next_default is not None:
                arg_def.set_default(next_default)

            # If there's no default but the argument is a flag, default to False
            if arg_def.has_default is False and isinstance(arg_def, Flag):
                arg_def.set_default(False)

        # Run sanity checks now that the argument definitions have been filled out with the remainder of
        # important details
        for arg_def in self.argdefs:
            arg_def.check()

    def print_help(self):
        # If there aren't any args, tell the user
        if len(self.argdefs) == 0:
            print('This command has no arguments specified.')
            return

        # Try to print out detailed argument help
        print('Arguments:')
        for argdef in self.argdefs:
            print(format_two_column_output(argdef, argdef.help))

    @property
    def depth(self):
        return len(self.path)

    def __call__(self, argv):
        # Scan argdefs for potential help requests
        for arg in argv:
            if arg in _HELP_ARGUMENTS:
                return _PRINT_HELP

        # Generate a kwargs dict
        kwargs = ArgumentMapper(self.argdefs).map_to_kwargs(argv)

        # Last but not least, we test to make sure all required arguments are provided
        for arg_def in self.argdefs:
            if arg_def.has_default is True and kwargs.get(arg_def.keyword) is None:
                print('Missing required argument: {}\n'.format(arg_def.short_form))
                return _PRINT_HELP

        # Hand off the args to the real receiver
        result = self.func(**kwargs)
        if result is _PRINT_HELP:
            return result

        return _EXEC_OK

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name
