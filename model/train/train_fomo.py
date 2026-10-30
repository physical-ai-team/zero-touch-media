"""FOMO(MobileNetV2 앞부분 + 1x1 머리) 로컬 학습 → int8 TFLite.

Edge Impulse FOMO와 같은 구조·입출력을 쓴다:
  입력 64x64x1 (0~1, int8 scale 1/255 zp -128), 출력 8x8x2 softmax (0=배경, 1=face).
그래서 Edge Impulse Arduino 라이브러리의 모델만 바꿔 끼울 수 있다(tools/swap_model.py).

사용: python train_fomo.py --train tr.npz --val va.npz --out runs/E6 [--alpha 0.35] [--epochs 60]
"""
import argparse
import json
import os
import time

import numpy as np
import tensorflow as tf
from scipy import ndimage

IN, GRID = 64, 8


def build(alpha, pretrained, head=32):
    inp = tf.keras.Input((IN, IN, 1))
    kw = dict(alpha=alpha, include_top=False)
    base1 = tf.keras.applications.MobileNetV2(input_shape=(IN, IN, 1), weights=None, **kw)
    if pretrained:
        base3 = tf.keras.applications.MobileNetV2(input_shape=(IN, IN, 3), weights='imagenet', **kw)
        for l1, l3 in zip(base1.layers, base3.layers):
            w = l3.get_weights()
            if l1.name == 'Conv1':
                # 흑백 1채널로 합치고, 입력 0~1 을 원래 -1~1 전처리에 맞게 접는다(2x-1)
                k = w[0].sum(axis=2, keepdims=True)
                w = [2 * k]
                # 바이어스가 없는 conv라 -sum(k)는 다음 BN의 moving_mean에 더한다
                bn = base1.get_layer('bn_Conv1'); bn3 = base3.get_layer('bn_Conv1')
                g, b, m, v = bn3.get_weights()
                l1.set_weights(w)
                bn.set_weights([g, b, m + k.sum(axis=(0, 1, 2)), v])
                continue
            if l1.name == 'bn_Conv1':
                continue
            if w:
                l1.set_weights(w)
    cut = base1.get_layer('block_6_expand_relu').output
    trunk = tf.keras.Model(base1.input, cut)
    x = trunk(inp)
    x = tf.keras.layers.Conv2D(head, 1, activation='relu', name='head')(x)
    x = tf.keras.layers.Conv2D(2, 1, activation='softmax', name='logits')(x)
    return tf.keras.Model(inp, x)


def loss_fn(obj_weight):
    def f(yw, p):
        y, w = yw[..., 0], yw[..., 1]
        p = tf.clip_by_value(p, 1e-7, 1 - 1e-7)
        ce = -(y * tf.math.log(p[..., 1]) * obj_weight + (1 - y) * tf.math.log(p[..., 0]))
        return tf.reduce_sum(ce * w) / (tf.reduce_sum(w) + 1e-6)
    return f


def augment(x, yw):
    flip = tf.random.uniform(()) < 0.5
    x = tf.cond(flip, lambda: tf.reverse(x, [1]), lambda: x)
    yw = tf.cond(flip, lambda: tf.reverse(yw, [1]), lambda: yw)
    x = tf.image.random_brightness(x, 0.2)
    x = tf.image.random_contrast(x, 0.7, 1.3)
    x = x + tf.random.normal(tf.shape(x), 0, 0.02)
    return tf.clip_by_value(x, 0, 1), yw


def f1_from_probs(prob, y, w, thr=0.5):
    """Edge Impulse 방식에 가깝게: 예측 칸 덩어리(연결 성분)를 하나의 검출로,
    정답 칸에서 1칸 이내에 검출이 있으면 TP. 무시 칸 검출은 세지 않는다."""
    tp = fp = fn = 0
    for pr, yy, ww in zip(prob, y, w):
        lab, n = ndimage.label(pr >= thr)
        used = set()
        for gy, gx in zip(*np.nonzero(yy)):
            hit = [l for l in np.unique(lab[max(0, gy - 1):gy + 2, max(0, gx - 1):gx + 2]) if l]
            if hit:
                tp += 1; used.update(hit)
            else:
                fn += 1
        for l in range(1, n + 1):
            if l in used:
                continue
            ys, xs = np.nonzero(lab == l)
            if ww[ys, xs].min() == 0:   # 무시(작은 얼굴) 칸
                continue
            fp += 1
    p = tp / (tp + fp + 1e-9); r = tp / (tp + fn + 1e-9)
    return dict(f1=2 * p * r / (p + r + 1e-9), p=p, r=r, tp=tp, fp=fp, fn=fn)


