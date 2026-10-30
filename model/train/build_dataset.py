"""WIDER FACE -> FOMO 학습용 64x64 흑백 데이터(npz).

시연 상황(카메라 앞 1~3명, 얼굴이 화면의 10~60%)에 맞게 정사각형으로 잘라 만든다.
라벨은 Edge Impulse FOMO와 같은 방식: 얼굴 중심이 들어간 격자 칸 = 1.
너무 작은 얼굴은 정답도 오답도 아닌 '무시' 칸(weight 0)으로 둔다.

사용: python build_dataset.py <WIDER 폴더> <출력.npz> --split train|val [--max N] [--extra 폴더]
"""
import argparse
import os
import random

import cv2
import numpy as np

IN = 64          # 입력 크기
GRID = IN // 8   # FOMO 출력 격자 (stride 8)
MIN_FRAC = 0.10  # 잘린 정사각형 대비 이 비율 이상인 얼굴만 '얼굴'
IGN_FRAC = 0.04  # 이보다 크고 MIN_FRAC보다 작으면 무시 칸


def read_gt(path):
    out = []
    with open(path) as f:
        lines = [l.strip() for l in f]
    i = 0
    while i < len(lines):
        name = lines[i]; n = int(lines[i + 1]); i += 2
        boxes = []
        for k in range(max(n, 1)):
            v = list(map(int, lines[i + k].split()))
            x, y, w, h, blur, expr, illum, invalid, occl, pose = v
            if n and not invalid and w > 0 and h > 0:
                boxes.append((x, y, w, h, occl))
        i += max(n, 1)
        out.append((name, boxes))
    return out


def gray(img):
    # Edge Impulse 이미지 DSP와 같은 계수
    b, g, r = img[..., 0].astype(np.float32), img[..., 1].astype(np.float32), img[..., 2].astype(np.float32)
    return np.clip(0.299 * r + 0.587 * g + 0.114 * b, 0, 255).astype(np.uint8)


def make_sample(g, boxes, cx0, cy0, side):
    """정사각형 (cx0,cy0,side)을 64로 줄이고 격자 라벨/가중치를 만든다."""
    crop = g[cy0:cy0 + side, cx0:cx0 + side]
    if crop.shape[0] != side or crop.shape[1] != side:
        return None
    x = cv2.resize(crop, (IN, IN), interpolation=cv2.INTER_AREA)
    y = np.zeros((GRID, GRID), np.uint8)
    wgt = np.ones((GRID, GRID), np.float32)
    n_face = 0
    for (bx, by, bw, bh, occl) in boxes:
        cx = bx + bw / 2 - cx0; cy = by + bh / 2 - cy0
        if not (0 <= cx < side and 0 <= cy < side):
            continue
        frac = max(bw, bh) / side
        gx = min(GRID - 1, int(cx / side * GRID)); gy = min(GRID - 1, int(cy / side * GRID))
        if frac >= MIN_FRAC and occl < 2:
            y[gy, gx] = 1; n_face += 1
        elif frac >= IGN_FRAC:
            # 작은 얼굴·많이 가려진 얼굴: 맞혀도 틀려도 세지 않는다(주변 1칸까지)
            wgt[max(0, gy - 1):gy + 2, max(0, gx - 1):gx + 2] = 0
    return x, y, wgt, n_face


def crops_for(g, boxes, rng):
    H, W = g.shape
    res = []
    big = [b for b in boxes if b[2] >= 12]
    if big:
        # 얼굴 하나를 골라 그 얼굴이 15~55% 가 되도록 자른다
        bx, by, bw, bh, _ = rng.choice(big)
        frac = rng.uniform(0.15, 0.55)
        side = int(max(bw, bh) / frac)
        side = min(side, H, W)
        if side >= 24:
            cx = bx + bw / 2 + rng.uniform(-0.3, 0.3) * side
            cy = by + bh / 2 + rng.uniform(-0.3, 0.3) * side
            cx0 = int(np.clip(cx - side / 2, 0, W - side)); cy0 = int(np.clip(cy - side / 2, 0, H - side))
            s = make_sample(g, boxes, cx0, cy0, side)
            if s and s[3] > 0:
                res.append(s)
    # 배경: 얼굴 중심이 없는 무작위 정사각형
    for _ in range(3):
        side = int(min(H, W) * rng.uniform(0.3, 0.9))
        cx0 = rng.randint(0, W - side); cy0 = rng.randint(0, H - side)
        s = make_sample(g, boxes, cx0, cy0, side)
        if s and s[3] == 0 and s[2].min() > 0:
            res.append(s); break
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wider'); ap.add_argument('out')
    ap.add_argument('--split', default='train'); ap.add_argument('--max', type=int, default=0)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    gt = read_gt(os.path.join(a.wider, 'wider_face_split', f'wider_face_{a.split}_bbx_gt.txt'))
    rng.shuffle(gt)
    X, Y, Wt = [], [], []
    for k, (name, boxes) in enumerate(gt):
        if a.max and k >= a.max:
            break
        img = cv2.imread(os.path.join(a.wider, f'WIDER_{a.split}', 'images', name))
        if img is None:
            continue
        g = gray(img)
        for x, y, w, _ in crops_for(g, boxes, rng):
            X.append(x); Y.append(y); Wt.append(w)
    X = np.stack(X); Y = np.stack(Y); Wt = np.stack(Wt)
    np.savez_compressed(a.out, x=X, y=Y, w=Wt)
    pos = int((Y.reshape(len(Y), -1).max(1) > 0).sum())
    print(f'{a.out}: {len(X)}장 (얼굴 있음 {pos}, 배경 {len(X) - pos}), 얼굴 칸 {int(Y.sum())}')


if __name__ == '__main__':
    main()
