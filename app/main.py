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
    upload_midi(s3, voice.filename, instrument_midi, sf_path)
    return voice.filename


@app.post("/beats/stack", status_code=200)
def stack_beats(beats: List[Beat]):
    waveforms = []
    stack_name = "voice_" + dt.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    for beat in beats:
        # stack 타입 비트에 한번 더 병합을 시도할 경우 추가 예정
        midi = download_midi(s3, beat.type, beat.filename)
        audio = midi.fluidsynth(sf2_path=sf_path[beat.type])
        waveforms.append(audio)
    stacked_audio = stack_audio(waveforms)
    upload_stacked_audio(s3, stack_name, stacked_audio)
    return stack_name