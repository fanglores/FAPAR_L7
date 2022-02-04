from math import *
import cv2
import winsound
import time
import threading

#0 - for g0, 1 - g1, 2 - g2
l = {
    0: [000, 0.27505, 0.35511, -0.004, -0.322, 0.299, -0.0131],
    1: [000, -10.036, -0.019804, 0.55438, 0.14108, 12.494, 0, 0, 0, 0, 0, 1.0],
    2: [000, 0.42720, 0.069884, -0.33771, 0.24690, -1.0821, -0.30401, -1.1024, -1.2596, -0.31949, -1.4864, 0]
}
#1 - Blue, 2 - Green, 3 - Red, 4 - NIR
k = {
    1: 0.76611,
    3: 0.63931,
    4: 0.81037
}

pic = {
    1: 0.643,
    3: 0.80760,
    4: 0.89472
}

hg = {
    1: -0.10055,
    3: -0.06156,
    4: -0.03924
}

E0 = [1969.0, 1551.0, 1044.0]

'''
Oo - solar zenith angle
Ov - sensor zenith angle
phi - sun-sensor relative azimuth
pic
hg
k
l
'''

def ro_star(n, ND):
    R = gain[n] * ND + offset[n]
    return ( pi * R * dsol**2 / E0[n] * cos(Oo))

def F(n):
    f1 = ( (cos(Oo)*cos(Ov))**(k[n] - 1) / (cos(Oo) + cos(Ov))**(1 - k[n]) )

    cos_g = cos(Oo)*cos(Ov) + sin(Oo)*sin(Ov)*cos(phi)

    f2 = ( (1 - hg[n]**2) / (1 + 2*hg[n]*cos_g + hg[n]**2)**1.5 )

    G = (tan(Oo)**2 + tan(Ov)**2 - 2*tan(Oo)*tan(Ov)*cos(phi))**0.5

    f3 = 1 + (1 - pic[n]) / (1 + G)

    return (f1 * f2 * f3)

def g12(x, y, n):
    return (l[n][1] * (x + l[n][2])**2 + l[n][3] * (y + l[n][4])**2 + l[n][5]*x*y) / (l[n][6] * (x + l[n][7]) ** 2 + l[n][8] * (y + l[n][9]) ** 2 + l[n][10]*x*y + l[n][11])

def g0(x, y, n = 0):
    return (l[n][1] * y - l[n][2] * x - l[n][3]) / ((l[n][4] - x) ** 2 + (l[n][5] - y) ** 2 + l[n][6])

#FAPAR index calcuator
def L7OF(blue, red, nir):
    #1 - Blue   2 - Green   3 - Red   4 - NIR

    ro_star_1 = ro_star(0, blue)
    ro_star_3 = ro_star(1, red)
    ro_star_4 = ro_star(2, nir)

    blue, red, nir = ro_star_1, ro_star_3, ro_star_4

    if (blue <= 0 or red <= 0 or nir <= 0): return [0, 0, 0]    #bad data(1)
    if (blue >= 0.257752 or red >= 0.48407 or nir >= 0.683928): return [255, 255, 0]  #cloud, snow, ice (2)
    if ((0 < blue < 0.257752) and (0 < red < 0.48407) and (0 < nir < 0.683928)):
        if (blue > nir): return [128, 0, 0]  #water, shadow (3)
        if ((0 < blue <= nir) and (1.25*red > nir)): return [255, 255, 255]  #bright surface (4)

    ro_tilda_1 = ro_star_1 / F(1)
    ro_tilda_3 = ro_star_3 / F(3)
    ro_tilda_4 = ro_star_4 / F(4)

    #g1 and g2 functions
    ro_rred = g12(ro_tilda_1, ro_tilda_3, 1)   #RO RRED with g1
    ro_rnir = g12(ro_tilda_1, ro_tilda_4, 2)   #RO RNIR with g2

    if(ro_rred < 0 or ro_rnir < 0): return [0, 0, 0]     #undefined (5)

    #g0 function
    fapar =  g0(ro_rred, ro_rnir)

    if (fapar <= 0): return [208, 255, 255]
    if (0 < fapar <= 0.25): return [150 - 10*int(4*fapar/0.25), 255, 255]
    if (0.25 < fapar <= 0.5): return [50 - 10*int(4*(fapar - 0.25) / 0.25), 255, 50 - 10*int(4*(fapar - 0.25) / 0.25)]
    if (0.5 < fapar <= 0.625): return [0, 200 - 10*int(4*(fapar - 0.5) / 0.125), 0]
    if (0.625 < fapar <= 0.75): return [0, 150 - 10*int(4*(fapar - 0.625) / 0.125), 0]
    if (0.75 < fapar < 1): return [0, 100 - 10*int(4*(fapar - 0.75) / 0.25), 0]
    if (1 <= fapar): return [0, 60, 0]

