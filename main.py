import datetime
import json
import math
import subprocess

import click
import srt
from vosk import KaldiRecognizer, Model, SetLogLevel


@click.command()
@click.option('--file-path', required=True, help='Path to the audio file')
@click.option('--model-path', required=True, help='Path to the model')
@click.option(
    '--save-path',
    required=True,
    default='result.srt',
    help='Path to resulting SRT file'
)
@click.option(
    '--words-per-line',
    required=True,
    type=int,
    default=14,
    help='Number of words per line'
)
def transcribe(file_path, model_path, save_path, words_per_line=7):
    sample_rate = 16000
    SetLogLevel(-1)

    model = Model(model_path)
    rec = KaldiRecognizer(model, sample_rate)
    rec.SetWords(True)

    process = subprocess.Popen(
        [
            'ffmpeg', '-loglevel', 'quiet', '-i', file_path, '-ar',
            str(sample_rate), '-ac', '1', '-f', 's16le', '-'
        ],
        stdout=subprocess.PIPE
    )

    results = []
    while True:
        data = process.stdout.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            results.append(res)
            if math.log2(len(results)) % 2 == 0:
                print(f'Progress: {len(results)}')
    results.append(json.loads(rec.FinalResult()))

    subs = []
    for res in results:
        if not 'result' in res:
            continue
        words = res['result']
        for j in range(0, len(words), words_per_line):
            line = words[j:j + words_per_line]
            s = srt.Subtitle(
                index=len(subs),
                content=" ".join([l['word'] for l in line]),
                start=datetime.timedelta(seconds=line[0]['start']),
                end=datetime.timedelta(seconds=line[-1]['end'])
            )
            subs.append(s)

    srt_res = srt.compose(subs)
    with open(save_path, 'w') as f:
        f.write(srt_res)


if __name__ == '__main__':
    transcribe()
