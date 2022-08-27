import datetime
import json
import subprocess

import click
import srt
import tqdm
from vosk import KaldiRecognizer, Model, SetLogLevel


@click.command()
@click.option('--file-path', required=True, help='Path to the audio file')
@click.option('--model-path', required=True, help='Path to the main model')
@click.option(
    '--save-path',
    required=True,
    default='result.srt',
    help='Path to the resulting SRT file'
)
@click.option(
    '--words-per-line',
    required=True,
    type=int,
    default=14,
    help='Number of words per line'
)
def transcribe(file_path, model_path, save_path, words_per_line):
    sample_rate = 16000
    words_per_line = 7
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
    prev_start = 0
    with tqdm.tqdm() as t:
        while True:
            data = process.stdout.read(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                results.append(res)
                if 'result' in res:
                    start = res['result'][0]['start']
                    t.update(start - prev_start)
                    prev_start = start
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