#function for debugging
def test__L7OF(blue, red, nir):
    ro_star_1 = ro_star(0, blue)
    ro_star_3 = ro_star(1, red)
    ro_star_4 = ro_star(2, nir)

    blue, red, nir = ro_star_1, ro_star_3, ro_star_4

    if (blue <= 0 or red <= 0 or nir <= 0): return 'bad data (1)'
    if (blue >= 0.257752 or red >= 0.48407 or nir >= 0.683928): 'cloud, snow, ice (2)'
    if ((0 < blue < 0.257752) and (0 < red < 0.48407) and (0 < nir < 0.683928)):
        if (blue > nir): return 'water, shadow (3)'
        if ((0 < blue <= nir) and (1.25*red > nir)): return 'bright surface (4)'

    ro_tilda_1 = ro_star_1 / F(1)
    ro_tilda_3 = ro_star_3 / F(3)
    ro_tilda_4 = ro_star_4 / F(4)

    ro_rred = g12(ro_tilda_1, ro_tilda_3, 1)
    ro_rnir = g12(ro_tilda_1, ro_tilda_4, 2)

    if (ro_rred < 0 or ro_rnir < 0): return 'undefined (5)'

    fapar = g0(ro_rred, ro_rnir)

    return fapar

'''
(BLUE)  Band 1 Visible (0.45 - 0.52 µm) 30 m
(GREEN) Band 2 Visible (0.52 - 0.60 µm) 30 m
(RED)   Band 3 Visible (0.63 - 0.69 µm) 30 m
(NIR)   Band 4 Near-Infrared (0.77 - 0.90 µm) 30 m
(SWIR)  Band 5 Short-wave Infrared (1.55 - 1.75 µm) 30 m
(THM)   Band 6 Thermal (10.40 - 12.50 µm) 60 m Low Gain / High Gain
(MIR)   Band 7 Mid-Infrared (2.08 - 2.35 µm) 30 m
(PAN)   Band 8 Panchromatic (PAN) (0.52 - 0.90 µm) 15 m
'''

def parse_metadata(path):
    with open(path + 'MTL.txt') as f:
        for line in f:
            line = line[:-1]
            if(line == 'END'): break
            (key, val) = line.split(' = ')

            while(key[0] == ' '): key = key[1:]

            if (key != 'GROUP' and key != 'END_GROUP'):
                if (val[0] == '\"'):
                    metadata[key] = val[1:-1]
                else:
                    metadata[key] = val

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Main~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
DEBUG_MODE = False

LOCATION = 5
MAP = {
    1: 'Moscow',
    2: 'Desert',
    3: 'Forest',
    4: 'Autumn_msk',
    5: 'Summer_msk'
}
PATH = 'C:\\Users\\kosiya\\Downloads\\Science\\Source\\' + MAP[LOCATION] + '\\'

print('[DEBUG] Passed ' + MAP[LOCATION] + ' location')

metadata = {}
parse_metadata(PATH)

Oo = (90 - float(metadata['SUN_ELEVATION']))*pi/180
phi = float(metadata['SUN_AZIMUTH'])*pi/180
Ov = 0
#!!! lim(Ov) = 0, but Ov != 0

if ('EARTH_SUN_DISTANCE' in metadata.keys()):
    dsol = float(metadata['EARTH_SUN_DISTANCE'])
    print('\t\tParsed earth_sun_distance: ', dsol)
