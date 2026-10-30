"""Edge Impulse Arduino 라이브러리 + main.cpp 를 PC용 실행 파일로 빌드한다(MinGW g++).

사용: python build.py <라이브러리 폴더(…_inferencing)> <출력 exe> [--gxx g++경로] [-j 8]
보드 전용 가속(ESP-NN, CMSIS-NN)은 끄고 일반 C 커널로 돈다 — 정확도 비교용, 속도는 상대값만.
"""
import argparse
import hashlib
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = ('porting/arduino', 'porting/espressif', 'porting/particle', 'CMSIS/NN', 'CMSIS/DSP',
        'porting/zephyr', 'third_party/arc_mli')
DEFS = ['-DEI_CLASSIFIER_TFLITE_ENABLE_CMSIS_NN=0', '-DEI_CLASSIFIER_TFLITE_ENABLE_ESP_NN=0',
        '-DEI_PORTING_ARDUINO=0', '-DEI_PORTING_POSIX=0', '-DEI_CLASSIFIER_ENABLE_DETECTION_POSTPROCESS_OP=1',
        '-DTF_LITE_DISABLE_X86_NEON', '-DNDEBUG', '-DEIDSP_USE_CMSIS_DSP=0', '-DEIDSP_LOAD_CMSIS_DSP_SOURCES=0']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lib'); ap.add_argument('exe')
    ap.add_argument('--gxx', default='g++'); ap.add_argument('-j', type=int, default=8)
    a = ap.parse_args()
    src = os.path.join(os.path.abspath(a.lib), 'src')
    # 모델 설정(헤더)이 바뀌면 SDK까지 다시 컴파일해야 하므로 obj 폴더 이름에 설정 해시를 넣는다
    h = hashlib.sha1()
    for d in ('model-parameters', 'tflite-model'):
        for f in sorted(os.listdir(os.path.join(src, d))):
            h.update(open(os.path.join(src, d, f), 'rb').read())
    obj = os.path.join(os.path.dirname(os.path.abspath(a.exe)),
                       'obj_' + os.path.basename(a.exe).replace('.exe', '') + '_' + h.hexdigest()[:8])
    os.makedirs(obj, exist_ok=True)
    files = []
    for root, _, fs in os.walk(src):
        rel = os.path.relpath(root, src).replace('\\', '/')
        if any(s in rel for s in SKIP):
            continue
        for f in fs:
            if f.endswith(('.c', '.cpp', '.cc')):
                files.append(os.path.join(root, f))
    files += [os.path.join(HERE, 'main.cpp'), os.path.join(HERE, 'porting_pc.cpp')]
    gcc = a.gxx.replace('g++', 'gcc')

    def comp(p):
        o = os.path.join(obj, os.path.relpath(p, os.path.dirname(src)).replace(os.sep, '_').replace(':', '') + '.o')
        if os.path.exists(o) and os.path.getmtime(o) > os.path.getmtime(p):
            return o, None
        cc = [gcc, '-std=gnu11'] if p.endswith('.c') else [a.gxx, '-std=gnu++17']
        cmd = cc + ['-O2', '-c', p, '-o', o, '-I', src, '-I', os.path.join(src, 'edge-impulse-sdk'),
                    '-w'] + DEFS
        r = subprocess.run(cmd, capture_output=True, text=True)
        return o, (r.stderr[-3000:] if r.returncode else None)

    with ThreadPoolExecutor(a.j) as ex:
        res = list(ex.map(comp, files))
    errs = [(f, e) for f, (_, e) in zip(files, res) if e]
    for f, e in errs[:5]:
        print('==', f, '\n', e)
    if errs:
        print(f'{len(errs)} 파일 실패'); sys.exit(1)
    r = subprocess.run([a.gxx, '-o', a.exe] + [o for o, _ in res] + ['-static', '-lm'], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-5000:]); sys.exit(1)
    print('ok', a.exe, len(files), 'files')


if __name__ == '__main__':
    main()
