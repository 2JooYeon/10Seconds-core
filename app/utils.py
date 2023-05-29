import boto3
import os
import io
from pydub import AudioSegment
from scipy.io.wavfile import write
import ffmpeg
import pretty_midi
import numpy as np

bucket_name = "cau-tensecond"


def s3_credential():
    s3 = boto3.client('s3',
                      aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                      aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
    return s3


def match_instrument_sf_path():
    sf_dir = "../soundfont"
    match = {"piano": os.path.join(sf_dir, "GeneralUserMuseScore.sf2"), "bass": os.path.join(sf_dir, "JazzClubBass.sf2"), "drum" : os.path.join(sf_dir, "GeneralUserMuseScore.sf2")}
    return match


def stack_audio(waveforms):
    stacked_waveform = np.zeros(np.max([w.shape[0] for w in waveforms]))
    for waveform in waveforms:
        stacked_waveform[:waveform.shape[0]] += waveform
    stacked_waveform /= np.abs(stacked_waveform).max()
    return stacked_waveform


def download_sf(s3):
    sf_dir = "../soundfont"
    if not os.path.exists(sf_dir):
        os.makedirs(sf_dir)
    if not os.path.exists(os.path.join(sf_dir, "GeneralUserMuseScore.sf2")):
        s3.download_file(bucket_name, "soundfont/GeneralUserMuseScore.sf2", os.path.join(sf_dir, "GeneralUserMuseScore.sf2"))
    if not os.path.exists(os.path.join(sf_dir, "JazzClubBass.sf2")):
        s3.download_file(bucket_name, "soundfont/JazzClubBass.sf2", os.path.join(sf_dir, "JazzClubBass.sf2"))


def download_voice(s3, filename):
    response = s3.get_object(Bucket=bucket_name, Key=f"voice/{filename}.m4a")
    audio_data = response['Body'].read()
    audio = AudioSegment.from_file(io.BytesIO(audio_data), format='m4a')
    audio = audio.export(format='wav')
    audio_bytes = audio.read()
    return io.BytesIO(audio_bytes)


def download_midi(s3, type, filename):
    s3.download_file("cau-tensecond", f"midi/{type}/{filename}.mid", f"{filename}.mid")
    midi = pretty_midi.PrettyMIDI(f"{filename}.mid")
    os.remove(f"{filename}.mid")
    return midi


def upload_stacked_audio(s3, filename, stacked_audio):
    write(f"{filename}.wav", 44100, stacked_audio)
    ffmpeg.input(f"{filename}.wav").output(f"{filename}.m4a").run()
    s3.upload_file(f"{filename}.m4a", bucket_name, f"beat/stack/{filename}.m4a")
    os.remove(f"{filename}.wav")
    os.remove(f"{filename}.m4a")


def upload_midi(s3, filename, instrument_midi, sf_path):
    for instrument, midi in instrument_midi.items():
        audio = midi.fluidsynth(sf2_path=sf_path[instrument])
        # 추후에 파일 저장 없이 메모리 버퍼로만 진행할 수 있도록 코드 수정
        write(f"{filename}.wav", 44100, audio)
        ffmpeg.input(f"{filename}.wav").output(f"{filename}.m4a").run()
        s3.upload_file(f"{filename}.m4a", bucket_name, f"beat/{instrument}/{filename}.m4a")
        os.remove(f"{filename}.wav")
        os.remove(f"{filename}.m4a")
        # midi 파일 업로드
        midi_file = io.BytesIO()
        midi.write(midi_file)
        midi_file.seek(0)
        s3.upload_fileobj(midi_file, bucket_name, f"midi/{instrument}/{filename}.mid")
