import numpy as np
import pretty_midi
from scipy.io.wavfile import write
from pydantic import BaseModel
from typing import List
import boto3
import datetime as dt
import ffmpeg
import os
from fastapi import FastAPI

class Item(BaseModel):
    filename: str
    type: str

sf_path={"piano": "GeneralUserMuseScore.sf2", "bass": "JazzClubBass.sf2", "drum" : "GeneralUserMuseScore.sf2"}
waveforms = []
s3 = boto3.client('s3')

app = FastAPI()

@app.post("/beats/stack", status_code=200)
def stack_beats(items: List[Item]):
    stack_name = "voice_" + dt.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    for item in items:
        # stack 타입 비트에 한번 더 병합을 시도할 경우 수정
        # if item.type == 'stack':
        #     s3.download_file("cau-tensecond", f"beat/{item.type}/{item.filename}.m4a", f"{item.filename}.m4a")
        #     y, sr = librosa.load(f"{item.filename}.m4a")
        #     print(len(y))
        #     y = y.astype(np.float64)
        #     waveforms.append(y)
        #     os.remove(f"{item.filename}.m4a")
        #     continue
        s3.download_file("cau-tensecond", f"midi/{item.type}/{item.filename}.mid", f"{item.filename}.mid")
        midi = pretty_midi.PrettyMIDI(f"{item.filename}.mid")
        audio = midi.fluidsynth(sf2_path=sf_path[item.type])
        waveforms.append(audio)
        os.remove(f"{item.filename}.mid")
    synthesized = np.zeros(np.max([w.shape[0] for w in waveforms]))
    for waveform in waveforms:
        synthesized[:waveform.shape[0]] += waveform
    synthesized /= np.abs(synthesized).max()
    write(f"{stack_name}.wav", 44100, synthesized)
    ffmpeg.input(f"{stack_name}.wav").output(f"{stack_name}.m4a").run()
    s3.upload_file(f"{stack_name}.m4a", "cau-tensecond", f"beat/stack/{stack_name}.m4a")
    os.remove(f"{stack_name}.wav")
    os.remove(f"{stack_name}.m4a")
    return stack_name