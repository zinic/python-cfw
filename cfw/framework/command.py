import inspect
import itertools
import sys
from collections import defaultdict
from typing import Optional, List, Any, Dict, Tuple, Callable, Iterator

from cfw.framework.args import *
from cfw.framework.args.model import ArgumentDefinition
from cfw.framework.errors import CommandError, CommandArgumentError
from cfw.framework.formatting import format_two_column_output, format_one_column_output
from cfw.framework.util import GREEDY_WHITESPACE_RE

_EXEC_OK = "OK"
_PRINT_HELP = "PRINT_HELP"

_ARG_SWITCH_CHAR = "-"
_PRIVATE_NAME_PREFIX = "__"
_HELP_ARGUMENTS = ("-h", "-?", "--help")
_LAST_DEFAULT_ITR_VALUE = "LAST_DEFAULT_ITER"


class CommandWrapper(object):

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        path: Optional[str] = None,
        help: Optional[str] = None,
        arguments: Optional[List[ArgumentDefinition]] = None,
    ) -> None:
        self.func = func
        self.path: List[str] = list()
        self.path_spec = path
        self.argdefs: List[ArgumentDefinition] = list()
        self._func_argspec = inspect.getfullargspec(self.func)

        # If there's no name specified then use the name of the fuction instead
        self.name: str = name if name is not None else self.func.__name__

        if self.path_spec is not None:
            # If there's a path_spec, parse it into our path array
            self.path.extend(GREEDY_WHITESPACE_RE.split(self.path_spec))

        self.help: str = "" if help is None else help

        # If there's a valid docstring for the function but no help output
        # provided then use the docstring instead
        if help is None and self.func.__doc__ is not None:
            self.help: str = self.func.__doc__

        if arguments is not None:
            self.argdefs.extend(arguments)

        # Process our definitions and do some sanity checks
        self._process_arg_defs()

    def _positional_argdefs(self) -> List[Positional]:
        return [a for a in self.argdefs if isinstance(a, Positional)]

    def _non_positional_argdefs(self) -> List[ArgumentDefinition]:
        return [a for a in self.argdefs if not a.positional]

    def _process_arg_defs(self) -> None:
        # Iterator to track our position in the arg keyword list in reverse
        arg_kw_iter: Iterator[str] = reversed(self._func_argspec.args)

        # We create the arg_defaults iterator with an empty list first to avoid any weird
        # special-case checks while popping off default values
        arg_default_iter: Iterator[Any] = iter(list())
        if self._func_argspec.defaults is not None:
            # If there is a set of defaults in the argspec, iterate through them in reverse
            arg_default_iter = reversed(self._func_argspec.defaults)

        for arg_def in reversed(self.argdefs):
            # Check the annotation for hygiene first
            if arg_def.short_form in _HELP_ARGUMENTS or arg_def.long_form in _HELP_ARGUMENTS:
                raise CommandArgumentError("Arguments may not carry the signature of: {}".format(_HELP_ARGUMENTS))

            # Assign the matching function keyword
            try:
                arg_def.keyword = next(arg_kw_iter)
            except StopIteration:
                raise CommandArgumentError(
                    "CLI argument {} defined but function {} has no answering argument.".format(
                        arg_def, self.func.__name__
                    )
                ) from None

            # Map the default if any
            next_default = next(arg_default_iter, _LAST_DEFAULT_ITR_VALUE)
            if next_default is not _LAST_DEFAULT_ITR_VALUE:
                arg_def.set_default(next_default)

            # If there's no default but the argument is a flag, default to False
            if arg_def.has_default is False and isinstance(arg_def, Flag):
                arg_def.set_default(False)

        # Run sanity checks now that the argument definitions have been filled out with the remainder of
        # important details
        for arg_def in self.argdefs:
            arg_def.check()

    def print_help(self) -> None:
        # If there aren't any args, tell the user
        if len(self.argdefs) == 0:
            print("This command has no arguments specified.")
            return

        # Try to print out detailed argument help
        non_positional_argdefs = self._non_positional_argdefs()
        positional_argdefs = self._positional_argdefs()

        if len(non_positional_argdefs) > 0:
            # Do non-positional args first
            for argdef in self.argdefs:
                if not argdef.positional:
                    print(format_two_column_output(str(argdef), argdef.help))

            if len(positional_argdefs) > 0:
                # Add an additional newline if there are positional arguments
                print("")

        # Follow up with positional arguments last
        for argdef in positional_argdefs:
            if argdef.positional:
                print(format_two_column_output(str(argdef), argdef.help))

    @property
    def depth(self) -> int:
        return len(self.path)

    def __call__(self, argv: List[Any]) -> Any:
        # Scan argdefs for potential help requests
        for arg in argv:
            if arg in _HELP_ARGUMENTS:
                return _PRINT_HELP

        # Generate a kwargs dict
        try:
            kwargs = ArgumentMapper(self._positional_argdefs(), self._non_positional_argdefs()).map_to_kwargs(argv)
        except CommandError as ce:
            # Command errors here should be output directly to the user without a stacktrace
            print("{}\n".format(ce.msg))
            return _PRINT_HELP

        # Last but not least, we test to make sure all required arguments are provided
        required_arguments = list()
        for arg_def in self.argdefs:
            if arg_def.has_default is False and kwargs.get(arg_def.keyword) is None:
                required_arguments.append(arg_def)

        # If we're missing required arguments, remind the user of what we need and then print the help output
        if len(required_arguments) > 0:
            for arg_def in required_arguments:
                print("Argument required but not set: {}".format(arg_def))

            print("")
            return _PRINT_HELP

        # Hand off the args to the real receiver
        return self.func(**kwargs)

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class CommandNode(object):

    def __init__(self, cmd: CommandWrapper, is_root: bool = False) -> None:
        self.cmd = cmd
        self.is_root = is_root
        self.descendants: Dict[str, CommandNode] = dict()

    def append(self, cmd: "CommandNode") -> None:
        self.descendants[cmd.name] = cmd

    def get(self, name: str) -> Optional["CommandNode"]:
        return self.descendants.get(name)

    def print_help(self, cli_call_name: str) -> None:
        cmd_path = "{} {}".format(" ".join(self.cmd.path), self.name) if self.cmd.depth > 0 else self.name
        cmd_spec = "Usage: {} {}".format(cli_call_name, cmd_path)

        # Building an arg spec string is important for things like positional arguments where the order
        # of the argument determines where it is slotted in the target function
        cmd_arg_spec = "[options]"
        for argdef in self.cmd.argdefs:
            if argdef.positional is True:
                # If this isn't the first positional arg added to the cmd_arg_spec then we need as space
                if len(cmd_arg_spec) > 0:
                    cmd_arg_spec += " "

                cmd_arg_spec += "<{}>".format(argdef.name)

        # If there were positional arguments we need to append the cmd_arg_spec to the cmd_spec for output
        if len(cmd_arg_spec) > 0:
            cmd_spec += " {}".format(cmd_arg_spec)

        # Usage line first with the name we were called by on the CLI
        print("{}\n".format(cmd_spec))

        # Only output the help info if we have a help specified that is of non-zero length
        if self.help is not None and len(self.help) > 0:
            print("{}\n".format(format_one_column_output(self.help)))

        # List subcommands if any
        if len(self.descendants) > 0:
            self._print_subcmd_help()

            # Extra newline
            print("")

        # Any arguments from the command it self should be printed now
        self.cmd.print_help()

    def _print_subcmd_help(self) -> None:
        output = "Available Commands:\n"

        for name, subcmd in self.descendants.items():
            output += "{}\n".format(format_two_column_output(name, subcmd.help))

        print(output)

    @property
    def help(self) -> str:
        return self.cmd.help

    @property
    def name(self) -> str:
        return self.cmd.name

    def exec(self, cli_call_name: str, argv: List[Any]) -> None:
        result = self.cmd(argv)

        if result == _PRINT_HELP:
            self.print_help(cli_call_name)

    def __str__(self) -> str:
        return "CommandNode({})".format(self.name)


