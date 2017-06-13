import importlib
import os
import sys

from .command import CommandWrapper, CommandTrie
from .errors import CommandDependencyError

_PRIVATE_NAME_PREFIX = '__'
_IGNORE_LIST = ('__pycache__',)
_PYTHON_EXTENSIONS = ('.py', '.pyc',)
_PYTHON_MODULE_INIT_FILE = '__init__.py'


def _file_extension(path):
    ext_parts = os.path.splitext(path)
    return ext_parts[1] if len(ext_parts) > 1 else ''


def command(*args, **kwargs):
    """
    Just a marker annotation for code documentation for now. Might work to auto-pull in
    command line functions but that's for later.

    :return:
    """
    func = None
    invoked = bool(not args or kwargs)
    if invoked is False:
        func, args = args[0], ()

    def _factory(target_func):
        return CommandWrapper(target_func, *args, **kwargs)

    return _factory if invoked is True else _factory(func)


def dispatch(target_module, argv=None, verbose=False, help=None):
    if argv is None:
        argv = sys.argv

    trie = scan(argv[0], target_module, verbose, help)
    trie.dispatch(argv)


def scan(cli_call_name, target_module, verbose, help):
    """
    This crawls all of the modules below us and imports them recursively
    :return:
    """
    root_module = importlib.import_module(target_module)
    root_path = root_module.__file__

    if verbose:
        print('Scanning module {} starting at file path: {}'.format(target_module, root_path))

    # Search path changes if the __file__ entry is a python file and not a directory
    search_path = root_path
    if _file_extension(search_path) in _PYTHON_EXTENSIONS:
        search_path = os.path.dirname(root_path)

    # First identify all submodules
    submodule_names = list()
    for filename in os.listdir(search_path):
        if filename in _IGNORE_LIST:
            continue

        abs_path = os.path.join(search_path, filename)
        init_path = os.path.join(abs_path, _PYTHON_MODULE_INIT_FILE)

        if os.path.isdir(abs_path) and os.path.exists(init_path):
            submodule_names.append('.'.join((target_module, filename,)))

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
                    print('Found command component: {}'.format(component))

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
                    print('Inserted {}'.format(command))

                delete_list.append(idx)
                break

        if len(delete_list) == 0:
            raise CommandDependencyError('Dependency resolution error!')

        for idx in reversed(sorted(delete_list)):
            command_components.pop(idx)

    return command_trie