else:
    y, m, d = (metadata['DATE_ACQUIRED']).split('-')
    y, m, d = int(y), int(m), int(d)

    if (y % 4 != 0 or (y % 100 == 0 and y % 400 != 0)): v = 0
    else: v = 1

    dm = [000, 31, 28 + v, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    DOY = 0
    for i in range(1, m): DOY += dm[i]
    DOY += d - 1

    SCT = metadata['SCENE_CENTER_TIME']
    ho, mi, se = SCT[:-1].split(':')
    DOY += (int(ho)*3600 + int(mi)*60 + float(se)) / (24 * 3600)

    #dsol  = 1.00014 - 0.01672 * cos(2*pi * (DOY - 4) / 365.256363)
    dsol = 1.00014 - 0.01671 * cos(2*pi * (DOY - 3.4532868) / 365.256363)
    print('\t\tCalculated earth_sun_distance ', dsol)

gain = [float(metadata['RADIANCE_MULT_BAND_1']), float(metadata['RADIANCE_MULT_BAND_3']), float(metadata['RADIANCE_MULT_BAND_4'])]
offset = [float(metadata['RADIANCE_ADD_BAND_1']), float(metadata['RADIANCE_ADD_BAND_3']), float(metadata['RADIANCE_ADD_BAND_4'])]

print('\t\tParsed gain and offset:', gain, offset)
print('[DEBUG] Metadata parsed successfully')

img_B1 = cv2.imread(PATH + 'B1.tif', cv2.IMREAD_GRAYSCALE)
img_B3 = cv2.imread(PATH + 'B3.tif', cv2.IMREAD_GRAYSCALE)
img_B4 = cv2.imread(PATH + 'B4.tif', cv2.IMREAD_GRAYSCALE)

#print chosen img[i][j] fapar index
if (DEBUG_MODE):
    i, j = 4000, 5000
    print('[DEBUG MODE] for i =', i, '; j =', j, 'fapar is', test__L7OF(img_B1[i][j].astype(float), img_B3[i][j].astype(float), img_B4[i][j].astype(float)))
    exit(0)

img_fapar = cv2.imread(PATH + 'B4.tif', cv2.IMREAD_COLOR)
print('[DEBUG] Images created')

global results
results = [0, 0]

def f1():
    mf1 = cf1 = 0
    print('[THREAD] First thread engaged')
    for i in range(0, len(img_fapar)//2):
        for j in range(len(img_fapar[0])):
            b, r, n = img_B1[i][j].astype(float), img_B3[i][j].astype(float), img_B4[i][j].astype(float)
            if (b == 0 and r == 0 and n == 0):
                img_fapar[i][j] = [255, 255, 255]
            else:
                tmp = test__L7OF(b, r, n)
                # img_fapar[i][j] = tmp
                if (not (type(tmp) is str)): mf1 += tmp
                cf1 += 1

    print('[THREAD] First thread completed it`s work with result:', mf1 / cf1)
    results[0] = mf1 / cf1

def f2():
    mf2 = cf2 = 0
    print('[THREAD] Second thread engaged')
    for i in range(len(img_fapar)//2, len(img_fapar)):
        for j in range(len(img_fapar[0])):
            b, r, n = img_B1[i][j].astype(float), img_B3[i][j].astype(float), img_B4[i][j].astype(float)
            if (b == 0 and r == 0 and n == 0):
                img_fapar[i][j] = [255, 255, 255]
            else:
                tmp = test__L7OF(b, r, n)
                # img_fapar[i][j] = tmp
                if (not (type(tmp) is str)): mf2 += tmp
                cf2 += 1

    print('[THREAD] Second thread completed it`s work with result:', mf2 / cf2)
    results[1] = mf2 / cf2


th1 = threading.Thread(target=f1)
th2 = threading.Thread(target=f2)

print('[DEBUG] Starting time:', time.strftime("%H:%M:%S", time.gmtime()))

th1.start()
th2.start()

start = time.time()

th1.join()
th2.join()

print(results)

print('[DEBUG] Images parsed')
end = time.time()

print("[DEBUG] Elapsed time: " + str(end - start))

winsound.MessageBeep()

cv2.imwrite('C:\\Users\\kosiya\\Downloads\\Science\\Source\\FAPAR3d_' + MAP[LOCATION] + '.jpeg', img_fapar)
print('[DEBUG] Image saved')
#print('Mean fapar value:', mean_fapar/count_fapar)
