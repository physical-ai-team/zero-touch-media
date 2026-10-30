"""PC 하네스(exe) 출력으로 검증셋 F1을 잰다. 보드와 같은 DSP·후처리·임계값(라이브러리 기본값)을 쓴다.

사용: python eval_harness.py <harness.exe> <val.npz> [--n 2000]
"""
import argparse
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from train_fomo import f1_from_probs  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exe'); ap.add_argument('val'); ap.add_argument('--n', type=int, default=0)
    a = ap.parse_args()
    d = np.load(a.val); x, y, w = d['x'], d['y'], d['w']
    if a.n:
        x, y, w = x[:a.n], y[:a.n], w[:a.n]
    tmp = os.path.join(os.path.dirname(os.path.abspath(a.exe)), 'val_imgs.u8')
    x.astype(np.uint8).tofile(tmp)
    r = subprocess.run([a.exe, tmp], capture_output=True, text=True)
    print(r.stderr.strip().splitlines()[-1])
    side = x.shape[1]; cell = side / y.shape[1]
    prob = np.zeros(y.shape, np.float32)
    for line in r.stdout.splitlines():
        v = line.split(); i, n = int(v[0]), int(v[1])
        for k in range(n):
            bx, by, bw, bh, val = map(float, v[2 + 5 * k: 7 + 5 * k])
            # 박스가 덮는 칸을 '검출'로 칠한다 (FOMO 박스는 칸 단위)
            x0, y0 = int(bx // cell), int(by // cell)
            x1, y1 = int(np.ceil((bx + bw) / cell)), int(np.ceil((by + bh) / cell))
            prob[i, y0:max(y1, y0 + 1), x0:max(x1, x0 + 1)] = max(val, 0.51)
    m = f1_from_probs(prob, y, w, 0.5)
    print(f'harness F1 {m["f1"]:.3f} P {m["p"]:.3f} R {m["r"]:.3f} (tp {m["tp"]} fp {m["fp"]} fn {m["fn"]})')


if __name__ == '__main__':
    main()
