import math
import cv2
import time
import multiprocessing
import os

'''
Oo - solar zenith angle
Ov - sensor zenith angle
phi - sun-sensor relative azimuth
pic
hg
k
l

(BLUE)  Band 1 Visible (0.45 - 0.52 µm) 30 m
(GREEN) Band 2 Visible (0.52 - 0.60 µm) 30 m
(RED)   Band 3 Visible (0.63 - 0.69 µm) 30 m
(NIR)   Band 4 Near-Infrared (0.77 - 0.90 µm) 30 m
(SWIR)  Band 5 Short-wave Infrared (1.55 - 1.75 µm) 30 m
(THM)   Band 6 Thermal (10.40 - 12.50 µm) 60 m Low Gain / High Gain
(MIR)   Band 7 Mid-Infrared (2.08 - 2.35 µm) 30 m
(PAN)   Band 8 Panchromatic (PAN) (0.52 - 0.90 µm) 15 m
'''


def image_thread(path, mode, n):
    print('[THREAD] Thread', n, 'engaged')

    if mode == 'map' and os.path.isfile(path + 'map.txt'):
        print('[THREAD] Thread', n, 'disengaged due to map file existence')
        return None

    obj = Fapar(path)
    print('(' + str(n) +')')
    rv = obj.build_pool(mode)

    print('[THREAD] Thread', n, 'disengaged')

    return rv


