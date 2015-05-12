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

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

_HAS_GST = True
try:
    from gi.repository import Gst
    Gst.init(None)
    Gst.parse_launch('espeak')
except:
    logging.error('Gst or the espeak plugin is not installed in the system.')
    _HAS_GST = False

from sugar3 import power

DEFAULT_PITCH = 0


DEFAULT_RATE = 0


_SAVE_TIMEOUT = 500


# This voice names are use dto allow the translation of the voice names.
# If espeak add new voices, we need update this list.

translated_espeak_voices = {
    'af': _('Afrikaans'),
    'an': _('Aragonese'),
    'bg': _('Bulgarian'),
    'bs': _('Bosnian'),
    'ca': _('Catalan'),
    'cs': _('Czech'),
    'cy': _('Welsh'),
    'da': _('Danish'),
    'de': _('German'),
    'el': _('Greek'),
    'en': _('Default'),
    'en_gb': _('English Britain'),
    'en_sc': _('English scottish'),
    'en_uk-north': _('English-north'),
    'en_uk-rp': _('English_rp'),
    'en_uk-wmids': _('English_wmids'),
    'en_us': _('English USA'),
    'en_wi': _('English west indies'),
    'eo': _('Esperanto'),
    'es': _('Spanish'),
    'es_la': _('Spanish latin american'),
    'et': _('Estonian'),
    'fa': _('Farsi'),
    'fa_pin': _('Farsi-pinglish'),
    'fi': _('Finnish'),
    'fr_be': _('French belgium'),
    'fr_fr': _('French'),
    'ga': _('Irish-gaeilge'),
    'grc': _('Greek-ancient'),
    'hi': _('Hindi'),
    'hr': _('Croatian'),
    'hu': _('Hungarian'),
    'hy': _('Armenian'),
    'hy_west': _('Armenian (west)'),
    'id': _('Indonesian'),
    'is': _('Icelandic'),
    'it': _('Italian'),
    'jbo': _('Lojban'),
    'ka': _('Georgian'),
    'kn': _('Kannada'),
    'ku': _('Kurdish'),
    'la': _('Latin'),
    'lt': _('Lithuanian'),
    'lv': _('Latvian'),
    'mk': _('Macedonian'),
    'ml': _('Malayalam'),
    'ms': _('Malay'),
    'ne': _('Nepali'),
    'nl': _('Dutch'),
    'no': _('Norwegian'),
    'pa': _('Punjabi'),
    'pl': _('Polish'),
    'pt_br': _('Portuguese (Brazil)'),
    'pt_pt': _('Portuguese (Portugal)'),
    'ro': _('Romanian'),
    'ru': _('Russian'),
    'sk': _('Slovak'),
    'sq': _('Albanian'),
    'sr': _('Serbian'),
    'sv': _('Swedish'),
    'sw': _('Swahili-test'),
    'ta': _('Tamil'),
    'tr': _('Turkish'),
    'vi': _('Vietnam'),
    'vi_hue': _('Vietnam_hue'),
    'vi_sgn': _('Vietnam_sgn'),
    'zh': _('Mandarin'),
    'zh_yue': _('Cantonese')
}


