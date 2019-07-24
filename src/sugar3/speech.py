# Copyright (C) 2011 One Laptop Per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import logging
from gettext import gettext as _

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

_HAS_GST = True
try:
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    Gst.parse_launch('espeak')
except BaseException:
    logging.error('Gst or the espeak plugin is not installed in the system.')
    _HAS_GST = False

from sugar3 import power

DEFAULT_PITCH = 0


DEFAULT_RATE = 0


_SAVE_TIMEOUT = 500


# This voice names are use dto allow the translation of the voice names.
# If espeak add new voices, we need update this list.

translated_espeak_voices = {
    # Translators:  http://en.wikipedia.org/wiki/Afrikaans_language
    'af': _('Afrikaans'),
    # Translators:  http://en.wikipedia.org/wiki/Aragonese_language
    'an': _('Aragonese'),
    # Translators:  http://en.wikipedia.org/wiki/Bulgarian_language
    'bg': _('Bulgarian'),
    # Translators:  http://en.wikipedia.org/wiki/Bosnian_language
    'bs': _('Bosnian'),
    # Translators:  http://en.wikipedia.org/wiki/Catalan_language
    'ca': _('Catalan'),
    # Translators:  http://en.wikipedia.org/wiki/Czech_language
    'cs': _('Czech'),
    # Translators:  http://en.wikipedia.org/wiki/Welsh_language
    'cy': _('Welsh'),
    # Translators:  http://en.wikipedia.org/wiki/Danish_language
    'da': _('Danish'),
    # Translators:  http://en.wikipedia.org/wiki/German_language
    'de': _('German'),
    # Translators:  http://en.wikipedia.org/wiki/Modern_Greek
    'el': _('Greek'),
    'en': _('English'),
    # Translators:  http://en.wikipedia.org/wiki/British_English
    'en_gb': _('English Britain'),
    # Translators:  http://en.wikipedia.org/wiki/Scottish_English
    'en_sc': _('English scottish'),
    'en_uk-north': _('English-north'),
    # Translators:  http://en.wikipedia.org/wiki/Received_Pronunciation
    'en_uk-rp': _('English_rp'),
    # Translators:  http://en.wikipedia.org/wiki/West_Midlands_English
    'en_uk-wmids': _('English_wmids'),
    # Translators:  http://en.wikipedia.org/wiki/American_English
    'en_us': _('English USA'),
    # Translators:  http://en.wikipedia.org/wiki/Caribbean_English
    'en_wi': _('English West Indies'),
    # Translators:  http://en.wikipedia.org/wiki/Esperanto
    'eo': _('Esperanto'),
    # Translators:  http://en.wikipedia.org/wiki/Spanish_language
    'es': _('Spanish'),
    'es_la': _('Spanish latin american'),
    # Translators:  http://en.wikipedia.org/wiki/Estonian_language
    'et': _('Estonian'),
    # Translators:  http://en.wikipedia.org/wiki/Persian_language
    'fa': _('Farsi'),
    # Translators:  http://en.wikipedia.org/wiki/Fingilish
    'fa_pin': _('Farsi-pinglish'),
    # Translators:  http://en.wikipedia.org/wiki/Finnish_language
    'fi': _('Finnish'),
    # Translators:  http://en.wikipedia.org/wiki/Belgian_French
    'fr_be': _('French belgium'),
    # Translators:  http://en.wikipedia.org/wiki/French_language
    'fr_fr': _('French'),
    # Translators:  http://en.wikipedia.org/wiki/Irish_language
    'ga': _('Irish-gaeilge'),
    # Translators:  http://en.wikipedia.org/wiki/Ancient_Greek
    'grc': _('Greek-ancient'),
    # Translators:  http://en.wikipedia.org/wiki/Hindi
    'hi': _('Hindi'),
    # Translators:  http://en.wikipedia.org/wiki/Croatian_language
    'hr': _('Croatian'),
    # Translators:  http://en.wikipedia.org/wiki/Hungarian_language
    'hu': _('Hungarian'),
    # Translators:  http://en.wikipedia.org/wiki/Armenian_language
    'hy': _('Armenian'),
    # Translators:  http://en.wikipedia.org/wiki/Western_Armenian
    'hy_west': _('Armenian (west)'),
    # Translators:  http://en.wikipedia.org/wiki/Indonesian_language
    'id': _('Indonesian'),
    # Translators:  http://en.wikipedia.org/wiki/Icelandic_language
    'is': _('Icelandic'),
    # Translators:  http://en.wikipedia.org/wiki/Italian_language
    'it': _('Italian'),
    # Translators:  http://en.wikipedia.org/wiki/Lojban
    'jbo': _('Lojban'),
    # Translators:  http://en.wikipedia.org/wiki/Georgian_language
    'ka': _('Georgian'),
    # Translators:  http://en.wikipedia.org/wiki/Kannada_language
    'kn': _('Kannada'),
    # Translators:  http://en.wikipedia.org/wiki/Kurdish_language
    'ku': _('Kurdish'),
    # Translators:  http://en.wikipedia.org/wiki/Latin
    'la': _('Latin'),
    # Translators:  http://en.wikipedia.org/wiki/Lithuanian_language
    'lt': _('Lithuanian'),
    # Translators:  http://en.wikipedia.org/wiki/Latvian_language
    'lv': _('Latvian'),
    # Translators:  http://en.wikipedia.org/wiki/Macedonian_language
    'mk': _('Macedonian'),
    # Translators:  http://en.wikipedia.org/wiki/Malayalam
    'ml': _('Malayalam'),
    # Translators:  http://en.wikipedia.org/wiki/Malay_language
    'ms': _('Malay'),
    # Translators:  http://en.wikipedia.org/wiki/Nepali_language
    'ne': _('Nepali'),
    # Translators:  http://en.wikipedia.org/wiki/Dutch_language
    'nl': _('Dutch'),
    # Translators:  http://en.wikipedia.org/wiki/Norwegian_language
    'no': _('Norwegian'),
    # Translators:  http://en.wikipedia.org/wiki/Punjabi_language
    'pa': _('Punjabi'),
    # Translators:  http://en.wikipedia.org/wiki/Polish_language
    'pl': _('Polish'),
    # Translators:  http://en.wikipedia.org/wiki/Brazilian_Portuguese
    'pt_br': _('Portuguese (Brazil)'),
    # Translators:  http://en.wikipedia.org/wiki/Portuguese_language
    'pt_pt': _('Portuguese (Portugal)'),
    # Translators:  http://en.wikipedia.org/wiki/Romanian_language
    'ro': _('Romanian'),
    # Translators:  http://en.wikipedia.org/wiki/Russian_language
    'ru': _('Russian'),
    # Translators:  http://en.wikipedia.org/wiki/Slovak_language
    'sk': _('Slovak'),
    # Translators:  http://en.wikipedia.org/wiki/Albanian_language
    'sq': _('Albanian'),
    # Translators:  http://en.wikipedia.org/wiki/Serbian_language
    'sr': _('Serbian'),
    # Translators:  http://en.wikipedia.org/wiki/Swedish_language
    'sv': _('Swedish'),
    # Translators:  http://en.wikipedia.org/wiki/Swahili_language
    'sw': _('Swahili'),
    # Translators:  http://en.wikipedia.org/wiki/Tamil_language
    'ta': _('Tamil'),
    # Translators:  http://en.wikipedia.org/wiki/Turkish_language
    'tr': _('Turkish'),
    # Translators:  http://en.wikipedia.org/wiki/Vietnamese_language
    'vi': _('Vietnam'),
    'vi_hue': _('Vietnam_hue'),
    'vi_sgn': _('Vietnam_sgn'),
    # Translators:  http://en.wikipedia.org/wiki/Mandarin_Chinese
    'zh': _('Mandarin'),
    # Translators:  http://en.wikipedia.org/wiki/Cantonese
    'zh_yue': _('Cantonese')
}


