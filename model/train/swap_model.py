"""Edge Impulse Arduino 라이브러리(EON 컴파일본)의 모델을 로컬 학습 int8 TFLite로 바꿔 새 zip을 만든다.

EON(compiled) 대신 TFLite Micro 인터프리터 경로(EI_CLASSIFIER_COMPILED 0)를 쓴다.
DSP(흑백 64x64)·FOMO 후처리·라벨 'face'는 원본 라이브러리 그대로라 펌웨어 코드는 바꿀 필요가 없다.

사용: python swap_model.py <원본 라이브러리 폴더(ztmc-face-fomo_inferencing)> <model_int8.tflite> <출력 zip> [--arena 바이트]
"""
import argparse
import os
import re
import shutil
import tempfile
import zipfile


def c_array(name, data):
    rows = [', '.join(f'0x{b:02x}' for b in data[i:i + 16]) for i in range(0, len(data), 16)]
    return (f'#include "tflite_learn_{name}.h"\n'
            f'// 로컬 학습 모델 (model/train/train_fomo.py)\n'
            f'alignas(16) const unsigned char tflite_learn_{name}[] = {{\n  ' + ',\n  '.join(rows) + '\n};\n'
            f'const unsigned int tflite_learn_{name}_len = {len(data)};\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lib'); ap.add_argument('tflite'); ap.add_argument('out_zip')
    ap.add_argument('--arena', type=int, default=160 * 1024)
    ap.add_argument('--tag', default='local')
    a = ap.parse_args()
    data = open(a.tflite, 'rb').read()

    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, os.path.basename(os.path.normpath(a.lib)))
    shutil.copytree(a.lib, dst)
    src = os.path.join(dst, 'src')
    mv = os.path.join(src, 'model-parameters', 'model_variables.h')
    md = os.path.join(src, 'model-parameters', 'model_metadata.h')
    tdir = os.path.join(src, 'tflite-model')

    t = open(mv, encoding='utf-8').read()
    m = re.search(r'#include "tflite-model/tflite_learn_(\w+)_compiled\.h"', t)
    name = m.group(1)

    # EON 파일 제거, 모델 배열 추가
    for f in os.listdir(tdir):
        if f.startswith(f'tflite_learn_{name}_compiled'):
            os.remove(os.path.join(tdir, f))
    open(os.path.join(tdir, f'tflite_learn_{name}.h'), 'w', encoding='utf-8').write(
        f'#ifndef TFLITE_LEARN_{name}_H\n#define TFLITE_LEARN_{name}_H\n'
        f'extern const unsigned char tflite_learn_{name}[];\nextern const unsigned int tflite_learn_{name}_len;\n#endif\n')
    open(os.path.join(tdir, f'tflite_learn_{name}.cpp'), 'w', encoding='utf-8').write(c_array(name, data))

    t = t.replace(f'tflite-model/tflite_learn_{name}_compiled.h', f'tflite-model/tflite_learn_{name}.h')
    t = re.sub(r'const ei_config_tflite_eon_graph_t ei_config_graph_(\w+) = \{.*?\};',
               lambda mm: (f'const ei_config_tflite_graph_t ei_config_graph_{mm.group(1)} = {{\n'
                           f'    .implementation_version = 1,\n'
                           f'    .model = tflite_learn_{name},\n'
                           f'    .model_size = {len(data)},\n'
                           f'    .arena_size = {a.arena}\n}};'), t, flags=re.S)
    t = t.replace('.compiled = 1,', '.compiled = 0,')
    t = re.sub(r'\.impulse_name = "[^"]*"', f'.impulse_name = "{a.tag}"', t)
    open(mv, 'w', encoding='utf-8').write(t)

    d = open(md, encoding='utf-8').read()
    d = re.sub(r'#define EI_CLASSIFIER_COMPILED\s+1', '#define EI_CLASSIFIER_COMPILED                      0', d)
    d = re.sub(r'#define EI_CLASSIFIER_TFLITE_LARGEST_ARENA_SIZE\s+\d+',
               f'#define EI_CLASSIFIER_TFLITE_LARGEST_ARENA_SIZE     {a.arena}', d)
    open(md, 'w', encoding='utf-8').write(d)

    with zipfile.ZipFile(a.out_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(dst):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, tmp))
    shutil.rmtree(tmp)
    print(f'{a.out_zip}: 모델 {len(data)} B, arena {a.arena} B, block {name}')


if __name__ == '__main__':
    main()
