from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import datetime as dt
from app.utils import *
from app.voice2instrument import voice2midi
import librosa

app = FastAPI()
s3 = s3_credential()
download_sf(s3)
sf_path = match_instrument_sf_path()


class Voice(BaseModel):
    filename: str


class Beat(BaseModel):
    filename: str
    type: str


@app.post("/beats/convert", status_code=200)
def voice2instrument(voice: Voice):
    y, sr = librosa.load(download_voice(s3, voice.filename))
    instrument_midi = voice2midi(y)
    upload_midi(s3, voice.filename, instrument_midi)
    instrument_beat = convert_beat(instrument_midi, sf_path)
    upload_beat(s3, voice.filename, instrument_beat)
    return voice.filename


@app.post("/beats/stack", status_code=200)
def stack_beats(beats: List[Beat]):
    waveforms = []
    stacked_name = "voice_" + dt.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    stacked_midi = pretty_midi.PrettyMIDI()
    for beat in beats:
        midi = download_midi(s3, beat.type, beat.filename)
        for instrument in midi.instruments:
            audio = instrument.fluidsynth(sf2_path=sf_path[instrument.name])
            waveforms.append(audio)
            stacked_midi.instruments.append(instrument)
    stacked_audio = stack_audio(waveforms)
    upload_stacked_beat(s3, stacked_name, stacked_audio)
    upload_stacked_midi(s3, stacked_name, stacked_midi)
    return stacked_name