class SpeechManager(GObject.GObject):

    __gtype_name__ = 'SpeechManager'

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_FIRST, None, []),
        'pause': (GObject.SignalFlags.RUN_FIRST, None, []),
        'stop': (GObject.SignalFlags.RUN_FIRST, None, []),
        'mark': (GObject.SignalFlags.RUN_FIRST, None, [str])
    }

    MIN_PITCH = -100
    MAX_PITCH = 100

    MIN_RATE = -100
    MAX_RATE = 100

    def __init__(self, **kwargs):
        GObject.GObject.__init__(self, **kwargs)
        self.player = None
        if not self.enabled():
            return

        self.player = GstSpeechPlayer()
        self.player.connect('play', self._update_state, 'play')
        self.player.connect('stop', self._update_state, 'stop')
        self.player.connect('pause', self._update_state, 'pause')
        self.player.connect('mark', self._mark_cb)
        self._default_voice_name = self.player.get_default_voice()
        self._pitch = DEFAULT_PITCH
        self._rate = DEFAULT_RATE
        self._is_playing = False
        self._is_paused = False
        self._save_timeout_id = -1
        self.restore()

    def enabled(self):
        return _HAS_GST

    def _update_state(self, player, signal):
        self._is_playing = (signal == 'play')
        self._is_paused = (signal == 'pause')
        self.emit(signal)

    def _mark_cb(self, player, value):
        self.emit('mark', value)

    def get_is_playing(self):
        return self._is_playing

    is_playing = GObject.Property(type=bool, getter=get_is_playing,
                                  setter=None, default=False)

    def get_is_paused(self):
        return self._is_paused

    is_paused = GObject.Property(type=bool, getter=get_is_paused,
                                 setter=None, default=False)

    def get_pitch(self):
        return self._pitch

    def get_rate(self):
        return self._rate

    def set_pitch(self, pitch):
        self._pitch = pitch
        if self._save_timeout_id != -1:
            GLib.source_remove(self._save_timeout_id)
        self._save_timeout_id = GLib.timeout_add(_SAVE_TIMEOUT, self.save)

    def set_rate(self, rate):
        self._rate = rate
        if self._save_timeout_id != -1:
            GLib.source_remove(self._save_timeout_id)
        self._save_timeout_id = GLib.timeout_add(_SAVE_TIMEOUT, self.save)

    def say_text(self, text, pitch=None, rate=None, lang_code=None):
        if pitch is None:
            pitch = self._pitch
        if rate is None:
            rate = self._rate
        if lang_code is None:
            voice_name = self._default_voice_name
        else:
            voice_name = self.player.get_all_voices()[lang_code]
        if text:
            logging.error(
                'PLAYING %r lang %r pitch %r rate %r',
                text,
                voice_name,
                pitch,
                rate)
            self.player.speak(pitch, rate, voice_name, text)

    def say_selected_text(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        clipboard.request_text(self.__primary_selection_cb, None)

    def pause(self):
        self.player.pause_sound_device()

    def restart(self):
        self.player.restart_sound_device()

    def stop(self):
        self.player.stop_sound_device()

    def __primary_selection_cb(self, clipboard, text, user_data):
        self.say_text(text)

    def save(self):
        self._save_timeout_id = -1

        settings = Gio.Settings('org.sugarlabs.speech')
        settings.set_int('pitch', self._pitch)
        settings.set_int('rate', self._rate)
        logging.debug('saving speech configuration pitch %s rate %s',
                      self._pitch, self._rate)
        return False

    def restore(self):
        settings = Gio.Settings('org.sugarlabs.speech')
        self._pitch = settings.get_int('pitch')
        self._rate = settings.get_int('rate')
        logging.debug('loading speech configuration pitch %s rate %s',
                      self._pitch, self._rate)

    def get_all_voices(self):
        if self.player:
            return self.player.get_all_voices()
        return None

    def get_all_traslated_voices(self):
        """ deprecated after 0.112, due to method name spelling error """
        if self.player:
            return self.player.get_all_translated_voices()
        return None

    def get_all_translated_voices(self):
        if self.player:
            return self.player.get_all_translated_voices()
        return None


class GstSpeechPlayer(GObject.GObject):

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_FIRST, None, []),
        'pause': (GObject.SignalFlags.RUN_FIRST, None, []),
        'stop': (GObject.SignalFlags.RUN_FIRST, None, []),
        'mark': (GObject.SignalFlags.RUN_FIRST, None, [str])
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.pipeline = None
        self._all_voices = None
        self._all_translated_voices = None

    def restart_sound_device(self):
        if self.pipeline is None:
            logging.debug('Trying to restart not initialized sound device')
            return

        power.get_power_manager().inhibit_suspend()
        self.pipeline.set_state(Gst.State.PLAYING)
        self.emit('play')

    def pause_sound_device(self):
        if self.pipeline is None:
            return

        self.pipeline.set_state(Gst.State.PAUSED)
        power.get_power_manager().restore_suspend()
        self.emit('pause')

    def stop_sound_device(self):
        if self.pipeline is None:
            return

        self.pipeline.set_state(Gst.State.NULL)
        power.get_power_manager().restore_suspend()
        self.emit('stop')

    def make_pipeline(self, command):
        if self.pipeline is not None:
            self.stop_sound_device()
            del self.pipeline

        self.pipeline = Gst.parse_launch(command)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.__pipe_message_cb)

    def __pipe_message_cb(self, bus, message):
        if message.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            power.get_power_manager().restore_suspend()
            self.emit('stop')
        elif message.type is Gst.MessageType.ELEMENT and \
                message.get_structure().get_name() == 'espeak-mark':
            mark_value = message.get_structure().get_value('mark')
            self.emit('mark', mark_value)

    def speak(self, pitch, rate, voice_name, text):
        # TODO workaround for http://bugs.sugarlabs.org/ticket/1801
        if not [i for i in text if i.isalnum()]:
            return

        self.make_pipeline('espeak name=espeak ! autoaudiosink')
        src = self.pipeline.get_by_name('espeak')

        src.props.text = text
        src.props.pitch = pitch
        src.props.rate = rate
        src.props.voice = voice_name
        src.props.track = 2  # track for marks

        self.restart_sound_device()

    def get_all_voices(self):
        if self._all_voices is not None:
            return self._all_voices
        self._init_voices()
        return self._all_voices

    def get_all_translated_voices(self):
        if self._all_translated_voices is not None:
            return self._all_translated_voices
        self._init_voices()
        return self._all_translated_voices

    def _init_voices(self):
        self._all_voices = {}
        self._all_translated_voices = {}

        for voice in Gst.ElementFactory.make('espeak', None).props.voices:
            name, language, dialect = voice
            if dialect != 'none':
                lang_code = language + '_' + dialect
            else:
                lang_code = language

            self._all_voices[lang_code] = name
            if lang_code in translated_espeak_voices:
                self._all_translated_voices[lang_code] = \
                    translated_espeak_voices[lang_code]
            else:
                self._all_translated_voices[lang_code] = name

    def get_default_voice(self):
        """Try to figure out the default voice, from the current locale ($LANG)
           Fall back to espeak's voice called Default."""
        voices = self.get_all_voices()

        locale = os.environ.get('LANG', '')
        language_location = locale.split('.', 1)[0].lower()
        language = language_location.split('_')[0]
        # if the language is es but not es_es default to es_la (latin voice)
        if language == 'es' and language_location != 'es_es':
            language_location = 'es_la'

        best = voices.get(language_location) or voices.get(language) \
            or 'english'
        return best
