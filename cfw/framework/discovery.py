import importlib
import os
import sys
from typing import Callable, List, Any, Optional

from cfw.framework.args.model import ArgumentDefinition
from cfw.framework.command import CommandWrapper, CommandTrie
from cfw.framework.errors import CommandDependencyError, CommandError

_PYTHON_SRC_CODE_EXT = ".py"
_PYTHON_BYTE_CODE_EXT = ".pyc"
_PRIVATE_NAME_PREFIX = "__"
_IGNORE_LIST = ("__pycache__", "__init__.py")
_PYTHON_EXTENSIONS = (_PYTHON_SRC_CODE_EXT, _PYTHON_BYTE_CODE_EXT)
_PYTHON_MODULE_INIT_FILE = "__init__.py"


def _is_python_src_file(filename: str) -> bool:
    return filename.endswith(_PYTHON_SRC_CODE_EXT)


def _is_relative(module: str) -> bool:
    return module.startswith(".")


def _file_extension(path: str) -> str:
    ext_parts = os.path.splitext(path)
    return ext_parts[1] if len(ext_parts) > 1 else ""


def command(
    name: Optional[str] = None,
    path: Optional[str] = None,
    help: Optional[str] = None,
    arguments: Optional[List[ArgumentDefinition]] = None,
) -> Callable[[Callable], CommandWrapper]:
    """
    Just a marker annotation for code documentation for now. Might work to auto-pull in
    command line functions but that's for later.

    :return:
    """

    def _factory(target_func: Callable) -> CommandWrapper:
        return CommandWrapper(target_func, name, path, help, arguments)

    return _factory


def dispatch(
    module: str,
    package: Optional[str] = None,
    argv: Optional[List[Any]] = None,
    verbose: bool = False,
    help: Optional[str] = None,
) -> None:
    if _is_relative(module) is True and package is None:
        raise CommandError(
            "Attempting an import of a relative module requires the package argument to be specified."
        )

    if argv is None:
        argv = sys.argv

    trie = scan(argv[0], module, package, verbose, help)
    trie.dispatch(argv)


def scan(
    cli_call_name: str, module: str, package: Optional[str], verbose: bool, help: Optional[str]
) -> CommandTrie:
    """
    This crawls all of the modules below us and imports them recursively
    :return:
    """
    root_module = importlib.import_module(module, package=package)
    root_path = root_module.__file__

    if verbose:
        print("Scanning module {} starting at file path: {}".format(module, root_path))

    # Format the module name correctly if this is a relative import we're starting with
    target_module = module
    if _is_relative(target_module):
        if package is None:
            raise CommandError("Package was not specified but the module is relative.")

        target_module = package

    # Search path changes if the __file__ entry is a python init file and not a directory
    search_path = root_path
    if search_path.endswith(_PYTHON_MODULE_INIT_FILE):
        search_path = os.path.dirname(root_path)

    # First identify all submodules
    submodule_names = list()

    # If our search path is not a directory, move on
    if os.path.isdir(search_path):
        for filename in os.listdir(search_path):
            if filename in _IGNORE_LIST:
                continue

            abs_path = os.path.join(search_path, filename)
            init_path = os.path.join(abs_path, _PYTHON_MODULE_INIT_FILE)

            module_name = ""
            if os.path.isdir(abs_path) and os.path.exists(init_path):
                # Figure out if we're dealing with a directory that has the init file
                module_name = ".".join((target_module, filename))
            elif _is_python_src_file(filename):
                # Is it a python source file that's stand-alone?
                file_module_name = os.path.splitext(filename)[0]
                module_name = ".".join((target_module, file_module_name))
            else:
                # I don't like this continue but avoiding the print statement twice is a nice consequence
                continue

            if verbose:
                print("Adding module {} to the scan list.".format(module_name))

            # Add the module to our scan and import list
            submodule_names.append(module_name)

    # Load the modules
    submodules = [importlib.import_module(n) for n in submodule_names]

    # Add the root module since that's part of the scan
    submodules.append(root_module)

    # Load and scan the submodules for command components
    command_components = list()
    for submodule in submodules:
        for component_name in dir(submodule):
            component = getattr(submodule, component_name)
            if isinstance(component, CommandWrapper):
                if verbose:
                    print("Found command component: {}".format(component))

                command_components.append(component)

    # Build our command trie with collected components and perform rudimentary
    # dependency resolution for command paths
    command_trie = CommandTrie(cli_call_name, help=help)
    while len(command_components) > 0:
        delete_list = list()
        for idx in range(0, len(command_components)):
            command = command_components[idx]

            if command_trie.insert(command) is True:
                if verbose:
                    print("Inserted {}".format(command))

                delete_list.append(idx)
                break

        if len(delete_list) == 0:
            raise CommandDependencyError("Dependency resolution error!")

        for idx in reversed(sorted(delete_list)):
            command_components.pop(idx)

    return command_trie