class SpeechManager(GObject.GObject):

    __gtype_name__ = 'SpeechManager'

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_FIRST, None, []),
        'pause': (GObject.SignalFlags.RUN_FIRST, None, []),
        'stop': (GObject.SignalFlags.RUN_FIRST, None, [])
    }

    MIN_PITCH = -100
    MAX_PITCH = 100

    MIN_RATE = -100
    MAX_RATE = 100

    def __init__(self, **kwargs):
        GObject.GObject.__init__(self, **kwargs)
        self._player = None
        if not self.enabled():
            return

        self._player = _GstSpeechPlayer()
        self._player.connect('play', self._update_state, 'play')
        self._player.connect('stop', self._update_state, 'stop')
        self._player.connect('pause', self._update_state, 'pause')
        self._default_voice_name = self._player.get_default_voice()
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

    def get_is_playing(self):
        return self._is_playing

    is_playing = GObject.property(type=bool, getter=get_is_playing,
                                  setter=None, default=False)

    def get_is_paused(self):
        return self._is_paused

    is_paused = GObject.property(type=bool, getter=get_is_paused,
                                 setter=None, default=False)

    def get_pitch(self):
        return self._pitch

    def get_rate(self):
        return self._rate

    def set_pitch(self, pitch):
        self._pitch = pitch
        if self._save_timeout_id != -1:
            GObject.source_remove(self._save_timeout_id)
        self._save_timeout_id = GObject.timeout_add(_SAVE_TIMEOUT, self.save)

    def set_rate(self, rate):
        self._rate = rate
        if self._save_timeout_id != -1:
            GObject.source_remove(self._save_timeout_id)
        self._save_timeout_id = GObject.timeout_add(_SAVE_TIMEOUT, self.save)

    def say_text(self, text, pitch=None, rate=None, lang_code=None):
        if pitch is None:
            pitch = self._pitch
        if rate is None:
            rate = self._rate
        if lang_code is None:
            voice_name = self._default_voice_name
        else:
            voice_name = self._player.get_all_voices()[lang_code]
        if text:
            logging.debug('PLAYING "%s" lang %s', text, voice_name)
            self._player.speak(pitch, rate, voice_name, text)

    def say_selected_text(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        clipboard.request_text(self.__primary_selection_cb, None)

    def pause(self):
        self._player.pause_sound_device()

    def restart(self):
        self._player.restart_sound_device()

    def stop(self):
        self._player.stop_sound_device()

    def __primary_selection_cb(self, clipboard, text, user_data):
        self.say_text(text)

    def save(self):
        self._save_timeout_id = -1
        # DEPRECATED
        from gi.repository import GConf
        client = GConf.Client.get_default()
        client.set_int('/desktop/sugar/speech/pitch', self._pitch)
        client.set_int('/desktop/sugar/speech/rate', self._rate)

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
        if self._player:
            return self._player.get_all_voices()
        return None

    def get_all_traslated_voices(self):
        if self._player:
            return self._player.get_all_voices()
        return None


class _GstSpeechPlayer(GObject.GObject):

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_FIRST, None, []),
        'pause': (GObject.SignalFlags.RUN_FIRST, None, []),
        'stop': (GObject.SignalFlags.RUN_FIRST, None, [])
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self._pipeline = None
        self._all_voices = None
        self._all_translated_voices = None

    def restart_sound_device(self):
        if self._pipeline is None:
            logging.debug('Trying to restart not initialized sound device')
            return

        power.get_power_manager().inhibit_suspend()
        self._pipeline.set_state(Gst.State.PLAYING)
        self.emit('play')

    def pause_sound_device(self):
        if self._pipeline is None:
            return

        self._pipeline.set_state(Gst.State.PAUSED)
        power.get_power_manager().restore_suspend()
        self.emit('pause')

    def stop_sound_device(self):
        if self._pipeline is None:
            return

        self._pipeline.set_state(Gst.State.NULL)
        power.get_power_manager().restore_suspend()
        self.emit('stop')

    def make_pipeline(self, command):
        if self._pipeline is not None:
            self.stop_sound_device()
            del self._pipeline

        self._pipeline = Gst.parse_launch(command)

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.__pipe_message_cb)

    def __pipe_message_cb(self, bus, message):
        if message.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            power.get_power_manager().restore_suspend()
            self.emit('stop')

    def speak(self, pitch, rate, voice_name, text):
        # TODO workaround for http://bugs.sugarlabs.org/ticket/1801
        if not [i for i in text if i.isalnum()]:
            return

        self.make_pipeline('espeak name=espeak ! autoaudiosink')
        src = self._pipeline.get_by_name('espeak')

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
            or 'default'
        logging.debug('Best voice for LANG %s seems to be %s',
                      locale, best)
        return best
