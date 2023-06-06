import boto3
from botocore.exceptions import ClientError
import os
import io
from pydub import AudioSegment
from scipy.io.wavfile import write
import ffmpeg
import pretty_midi
import numpy as np
from fastapi import HTTPException

bucket_name = "cau-tensecond"


def s3_credential():
    s3 = boto3.client('s3',
                      aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                      aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
    return s3


def download_sf(s3):
    sf_dir = "../soundfont"
    if not os.path.exists(sf_dir):
        os.makedirs(sf_dir)
    if not os.path.exists(os.path.join(sf_dir, "GeneralUserMuseScore.sf2")):
        try:
            s3.download_file(bucket_name, "soundfont/GeneralUserMuseScore.sf2", os.path.join(sf_dir, "GeneralUserMuseScore.sf2"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise HTTPException(status_code=400,
                                    detail="soundfont/GeneralUserMuseScore.sf2 key does not exist in the S3 bucket")
    if not os.path.exists(os.path.join(sf_dir, "JazzClubBass.sf2")):
        try:
            s3.download_file(bucket_name, "soundfont/JazzClubBass.sf2", os.path.join(sf_dir, "JazzClubBass.sf2"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise HTTPException(status_code=400,
                                    detail="soundfont/JazzClubBass.sf2 key does not exist in the S3 bucket")


def match_instrument_sf_path():
    sf_dir = "../soundfont"
    match = {"piano": os.path.join(sf_dir, "GeneralUserMuseScore.sf2"), "bass": os.path.join(sf_dir, "JazzClubBass.sf2"), "drum" : os.path.join(sf_dir, "GeneralUserMuseScore.sf2")}
    return match


def download_voice(s3, filename):
    try:
        response = s3.get_object(Bucket=bucket_name, Key=f"voice/{filename}.m4a")
        audio_data = response['Body'].read()
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format='m4a')
        audio = audio.export(format='wav')
        audio_bytes = audio.read()
        return io.BytesIO(audio_bytes)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=400, detail=f"voice/{filename} key does not exist in the S3 bucket")


def download_midi(s3, type, filename):
    try:
        s3.download_file("cau-tensecond", f"midi/{type}/{filename}.mid", f"{filename}.mid")
        midi = pretty_midi.PrettyMIDI(f"{filename}.mid")
        os.remove(f"{filename}.mid")
        return midi
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise HTTPException(status_code=400, detail=f"midi/{type}/{filename} key does not exist in the S3 bucket")


def convert_beat(instrument_midi, sf_path):
    instrument_beats = {}
    for instrument, midi in instrument_midi.items():
        beat = midi.fluidsynth(sf2_path=sf_path[instrument])
        instrument_beats[instrument] = beat
    return instrument_beats


def upload_beat(s3, filename, instrument_beat):
    for instrument, beat in instrument_beat.items():
        write(f"{filename}.wav", 44100, beat)
        ffmpeg.input(f"{filename}.wav").output(f"{filename}.m4a").run()
        s3.upload_file(f"{filename}.m4a", bucket_name, f"beat/{instrument}/{filename}.m4a")
        os.remove(f"{filename}.wav")
        os.remove(f"{filename}.m4a")


def upload_midi(s3, filename, instrument_midi):
    for instrument, midi in instrument_midi.items():
        midi_file = io.BytesIO()
        midi.write(midi_file)
        midi_file.seek(0)
        s3.upload_fileobj(midi_file, bucket_name, f"midi/{instrument}/{filename}.mid")


def stack_audio(waveforms):
    stacked_waveform = np.zeros(np.max([w.shape[0] for w in waveforms]))
    for waveform in waveforms:
        stacked_waveform[:waveform.shape[0]] += waveform
    stacked_waveform /= np.abs(stacked_waveform).max()
    return stacked_waveform


def upload_stacked_beat(s3, filename, stacked_audio):
    write(f"{filename}.wav", 44100, stacked_audio)
    ffmpeg.input(f"{filename}.wav").output(f"{filename}.m4a").run()
    s3.upload_file(f"{filename}.m4a", bucket_name, f"beat/stack/{filename}.m4a")
    os.remove(f"{filename}.wav")
    os.remove(f"{filename}.m4a")


def upload_stacked_midi(s3, filename, stacked_midi):
    midi_file = io.BytesIO()
    stacked_midi.write(midi_file)
    midi_file.seek(0)
    s3.upload_fileobj(midi_file, bucket_name, f"midi/stack/{filename}.mid")
