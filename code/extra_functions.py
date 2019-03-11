#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 14:59:03 2019

@author: cyril
"""

import random
import numpy as np
from Xlib import display, X
from PIL import Image #PIL

def getRandDistrParams():
    beta_=random.uniform(0.1,5);
    alpha_smart=random.uniform(beta_,5);
    alpha_balanced=random.uniform(0.1,5);
    return beta_, alpha_smart, alpha_balanced



def angle_between(v1, v2):
    return np.degrees(np.math.atan2(np.linalg.det([v2,v1]),np.dot(v2,v1)))


def screenTablePortion(left=0,top=0,width=0,height=0):
    ##Get screenshot of the table##
    dsp = display.Display()
    root = dsp.screen().root
    raw = root.get_image(left, top, width,height, X.ZPixmap, 0xffffffff)
    table_img = Image.frombytes("RGB", (width, height), raw.data, "raw", "BGRX").convert('L')
    return table_img