class Fapar:
    # 0 - for g0, 1 - g1, 2 - g2
    l = {
        0: [000, 0.27505, 0.35511, -0.004, -0.322, 0.299, -0.0131],
        1: [000, -10.036, -0.019804, 0.55438, 0.14108, 12.494, 0, 0, 0, 0, 0, 1.0],
        2: [000, 0.42720, 0.069884, -0.33771, 0.24690, -1.0821, -0.30401, -1.1024, -1.2596, -0.31949, -1.4864, 0]
    }
    # 1 - Blue, 2 - Green, 3 - Red, 4 - NIR
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
    non-static used variables
    path - path to the images
    metadata - metadata from mtl file
    Oo, phi, Ov, dsol - angles and distance

    img_fapar, img_B1, img_B3, img_B4 - source images as arrays
    '''
    uid = 0

    def __init__(self, path):
        self.uid += 1

        try:
            self.path = path
            self.metadata = {}

            # parse metadata
            with open(path + 'MTL.txt') as f:
                for line in f:
                    line = line[:-1]
                    if line == 'END': break
                    (key, val) = line.split(' = ')

                    while key[0] == ' ': key = key[1:]

                    if key != 'GROUP' and key != 'END_GROUP':
                        if val[0] == '\"':
                            self.metadata[key] = val[1:-1]
                        else:
                            self.metadata[key] = val

            # init angles
            self.Oo = (90 - float(self.metadata['SUN_ELEVATION'])) * math.pi / 180
            self.phi = float(self.metadata['SUN_AZIMUTH']) * math.pi / 180
            self.Ov = 0

            # init dsol
            if 'EARTH_SUN_DISTANCE' in self.metadata.keys():
                self.dsol = float(self.metadata['EARTH_SUN_DISTANCE'])
            else:
                y, m, d = (self.metadata['DATE_ACQUIRED']).split('-')
                y, m, d = int(y), int(m), int(d)

                if y % 4 != 0 or (y % 100 == 0 and y % 400 != 0):
                    v = 0
                else:
                    v = 1

                dm = [0, 31, 28 + v, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                DOY = 0

                for i in range(1, m):
                    DOY += dm[i]
                DOY += d - 1

                SCT = self.metadata['SCENE_CENTER_TIME']
                ho, mi, se = SCT[:-1].split(':')
                DOY += (int(ho) * 3600 + int(mi) * 60 + float(se)) / (24 * 3600)

                self.dsol = 1.00014 - 0.01671 * math.cos(2 * math.pi * (DOY - 3.4532868) / 365.256363)

            # init gain and offset
            self.gain = [float(self.metadata['RADIANCE_MULT_BAND_1']), float(self.metadata['RADIANCE_MULT_BAND_3']),
                         float(self.metadata['RADIANCE_MULT_BAND_4'])]
            self.offset = [float(self.metadata['RADIANCE_ADD_BAND_1']), float(self.metadata['RADIANCE_ADD_BAND_3']),
                           float(self.metadata['RADIANCE_ADD_BAND_4'])]

            # init images
            self.img_B1 = cv2.imread(path + 'B1.tif', cv2.IMREAD_GRAYSCALE)
            self.img_B3 = cv2.imread(path + 'B3.tif', cv2.IMREAD_GRAYSCALE)
            self.img_B4 = cv2.imread(path + 'B4.tif', cv2.IMREAD_GRAYSCALE)

            # will used variables
            self.img_fapar = cv2.imread(path + 'B1.tif', cv2.IMREAD_COLOR)
            self.mean_fapar = None

            if multiprocessing.current_process().name == 'MainProcess':
                print('[DEBUG] Init successfull')
            else:
                print('\t\t[DEBUG] Init successfull ', end='')
        except:
            print('[ERROR] Error during init procedure')

    def get(self, i, j):
        b, r, n = self.img_B1[i][j].astype(float), self.img_B3[i][j].astype(float), self.img_B4[i][j].astype(float)
        return self.__L7OF_value(b, r, n)
        # recalculating method (add pull from exsisting fapar image?)

    def __del__(self):
        pass

    def build_pool(self, mode):
        # calculate color image from source images
        if mode == 'color':
            for i in range(len(self.img_fapar)):
                for j in range(len(self.img_fapar[0])):
                    b, r, n = self.img_B1[i][j].astype(float), self.img_B3[i][j].astype(float), self.img_B4[i][
                        j].astype(float)
                    if b == 0 and r == 0 and n == 0:
                        self.img_fapar[i][j] = [255, 255, 255]
                    else:
                        self.img_fapar[i][j] = self.__L7OF_color(b, r, n)

            cv2.imwrite(self.path + 'FAPAR_' + time.strftime("%H-%M-%S", time.localtime()) + '.jpeg', self.img_fapar)
        # calculate mean fapar value from source images
        elif mode == 'value':
            count_fapar, mean_fapar = 0, 0.0

            for i in range(len(self.img_fapar)):
                for j in range(len(self.img_fapar[0])):
                    b, r, n = self.img_B1[i][j].astype(float), self.img_B3[i][j].astype(float), self.img_B4[i][
                        j].astype(float)
                    tmp = self.__L7OF_value(b, r, n)
                    if not (type(tmp) is str):
                        mean_fapar += tmp
                        count_fapar += 1

            self.mean_fapar = mean_fapar / count_fapar
            f = open(self.path + 'mean_fapar.txt', "w")
            f.write(str(self.mean_fapar))
            return self.mean_fapar
        # build index map
        elif mode == 'map':
            f = open(self.path + 'map.txt', "w")
            for i in range(len(self.img_fapar)):
                for j in range(len(self.img_fapar[0])):
                    b, r, n = self.img_B1[i][j].astype(float), self.img_B3[i][j].astype(float), self.img_B4[i][j].astype(float)
                    f.write(str(self.__L7OF_value(b, r, n)) + ' ')
                f.write('\n')
            f.close()
        # count color from map
        elif mode == 'color_map':
            f = open(self.path + 'map.txt', "r")
            for i in range(len(self.img_fapar)):
                s = f.readline()
                ls = s.split(' ')
                for j in range(len(self.img_fapar[0])):
                    self.img_fapar[i][j] = self.__color_by_fapar(ls[j])
            f.close()
            cv2.imwrite(self.path + 'FAPAR_' + time.strftime("%H-%M-%S", time.localtime()) + '.jpeg', self.img_fapar)
        # count value from map
        elif mode == 'value_map':
            mean_fapar, count_fapar = 0.0, 0

            f = open(self.path + 'map.txt', "r")
            for i in range(len(self.img_fapar)):
                s = f.readline()
                ls = s.split(' ')
                for j in range(len(self.img_fapar[0])):
                    if not (ls[j][0] == '<'):
                        mean_fapar += float(ls[j])
                        count_fapar += 1
            f.close()
            self.mean_fapar = mean_fapar / count_fapar
            f = open(self.path + 'mean_fapar.txt', "w")
            f.write(str(self.mean_fapar))
            return self.mean_fapar
        else:
            print('[ERROR] Error incorrect mode')

    def build_proc(self, mode, st=1, en=1):
        print('\t[THREAD] Thread ' + multiprocessing.current_process().name + ' engaged')

        st, en = len(self.img_fapar) * (st - 1) // en, len(self.img_fapar) * st // en

        if mode == 'color':
            for i in range(st, en):
                for j in range(len(self.img_fapar[0])):
                    b, r, n = self.img_B1[i][j].astype(float), self.img_B3[i][j].astype(float), self.img_B4[i][
                        j].astype(float)
                    if b == 0 and r == 0 and n == 0:
                        self.img_fapar[i][j] = [255, 255, 255]
                    else:
                        self.img_fapar[i][j] = self.__L7OF_color(b, r, n)

        elif mode == 'value':
            count_fapar, mean_fapar = 0, 0.0

            for i in range(st, en):
                for j in range(len(self.img_fapar[0])):
                    b, r, n = self.img_B1[i][j].astype(float), self.img_B3[i][j].astype(float), self.img_B4[i][
                        j].astype(float)
                    tmp = self.__L7OF_value(b, r, n)
                    if not (type(tmp) is str):
                        mean_fapar += tmp
                        count_fapar += 1

            # mean_fapar is not updating
            if multiprocessing.current_process().name == 'MainProcess':
                self.mean_fapar = mean_fapar / count_fapar
            else:
                f = open(self.path + 'fapar_value' + multiprocessing.current_process().name + '.txt', "w")
                f.write(str(mean_fapar / count_fapar))
                f.close()
        else:
            print('[ERROR] Error incorrect mode')
        print('\t[THREAD] Thread ' + multiprocessing.current_process().name + ' disengaged')

        if mode == 'value':
            return self.mean_fapar

    def get_mean(self):
        return self.mean_fapar

    def set_mean(self, lst):
        self.mean_fapar = 0
        for i in range(len(lst)):
            self.mean_fapar += lst[i]
        self.mean_fapar /= len(lst)

    # fapar calculation algorithm
    def __ro_star(self, n, ND):
        R = self.gain[n] * ND + self.offset[n]
        return math.pi * R * self.dsol ** 2 / self.E0[n] * math.cos(self.Oo)

    def __F(self, n):
        f1 = ((math.cos(self.Oo) * math.cos(self.Ov)) ** (self.k[n] - 1) / (math.cos(self.Oo) + math.cos(self.Ov)) ** (
                    1 - self.k[n]))

        cos_g = math.cos(self.Oo) * math.cos(self.Ov) + math.sin(self.Oo) * math.sin(self.Ov) * math.cos(self.phi)

        f2 = ((1 - self.hg[n] ** 2) / (1 + 2 * self.hg[n] * cos_g + self.hg[n] ** 2) ** 1.5)

        G = (math.tan(self.Oo) ** 2 + math.tan(self.Ov) ** 2 - 2 * math.tan(self.Oo) * math.tan(self.Ov) * math.cos(
            self.phi)) ** 0.5

        f3 = 1 + (1 - self.pic[n]) / (1 + G)

        return f1 * f2 * f3

    def __g12(self, x, y, n):
        return (self.l[n][1] * (x + self.l[n][2]) ** 2 + self.l[n][3] * (y + self.l[n][4]) ** 2 + self.l[n][
            5] * x * y) / (
                       self.l[n][6] * (x + self.l[n][7]) ** 2 + self.l[n][8] * (y + self.l[n][9]) ** 2 + self.l[n][
                   10] * x * y + self.l[n][11])

    def __g0(self, x, y, n=0):
        return (self.l[n][1] * y - self.l[n][2] * x - self.l[n][3]) / (
                    (self.l[n][4] - x) ** 2 + (self.l[n][5] - y) ** 2 + self.l[n][6])

    def __color_by_fapar(self, s):
        if s[0] == '<':
            if (s[-3] == '1'): return [0, 0, 0]  # bad data(1)
            if (s[-3] == '2'): return [255, 255, 0]  # cloud, snow, ice (2)
            if (s[-3] == '3'): return [128, 0, 0]  # water, shadow (3)
            if (s[-3] == '4'): return [255, 255, 255]  # bright surface (4)
            if (s[-3] == '5'): return [0, 0, 0]  # undefined (5)
        else:
            fapar = float(s)
            if (fapar <= 0): return [208, 255, 255]
            if (0 < fapar <= 0.25): return [150 - 10 * int(4 * fapar / 0.25), 255, 255]
            if (0.25 < fapar <= 0.5): return [50 - 10 * int(4 * (fapar - 0.25) / 0.25), 255,
                                              50 - 10 * int(4 * (fapar - 0.25) / 0.25)]
            if (0.5 < fapar <= 0.625): return [0, 200 - 10 * int(4 * (fapar - 0.5) / 0.125), 0]
            if (0.625 < fapar <= 0.75): return [0, 150 - 10 * int(4 * (fapar - 0.625) / 0.125), 0]
            if (0.75 < fapar < 1): return [0, 100 - 10 * int(4 * (fapar - 0.75) / 0.25), 0]
            if (1 <= fapar): return [0, 60, 0]


    # function for getting color by values
    def __L7OF_color(self, blue, red, nir):
        # 1 - Blue   3 - Red   4 - NIR

        ro_star_1 = self.__ro_star(0, blue)
        ro_star_3 = self.__ro_star(1, red)
        ro_star_4 = self.__ro_star(2, nir)

        blue, red, nir = ro_star_1, ro_star_3, ro_star_4

        if (blue <= 0 or red <= 0 or nir <= 0): return [0, 0, 0]  # bad data(1)
        if (blue >= 0.257752 or red >= 0.48407 or nir >= 0.683928): return [255, 255, 0]  # cloud, snow, ice (2)
        if ((0 < blue < 0.257752) and (0 < red < 0.48407) and (0 < nir < 0.683928)):
            if (blue > nir): return [128, 0, 0]  # water, shadow (3)
            if ((0 < blue <= nir) and (1.25 * red > nir)): return [255, 255, 255]  # bright surface (4)

        ro_tilda_1 = ro_star_1 / self.__F(1)
        ro_tilda_3 = ro_star_3 / self.__F(3)
        ro_tilda_4 = ro_star_4 / self.__F(4)

        # g1 and g2 functions
        ro_rred = self.__g12(ro_tilda_1, ro_tilda_3, 1)  # RO RRED with g1
        ro_rnir = self.__g12(ro_tilda_1, ro_tilda_4, 2)  # RO RNIR with g2

        if (ro_rred < 0 or ro_rnir < 0): return [0, 0, 0]  # undefined (5)

        # g0 function
        fapar = self.__g0(ro_rred, ro_rnir)

        if (fapar <= 0): return [208, 255, 255]
        if (0 < fapar <= 0.25): return [150 - 10 * int(4 * fapar / 0.25), 255, 255]
        if (0.25 < fapar <= 0.5): return [50 - 10 * int(4 * (fapar - 0.25) / 0.25), 255,
                                          50 - 10 * int(4 * (fapar - 0.25) / 0.25)]
        if (0.5 < fapar <= 0.625): return [0, 200 - 10 * int(4 * (fapar - 0.5) / 0.125), 0]
        if (0.625 < fapar <= 0.75): return [0, 150 - 10 * int(4 * (fapar - 0.625) / 0.125), 0]
        if (0.75 < fapar < 1): return [0, 100 - 10 * int(4 * (fapar - 0.75) / 0.25), 0]
        if (1 <= fapar): return [0, 60, 0]

    # function for getting fapar value
    def __L7OF_value(self, blue, red, nir):
        # 1 - Blue   3 - Red   4 - NIR

        ro_star_1 = self.__ro_star(0, blue)
        ro_star_3 = self.__ro_star(1, red)
        ro_star_4 = self.__ro_star(2, nir)

        blue, red, nir = ro_star_1, ro_star_3, ro_star_4

        if (blue <= 0 or red <= 0 or nir <= 0): return '<bad_data(1)>'
        if (blue >= 0.257752 or red >= 0.48407 or nir >= 0.683928): '<cloud_snow_ice(2)>'
        if ((0 < blue < 0.257752) and (0 < red < 0.48407) and (0 < nir < 0.683928)):
            if (blue > nir): return '<water_shadow(3)>'
            if ((0 < blue <= nir) and (1.25 * red > nir)): return '<bright_surface(4)>'

        ro_tilda_1 = ro_star_1 / self.__F(1)
        ro_tilda_3 = ro_star_3 / self.__F(3)
        ro_tilda_4 = ro_star_4 / self.__F(4)

        ro_rred = self.__g12(ro_tilda_1, ro_tilda_3, 1)
        ro_rnir = self.__g12(ro_tilda_1, ro_tilda_4, 2)

        if (ro_rred < 0 or ro_rnir < 0): return '<undefined(5)>'

        fapar = self.__g0(ro_rred, ro_rnir)

        return fapar
