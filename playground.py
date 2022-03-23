
from rgbxy import Converter


def hsv_to_rgb(h, s, v):
    """
    This function takes
     h - 0 - 360 Deg
     s - 0 - 100 %
     v - 0 - 100 %
    """

    hPri = h / 60
    s = s / 100
    v = v / 100

    if s <= 0.0:
        return int(0), int(0), int(0)

    C = v * s  # Chroma
    X = C * (1 - abs(hPri % 2 - 1))

    RGB_Pri = [0.0, 0.0, 0.0]

    if 0 <= hPri <= 1:
        RGB_Pri = [C, X, 0]
    elif 1 <= hPri <= 2:
        RGB_Pri = [X, C, 0]
    elif 2 <= hPri <= 3:
        RGB_Pri = [0, C, X]
    elif 3 <= hPri <= 4:
        RGB_Pri = [0, X, C]
    elif 4 <= hPri <= 5:
        RGB_Pri = [X, 0, C]
    elif 5 <= hPri <= 6:
        RGB_Pri = [C, 0, X]
    else:
        RGB_Pri = [0, 0, 0]

    m = v - C

    return int((RGB_Pri[0] + m) * 255), int((RGB_Pri[1] + m) * 255), int((RGB_Pri[2] + m) * 255)


bla = hsv_to_rgb(360, 100, 1)

converter = Converter()
xy = converter.rgb_to_xy(bla[0], bla[1], bla[2])
print(xy[0], xy[1])