def to_tflite(model, xs):
    def rep():
        for i in range(0, min(len(xs), 500)):
            yield [xs[i:i + 1].astype(np.float32)]
    c = tf.lite.TFLiteConverter.from_keras_model(model)
    c.optimizations = [tf.lite.Optimize.DEFAULT]
    c.representative_dataset = rep
    c.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    c.inference_input_type = tf.int8
    c.inference_output_type = tf.int8
    return c.convert()


def run_tflite(tfl, xs):
    it = tf.lite.Interpreter(model_content=tfl)
    it.allocate_tensors()
    i, o = it.get_input_details()[0], it.get_output_details()[0]
    s_in, z_in = i['quantization']; s_out, z_out = o['quantization']
    out = []
    t0 = time.time()
    for x in xs:
        q = np.clip(np.round(x / s_in + z_in), -128, 127).astype(np.int8)
        it.set_tensor(i['index'], q[None]); it.invoke()
        out.append((it.get_tensor(o['index'])[0].astype(np.float32) - z_out) * s_out)
    return np.stack(out)[..., 1], dict(in_q=[float(s_in), int(z_in)], out_q=[float(s_out), int(z_out)],
                                       pc_ms=(time.time() - t0) / len(xs) * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--train', nargs='+', required=True); ap.add_argument('--val', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--alpha', type=float, default=0.35); ap.add_argument('--no-pretrained', action='store_true')
    ap.add_argument('--epochs', type=int, default=60); ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--obj-weight', type=float, default=100.); ap.add_argument('--head', type=int, default=32)
    ap.add_argument('--batch', type=int, default=64)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    def load(paths):
        d = [np.load(p) for p in paths]
        x = np.concatenate([e['x'] for e in d]).astype(np.float32)[..., None] / 255.
        y = np.concatenate([e['y'] for e in d]).astype(np.float32)
        w = np.concatenate([e['w'] for e in d]).astype(np.float32)
        return x, y, w
    xt, yt, wt = load(a.train); xv, yv, wv = load([a.val])
    print(f'train {len(xt)}  val {len(xv)}')

    model = build(a.alpha, not a.no_pretrained, a.head)
    ds = (tf.data.Dataset.from_tensor_slices((xt, np.stack([yt, wt], -1)))
          .shuffle(len(xt)).map(augment, num_parallel_calls=tf.data.AUTOTUNE).batch(a.batch).prefetch(2))
    sched = tf.keras.optimizers.schedules.CosineDecay(a.lr, a.epochs * int(np.ceil(len(xt) / a.batch)))
    model.compile(tf.keras.optimizers.Adam(sched), loss_fn(a.obj_weight))

    best = (-1, None)
    for ep in range(a.epochs):
        h = model.fit(ds, epochs=1, verbose=0)
        if ep % 5 == 4 or ep == a.epochs - 1:
            pv = model.predict(xv, verbose=0)[..., 1]
            ms = {t: f1_from_probs(pv, yv, wv, t) for t in (0.5, 0.7, 0.8, 0.9)}
            t, m = max(ms.items(), key=lambda kv: kv[1]['f1'])
            print(f'ep {ep + 1:3d} loss {h.history["loss"][0]:.4f}  val F1 {m["f1"]:.3f} P {m["p"]:.3f} R {m["r"]:.3f} @thr {t}  '
                  + ' '.join(f'{k}:{v["f1"]:.3f}' for k, v in ms.items()), flush=True)
            if m['f1'] > best[0]:
                best = (m['f1'], model.get_weights())
                model.save_weights(os.path.join(a.out, 'best.weights.h5'))
    model.set_weights(best[1])
    model.save(os.path.join(a.out, 'model.keras'))

    tfl = to_tflite(model, xt)
    open(os.path.join(a.out, 'model_int8.tflite'), 'wb').write(tfl)
    prob, q = run_tflite(tfl, xv)
    res = {'args': vars(a), 'float_best_f1': best[0], 'int8': {}, 'quant': q, 'tflite_bytes': len(tfl),
           'params': int(model.count_params())}
    for thr in (0.5, 0.6, 0.7, 0.8, 0.9):
        res['int8'][str(thr)] = f1_from_probs(prob, yv, wv, thr)
    json.dump(res, open(os.path.join(a.out, 'result.json'), 'w'), indent=1)
    print(json.dumps({k: res[k] for k in ('float_best_f1', 'quant', 'tflite_bytes', 'params')}))
    for thr, m in res['int8'].items():
        print(f'int8 thr {thr}: F1 {m["f1"]:.3f} P {m["p"]:.3f} R {m["r"]:.3f} (tp {m["tp"]} fp {m["fp"]} fn {m["fn"]})')


if __name__ == '__main__':
    main()
