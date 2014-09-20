import locale
import gettext
from gi.repository import Gio
from jarabe import config
import os
import logging
import subprocess


class Globalization:
    def getPreferredLanguage(self, args, parent, request):
        preferred_language = get_preferred_language()
        logging.error("The preferred_language : %s", preferred_language)
        parent._client.send_result(request, {"value": preferred_language})

    def getLocaleName(self, args, parent, request):
        locale_name = get_locale_name()
        logging.error("The preferred_language : %s", locale_name)
        parent._client.send_result(request, {"value": locale_name})


"""
def setup_locale():

    # NOTE: This needs to happen early because some modules register
    # translatable strings in the module scope.
    gettext.bindtextdomain('sugar', config.locale_path)
    gettext.bindtextdomain('sugar-toolkit-gtk3', config.locale_path)
    gettext.textdomain('sugar')

    settings = Gio.Settings('org.sugarlabs.date')
    timezone = settings.get_string('timezone')
    if timezone is not None and timezone:
        os.environ['TZ'] = timezone
"""


def read_all_languages(locale_name):
    logging.error("in the function - read_all_languages")
    fdp = subprocess.Popen(['locale', '-av'], stdout=subprocess.PIPE)
    lines = fdp.stdout.read().split('\n')
    locales = []
    flag_locale_found = 0

    for line in lines:
        if line.find('locale:') != -1:
            locale = line.split()[1]
            logging.error(locale)
            logging.error(locale_name)
            if locale_name.find(locale) != -1:
                flag_locale_found = 1
            else:
                flag_locale_found = 0
        elif line.find('language |') != -1:
            if flag_locale_found == 1:
                lang = line.lstrip('language |')
                return lang
            # lang = line.lstrip('language |')
            # Sometimes language is a language code, not the language name
            # if len(lang) <= 3:
            # lang = title.split()[0]

    return None


def get_locale_name():

    # setup_locale()
    logging.error(os.environ.get('HOME'))
    path = os.path.join(os.environ.get('HOME'), '.i18n')
    fd = open(path)
    locale_name = None
    lines = fd.readlines()
    for line in lines:
        if line.find('LANGUAGE=') != -1:
            string_language = line.split("=")
            locale_name = string_language[1]

    logging.error("locale_name= %s", locale_name)
    str_language_file = fd.read()
    fd.close()
    logging.error("On reading language file : %s", str_language_file)

    _default_lang = '%s.%s' % locale.getdefaultlocale()
    logging.error("default language : %s", _default_lang)

    return locale_name


def get_preferred_language():
    _default_lang = '%s.%s' % locale.getdefaultlocale()

    preferred_language = read_all_languages(_default_lang)
    logging.error("in get_preferred_language , the language:")
    logging.error(preferred_language)
    return preferred_language
