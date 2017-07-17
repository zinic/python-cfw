# Command Framework

Command framework is a auto discoverable CLI tool that is designed to make it easy for python developers to produce
beautiful CLIs without having to write pages of definitions and dispatch code. 

### Example Usage

```python
import cfw


# Function and definition for the first command
@cfw.command(arguments=[
    cfw.Flag('-v', '--verbose', help='Run with more output.'),
    cfw.Argument('-r', '--default', help='This is a default argument.'),
    cfw.Positional(name='positional_arg', help='This is a required positional argument.'),
    cfw.Argument('-o', '--optional', help='This is an optional argument.')
])
def first(verbose, required, positional, optional=None):
    """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec auctor turpis a ligula sollicitudin pellentesque.
    Maecenas quis feugiat neque. Vestibulum eu sem id augue iaculis elementum eu vel dolor. Suspendisse aliquet orci
    nec ipsum dapibus, non maximus felis pretium. In auctor eleifend neque, quis bibendum turpis convallis ac.
    Suspendisse dignissim auctor leo, vitae mollis dolor aliquam id. Nunc id leo placerat, commodo tellus sed,
    fringilla lectus. Cras posuere condimentum urna a volutpat. Vestibulum convallis interdum euismod. Duis dapibus
    sagittis erat, a iaculis urna porta nec. Vivamus pulvinar dolor lectus, et tristique tellus efficitur vel.
    Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Mauris porttitor nunc
    a pellentesque semper.
    """
    print('{} {}'.format(verbose, required))


# Help output may be placed in the command definition if you wish to be explicit or rely on docstrings
# for other features and or documentation.
#
# By specifying a path for this command we're explicitly telling CFW that this is part of a nested command structure
# and that this command belongs with the descendants of the test command. If there is no corresponding test command
# defined elsewhere, then CFW will create a simple stub that handles dispatch and collates documentation for you.
@cfw.command(path='test', help='A nested command that lets you test nested paths.')
def second():
    pass


def main():
    cfw.dispatch('cfw.testapp')


if __name__ == '__main__':
    main()
```

### Example Output

Calling the root command reveals helpful output:

```text
Usage: cfw/testapp/test.py

Available Commands:
  first                       Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                              Donec auctor turpis a ligula sollicitudin pellentesque.
                              Maecenas quis feugiat neque. Vestibulum eu sem id augue
                              iaculis...
  test

This command has no arguments specified.
```

Calling further subcommands will allow you to explore the CLI:

```text
Usage: cfw/testapp/test.py test

Available Commands:
  second                      A nested command that lets you test nested paths.
  
This command has no arguments specified.
```


### License

This software is made available to you under the [MIT License](LICENSE).
