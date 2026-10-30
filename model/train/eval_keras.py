"""저장된 model.keras 를 임계값별로 평가하고 int8 TFLite로 변환한다.

사용: python eval_keras.py <run 폴더> --val va.npz --rep tr.npz
(Windows 한글 사용자 폴더면 TMP/TEMP 를 영문 경로로 바꿔서 실행 — TFLite 변환이 임시 폴더를 쓴다)
"""
import argparse
import json
import os

import numpy as np
import tensorflow as tf

from train_fomo import f1_from_probs, loss_fn, run_tflite, to_tflite


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run'); ap.add_argument('--val', required=True); ap.add_argument('--rep', required=True)
    a = ap.parse_args()
    m = tf.keras.models.load_model(os.path.join(a.run, 'model.keras'), compile=False)
    v = np.load(a.val); xv = v['x'].astype(np.float32)[..., None] / 255.; yv, wv = v['y'], v['w']
    pf = m.predict(xv, verbose=0)[..., 1]
    print('float:', ' '.join(f'{t}:{f1_from_probs(pf, yv, wv, t)["f1"]:.3f}' for t in (0.5, 0.7, 0.8, 0.9, 0.95)))
    xr = np.load(a.rep)['x'][:2000].astype(np.float32)[..., None] / 255.
    tfl = to_tflite(m, xr)
    open(os.path.join(a.run, 'model_int8.tflite'), 'wb').write(tfl)
    pq, q = run_tflite(tfl, xv)
    res = {'quant': q, 'tflite_bytes': len(tfl), 'int8': {}}
    for t in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        r = f1_from_probs(pq, yv, wv, t); res['int8'][str(t)] = r
        print(f'int8 thr {t}: F1 {r["f1"]:.3f} P {r["p"]:.3f} R {r["r"]:.3f} (tp {r["tp"]} fp {r["fp"]} fn {r["fn"]})')
    json.dump(res, open(os.path.join(a.run, 'result.json'), 'w'), indent=1)
    print(json.dumps({k: res[k] for k in ('quant', 'tflite_bytes')}))


if __name__ == '__main__':
    main()
