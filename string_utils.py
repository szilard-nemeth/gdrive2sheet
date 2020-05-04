import unicodedata
import string


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