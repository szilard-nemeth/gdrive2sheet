import errno
import os
import string
import unicodedata

from tabulate import tabulate


def auto_str(cls):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    cls.__str__ = __str__
    return cls


class StringUtils:

  @staticmethod
  def replace_special_chars(unistr):
    if not isinstance(unistr, unicode):
      print("Object expected to be unicode: " + str(unistr))
      return str(unistr)
    normalized = unicodedata.normalize('NFD', unistr).encode('ascii', 'ignore')
    normalized = normalized.decode('utf-8')
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    valid_title = ''.join(c for c in normalized if c in valid_chars)
    return valid_title


class FileUtils:
    @classmethod
    def ensure_dir_created(cls, dirname):
        """
    Ensure that a named directory exists; if it does not, attempt to create it.
    """
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        return dirname


class ResultPrinter:
    def __init__(self, data, headers):
        self.data = data
        self.headers = headers

    def print_table(self):
        print(tabulate(self.data, self.headers, tablefmt="fancy_grid"))

    def print_table_html(self):
        print(tabulate(self.data, self.headers, tablefmt="html"))