class CommandTrie(object):

    def __init__(self, cli_call_name: str, help: Optional[str] = None) -> None:
        # This name is passed to us so that our output is accurate according to what the user typed in or
        # calls the program we're processing arguments for.
        self.cli_call_name = cli_call_name

        # Root commands are nameless
        self._root_cmd = CommandNode(command_stub("", help=help), is_root=True)

    def dispatch(self, argv: Optional[List[Any]] = None) -> bool:
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
            print("Unknown command: {}\n".format(" ".join(argv)))

            self.print_help()
            return False

        cursor.exec(self.cli_call_name, args_list)
        return True

    def print_help(self) -> None:
        self._root_cmd.print_help(self.cli_call_name)

    def find(self, path: List[str]) -> Tuple[Optional[CommandNode], List[str]]:
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

    def insert(self, command: CommandWrapper) -> bool:
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
                    path_str = " ".join(last_path[: len(last_path) - 1])

                # Create a command stub - this may be overwritten by further, more specific inserts
                self.insert(command_stub(missing_cmd, path=path_str))

                # Attempt to resolve our path again
                target, last_path = self.find(command.path)

            target.append(CommandNode(command))

        return True


class ArgumentIterator(object):

    def __init__(self, argv: List[Any]) -> None:
        self._idx = 0
        self._argv = argv

    def finish(self) -> None:
        self._idx = len(self._argv)

    def advance(self, steps: int = 1) -> None:
        self._idx += steps

    def get(self) -> Any:
        return self._argv[self._idx]

    def get_rest(self) -> List[Any]:
        return self._argv[self._idx :]

    @property
    def on_last(self) -> bool:
        return self._idx + 1 == len(self._argv)

    @property
    def empty(self) -> bool:
        return self._idx >= len(self._argv)


class ArgumentMapper(object):

    def __init__(self, positionals: List[Positional], non_positionals: List[ArgumentDefinition]) -> None:
        # Track different argument types to make searching more deterministic
        self.positionals = positionals
        self.non_positionals = non_positionals

    def _match_arg(self, arg: str) -> Optional[ArgumentDefinition]:
        # Search non-positional argument definitions first
        for argdef in self.non_positionals:
            if argdef.matches(arg):
                return argdef
        return None

    def _prepare_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = defaultdict(list)

        # Map all flags first as False
        arg_def_iter: Iterator[ArgumentDefinition] = itertools.chain(self.positionals, self.non_positionals)
        for arg_def in arg_def_iter:
            if arg_def.default is not None:
                # Function argument defaults beat out our typing
                kwargs[arg_def.keyword] = arg_def.default

        return kwargs

    def map_to_kwargs(self, argv: List[Any]) -> Dict[str, Any]:
        arg_source = ArgumentIterator(argv)
        kwargs = self._prepare_kwargs()

        while arg_source.empty is False:
            # Get the next argument
            arg = arg_source.get()

            # Try to match the arg against non-positional argdefs first
            argdef = self._match_arg(arg)

            if argdef is None:
                # If there are no positional arguments remaining then this argument is unknown
                if len(self.positionals) == 0 or arg.startswith(_ARG_SWITCH_CHAR):
                    raise CommandError("Unknown argument: {}".format(arg))

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


def command_stub(name: str, path: Optional[str] = None, help: Optional[str] = "") -> CommandWrapper:

    def _stub_closure() -> str:
        return _PRINT_HELP

    return CommandWrapper(_stub_closure, name=name, path=path, help=help)
