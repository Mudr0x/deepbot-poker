#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 14:19:23 2019

@author: cyril
"""
import pickle
import numpy as np 

###CONSTANTS

gen_id=-1
nb_bots= 1
log_dir = '../../../backed_simuls/'
log_dir = './simul_data/'
sb_amount = 50
ini_stack = 3000
hands_per_match=1000

#my_network = 'second'
simul_id = '-1'

with open(log_dir+'/simul_'+str(simul_id)+'/bot_earnings.pkl', 'rb') as f:  
    all_earnings = pickle.load(f)

     
avg_earning = np.average([list(all_earnings[i][0].values()) for i in range(len(all_earnings))],axis=0)
std_earning = np.std([list(all_earnings[i][0].values()) for i in range(len(all_earnings))],axis=0)
print(all_earnings)
print('')
#print(all_earnings[0])
print('')
print(np.average(avg_earning))
#print(avg_earning/hands_per_match/(2*sb_amount)*1000)

#print(std_earning)
