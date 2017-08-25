# -*- coding: utf-8 -*-
#!/usr/bin/env python

# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Speech API sample application using the streaming API.
NOTE: This module requires the additional dependency `pyaudio`. To install
using pip:
    pip install pyaudio
Example usage:
    python transcribe_streaming_mic.py
"""

# [START import_libraries]
from __future__ import division

import re
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue
import playsound

import translation_en_to_ko
import translation_ko_to_en
import translation_en_to_ja
import translation_en_to_cn
import translation_en_to_fr
import translation_en_to_sp
import translation_en_to_de
import translation_en_to_ru
import translation_en_to_pt
import translation_en_to_nl
import translation_en_to_it
import translation_ja_to_en
import translation_cn_to_en
import translation_fr_to_en
import translation_de_to_en
import translation_sp_to_en
import translation_ru_to_en
import translation_pt_to_en
import translation_nl_to_en
import translation_it_to_en
# [END import_libraries]

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)
# [END audio_stream]


textLists = [
    ['English to Korean', 'Say!', 1],
    ['English Korean', 'Say!', 1],
    ['Korean to English', 'Say!', 2],
    ['Korean English', 'Say!', 2],
    ['English to Japanese', 'Say!', 3],
    ['English Japanese', 'Say!', 3],
    ['English to Chinese', 'Say!', 4],
    ['English Chinese', 'Say!', 4],
    ['English to French', 'Say!', 5],
    ['English French', 'Say!', 5],
    ['English to Spanish', '', 6],
    ['English Spanish', '', 6],
    ['English to German', '', 7],
    ['English German', '', 7],
    ['English to Russian', '', 8],
    ['English Russian', '', 8],
    ['English to Portuguese', '', 9],
    ['English Portuguese', '', 9],
    ['English to Dutch', '', 10],
    ['English Dutch', '', 10],
    ['English to Italian', '', 11],
    ['English Italian', '', 11],
    ['Japanese to English', '', 12],
    ['Japanese English', '', 12],
    ['Chinese to English', '', 13],
    ['Chinese English', '', 13],
    ['French to English', '', 14],
    ['French English', '', 14],
    ['German to English', '', 15],
    ['German English', '', 15],
    ['Spanish to English', '', 16],
    ['Spanish English', '', 16],
    ['Russian to English', '', 17],
    ['Russian English', '', 17],
    ['Portuguese to English', '', 18],
    ['Portuguese English', '', 18],
    ['Dutch to English', '', 19],
    ['Dutch English', '', 19],
    ['Italian to English', '', 20],
    ['Italian English', '', 20]]

    

def TranslationSet(stt):
    text = stt.strip()

    for textList in textLists:
        if text == textList[0]:
            return textList[2]



def listen_print_loop(responses):
    """Iterates through server responses and prints them.
    The responses passed is a generator that will block until a response
    is provided by the server.
    Each response may contain multiple results, and each result may contain
    multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
    print only the transcription for the top alternative of the top result.
    In this case, responses are provided for interim results as well. If the
    response is an interim one, print a line feed at the end of it, to allow
    the next result to overwrite it, until the response is a final one. For the
    final one, print a newline to preserve the finalized transcription.
    """
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        # There could be multiple results in each response.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            if TranslationSet(transcript) > 0 :
                return TranslationSet(transcript)

            # Exit recognition if any of the transcribed phrases could be
            # one of our keywords.
            if re.search(r'\b(exit|quit)\b', transcript, re.I):
                print('Exiting..')
                break
            

            num_chars_printed = 0

def kill():
    return 
    

def main():
    # Play information sound.
    playsound.playsound('start_ko.mp3')
    playsound.playsound('start_en.mp3')
    
    # See http://g.co/cloud/speech/docs/languages
    # for a list of supported languages.
    language_code = 'en-US'  # a BCP-47 language tag

    client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)

        # Now, put the transcription responses to use.
	var = listen_print_loop(responses)
		

    if var == 1 :
        translation_en_to_ko.main()
    elif var == 2:
        translation_ko_to_en.main()
    elif var == 3:
        translation_en_to_ja.main()
    elif var == 4: 
        translation_en_to_cn.main()
    elif var == 5:
        translation_en_to_fr.main()
    elif var == 6:
        translation_en_to_sp.main()
    elif var == 7:
        translation_en_to_de.main()
    elif var == 8:
        translation_en_to_ru.main()
    elif var == 9:
        translation_en_to_pt.main()
    elif var == 10:
        translation_en_to_nl.main()
    elif var == 11:
        translation_en_to_it.main()
    elif var == 12:
        translation_ja_to_en.main()
    elif var == 13:
        translation_cn_to_en.main()
    elif var == 14:
        translation_fr_to_en.main()
    elif var == 15:
        translation_de_to_en.main()
    elif var == 16:
        translation_sp_to_en.main()
    elif var == 17:
        translation_ru_to_en.main()
    elif var == 18:
        translation_pt_to_en.main()
    elif var == 19:
        translation_nl_to_en.main()
    elif var == 20:
        translation_it_to_en.main()



if __name__ == '__main__':
    main()
