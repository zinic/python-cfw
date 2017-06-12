from .util import GREEDY_WHITESPACE_RE

# Formatting guides
_FIRST_COLUMN_LEN = 30
_SECOND_COLUMN_LEN = 56

# 32 - 4 (spacing) - 2 (leading space)
_MAX_FIRST_COLUMN_LEN = 26
_MAX_LINE_LEN = 88
_MAX_SECOND_COLUMN_LINES = 4


def _sanitize(input):
    return input.strip().replace('\n', ' ')


def _sanitize_split(input):
    return GREEDY_WHITESPACE_RE.split(_sanitize(input))


def format_one_column_output(first):
    first_output = ''

    buf = ''
    for word in _sanitize_split(first):
        if len(buf) + len(word) > _MAX_LINE_LEN:
            first_output += '{}\n'.format(buf)
            buf = word

        elif len(buf) == 0:
            buf = word

        else:
            buf += ' {}'.format(word)

    if len(buf) > 0:
        first_output += buf

    return first_output


def format_two_column_output(first, second):
    first_output = '  {}'.format(_sanitize(first))
    if len(first_output) > _MAX_FIRST_COLUMN_LEN:
        first_output = '  {}...'.format(first[:_MAX_FIRST_COLUMN_LEN - 3])

    add_nl_buffer = False
    second_output = ''.join([' ' for _ in range(_FIRST_COLUMN_LEN - len(first_output))])
    if second is not None:
        buf = ''
        lines = 1
        for word in _sanitize_split(second):
            if len(buf) + len(word) > _SECOND_COLUMN_LEN:
                # Make sure to output an additional newline for this output since we broke lines
                add_nl_buffer = True

                # Append to our output buffer and set our working buffer to the word that wouldn't fit
                second_output += '{}\n{}'.format(buf, ''.join([' ' for _ in range(_FIRST_COLUMN_LEN)]))
                buf = word

                # Increase the number of lines - if there are too many break here.
                lines += 1
                if lines >= _MAX_SECOND_COLUMN_LINES:
                    buf = '{}...'.format(buf)
                    break

            elif len(buf) == 0:
                buf = word

            else:
                buf += ' {}'.format(word)

        if len(buf) > 0:
            second_output += buf

    return '{}{}{}'.format(first_output, second_output, '' if add_nl_buffer is False else '\n')
