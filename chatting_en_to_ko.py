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
import os
import time
import translation_stt_tts

import RPi.GPIO as GPIO

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from google.cloud import translate
import pyaudio
from six.moves import queue
import six
from gtts import gTTS
import playsound

translate_client = translate.Client()
target = 'ko'
# [END import_libraries]

pin1 = 18
pin2 = 24

secret = 1

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

EXIT = 0


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
        #명령어    대답    종료 리턴값
        [u'exit',     'good bye',       0],
	[u'translation', 'abc' , 2],
        [u'hello',       'hello',        1],
        [u"what's your name", 'I am Suho, maschote of pyeongchang olympic',      1],
        [u'how old are you',     "That is secret", 1],
        [u'where is the Olympic Stadium', 'It is near the GoWeon stadium',1],
        [u'can you dance','Guess what',3],
        [u'where are you from','I am from pyeongchang, dreams of many people',1],
        [u"what's your hobby",'SnowBorad is my favorite',1],
        [u'where is ski jump center', 'That is located in the Alphensia Resort',1],
	[u'when ski game starts', 'Tomorrow noon. never be late', 1], 
	[u'where is best restaurant nearby', 'Millak restaurant is best. why do not you just give it a try', 1],
        [u'recommend me korean food','Bulgogi is the best.',1]]

def dance() :
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin1, GPIO.OUT)
    GPIO.setup(pin2, GPIO.OUT)

    p = GPIO.PWM(pin1, 50)
    q = GPIO.PWM(pin2, 50)

    p.start(7.5)
    q.start(7.5)

    i = 0

    while i < 10 :
        p.ChangeDutyCycle(12.5)
        time.sleep(1)
        q.ChangeDutyCycle(2.5)
        time.sleep(1)
        p.ChangeDutyCycle(7.5)
        q.ChangeDutyCycle(7.5)
        time.sleep(2)
        p.ChangeDutyCycle(2.5)
        time.sleep(1)
        q.ChangeDutyCycle(12.5)
        time.sleep(1)
        p.ChangeDutyCycle(7.5)
        q.ChangeDutyCycle(7.5)
        time.sleep(2)

    p.stop()
    q.stop()
    GPIO.cleanup()   


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

    # A class for counting the number of text to speech files.
    class numTTS:
        num = 0

    num_ttsFile = numTTS
    
    for response in responses:
        if EXIT == 1 :
            return -1

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
            # Remove spaces of transcript text.  
            text = transcript.strip()
            text.lower()
            print(text + overwrite_chars)

            answer = "Null"

            # Find input question in prepared text list
            # and print correct answer for the question.
            for textList in textLists:
                if text == textList[0]:
                    answer = textList[1]
                    print(textList[1])

            # If text list's return value is 0,
            # terminate program.
            if textList[2] == 0  :
                print('Chat feature terminated.')
                return 0

        if answer == 'abc' :
            return 125

        if answer == "Null" :
            tts2 = gTTS(text = 'Please talk again', lang='en')
            ttsFile2 = 'Null.mp3'
            tts2.save(ttsFile2)
            playsound.playsound('Null.mp3')
            os.remove(ttsFile2)

            num_chars_printed = 0
            return

        if secret == 1 :
            dance()
            return

            # Save the answer into an mp3 file by using
            # Google text to speech API, gtts.
            # And play it with playsound package
        tts = gTTS(text = answer, lang='en')
        ttsFile = 'TTS' + str(num_ttsFile.num) + '.mp3'
        tts.save(ttsFile)
        playsound.playsound(ttsFile,True)
        num_ttsFile.num += 1

        # Remove tts file because of permisson issue.
        os.remove(ttsFile)

        # Exit recognition if any of the transcribed phrases could be
        # one of our keywords.
        if re.search(r'\b(exit|quit)\b', transcript, re.I):
            print('Exiting..')
            break

        num_chars_printed = 0
        return


def kill():
    EXIT = 1
    return 0
	

def main():
    EXIT = 0
    # Play information sound.
    playsound.playsound('Chatting_ko_start.mp3')
    playsound.playsound('Chatting_en_start.mp3')
    
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

    if var == 125 :
        translation_stt_tts.main()



if __name__ == '__main__':
    main()
