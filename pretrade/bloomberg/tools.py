import sys


def progress(count, total, status=None):
    bar_length = 100
    filled_length = int(bar_length * count/float(total))
    percents = round(100 * count/float(total), 2)

    bar = u'\u25A0' * filled_length + '_' * (bar_length - filled_length)
    if status is not None:
        sys.stdout.write(u'{}  {}% - {}\r'.format(bar, percents, status))
    else:
        sys.stdout.write(u'{}  {}%\r'.format(bar, percents))
    sys.stdout.flush()
    if count >= total:
        print('')
