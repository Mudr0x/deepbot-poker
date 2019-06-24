#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 12:23:22 2019

@author: cyril
"""

import mkl
mkl.set_num_threads(64)
import os 
import numpy as np
import pickle
from bot_LSTMBot import LSTMBot    
import random
import torch
from sys import getsizeof
from collections import OrderedDict
from operator import add


def select_next_gen_bots(log_dir, simul_id, gen_id, all_earnings, BB, nb_bots, all_gen_flat, method = 'GA', nb_gens= 250, network='first', nb_opps=4, normalize=True):
    mkl.set_num_threads(64)
    #old_gen_dir = log_dir+'/simul_'+str(simul_id)+'/gen_'+str(gen_id)
    #creating new generation directory
    lstm_ref = LSTMBot(None, network=network)
    
    if method =='GA':
        ANEs = compute_ANE(all_earnings=all_earnings, BB=BB, nb_bots=nb_bots, nb_opps=nb_opps, normalize=normalize)
        ord_bot_ids = [el+1 for el in sorted(range(len(ANEs)), key=lambda i:ANEs[i], reverse=True)]

        #SELECTING SURVIVORS
        surv_perc = 0.3
        surv_bot_ids = ord_bot_ids[:int(surv_perc*nb_bots)]  
        surv_bots_flat = []
        for bot_id in surv_bot_ids:
            surv_bot_flat = all_gen_flat[bot_id-1]
            surv_bots_flat.append(surv_bot_flat)      
        surv_ANEs = [ANEs[i-1] for i in surv_bot_ids]
        
        ## SELECTING ELITE BOTS
        elite_bot_ids = [id_ for id_ in surv_bot_ids if (ANEs[id_-1]) > sum(surv_ANEs)/float(len(surv_ANEs))]#[:int(len(surv_bot_ids)/2)]      
        print('surv ANEs: ' +str(surv_ANEs))
        print('avg surv ANEs: ' + str(sum(surv_ANEs)/float(len(surv_ANEs))))
        
        if len(elite_bot_ids) == 0 or len(elite_bot_ids)==len(surv_bot_ids):
            elite_bot_ids = [surv_bot_ids[i] for i in range(int(len(surv_bot_ids)))]
            print('[Warning] There were no elite (all equal), picking all survivors as elite')
        
        
        ## Verify that one opponent is not 'left behind', as in unbeaten by elites
        elite_earnings = np.array([list(all_earnings[elite_bot_ids[i]-1].values()) for i in range(len(elite_bot_ids))])
        if any(elite_earnings[0]<=0): #one opponent bot is not being beaten
            balanced = False
            for i in range(1, len(elite_earnings)):
                if all((elite_earnings[0] + elite_earnings[i]) >0):
                    balanced = True
                    break
            if balanced==False:
                print('Elites are sligthly unbalanced vs opponents, attempting correction')
                for bot_id in ord_bot_ids[1:]:
                    if all((elite_earnings[0] + np.array(list(all_earnings[bot_id-1].values()))) >0):
                        print('Found a strong bot to get balanced elites, it has following earnings: '+str((all_earnings[bot_id-1])))
                        elite_bot_ids = elite_bot_ids + [bot_id]
                        balanced = True
                        break
            if balanced==False:
                print('Elites remain slightly unbalanced')
                if all(np.max(elite_earnings, axis=0)>0):
                    balanced = True
                else:
                    print('Elites are very unbalanced vs opponents, attempting correction')   
            if balanced==False:
                lost_opp_ids = elite_earnings[0]<=0
                for k in range(sum(lost_opp_ids)):
                    for bot_id in ord_bot_ids[1:]:
                        if np.array(list(all_earnings[bot_id-1].values()))[lost_opp_ids][k] >0:
                            print('Found a weak bot to get more balanced elites, it has following earnings: '+str((all_earnings[bot_id-1])))
                            elite_bot_ids = elite_bot_ids + [bot_id]
                            break
            #if balanced==False:
                #print('Elites remain very unbalanced vs opponents')
            
                
        if len(elite_bot_ids) ==1:  
            elite_bot_ids = elite_bot_ids + [surv_bot_ids[random.randint(1,len(surv_bot_ids)-1)]]   #if there is only one elite, add other one from survivors
            print('There was only one elite, adding a random survivor as elite')

        ##Preparing elite bots
        elite_bots_flat = []
        for bot_id in elite_bot_ids:
            elite_bots_flat.append(all_gen_flat[bot_id-1])
            
        ## SELECTING SECOND TIER BOTS
        sec_tier_bot_ids = [id_ for id_ in surv_bot_ids if id_ not in elite_bot_ids]
        ##Preparing elite bots
        sec_tier_bots_flat = []
        for bot_id in sec_tier_bot_ids:
            sec_tier_bots_flat.append(all_gen_flat[bot_id-1])
                
        print('Nb surviving bots: ' +str(len(surv_bot_ids))+ ', nb elite bots: '+str(len(elite_bot_ids)))
    
        nb_new_crossover = nb_bots- len(surv_bot_ids)
        cross_bots_flat = crossover_bots(parent_bots_flat = elite_bots_flat, m_sizes_ref = lstm_ref, nb_new_bots = nb_new_crossover)
        print('done cross')
        nb_new_mutant = nb_bots - len(elite_bot_ids)
        mut_rate = 0.3 - 0.25*gen_id/nb_gens #0.25 - 0.2*gen_id/nb_gens# ##important values
        mut_strength =  0.5 - 0.4*gen_id/nb_gens #0.5 - 0.4*gen_id/nb_gens #
        mutant_bots_flat = mutate_bots(orig_bots_flat = sec_tier_bots_flat+cross_bots_flat, nb_new_bots = nb_new_mutant,
                                  mut_rate=mut_rate , mut_strength=mut_strength)
        print('done mutation')
        new_gen_bots = elite_bots_flat+mutant_bots_flat
        
    elif method=='ASE':
        pass
    return new_gen_bots


def crossover_bots(parent_bots_flat, m_sizes_ref, nb_new_bots):
    cross_bots = []
    for i in range(nb_new_bots):
        #random approach, parents are selected randomly
        while(True):
            first_parent_id = random.randint(0,len(parent_bots_flat)-1)
            second_parent_id = random.randint(0,len(parent_bots_flat)-1)
            if(first_parent_id != second_parent_id):
                break
        first_parent = parent_bots_flat[first_parent_id]
        second_parent = parent_bots_flat[second_parent_id]

        #deterministic approach, each elite crosses with each other elite
        """
        for i in range(len(parent_bots_flat)):
            for j in range(i+1,len(parent_bots_flat)):
                first_parent = parent_bots_flat[i]
                second_parent = parent_bots_flat[j]
        """
        
        #taking even and odd weights
        #child_flat_params = torch.Tensor([first_parent[k].float() if k%2==0 else second_parent[k].float() for k in range(len(first_parent))])
        
        #taking mean weight
        #child_flat_params = [(first_parent[k] + second_parent[k])/2 for k in range(len(first_parent))]
        
        
        #taking by layer
        dict_sizes=get_dict_sizes(m_sizes_ref.state_dict,m_sizes_ref.model.i_opp,m_sizes_ref.model.i_gen)
        i_start=0
        child_flat_params = []
        for layer in sorted(dict_sizes.keys()):
            if layer == 'lin_dec_1.weight':  #special case for very large dense layer
                for i in range(int(dict_sizes[layer]['numel']/500)): # splitting by groups of 500
                    if random.random()<0.5:
                        child_flat_params= child_flat_params+list(first_parent[i_start:i_start+500])
                    else:
                        child_flat_params = child_flat_params+list(second_parent[i_start:i_start+500])                
                    i_start+=500
            else:
                if random.random()<0.5:
                    child_flat_params= child_flat_params+list(first_parent[i_start:i_start+dict_sizes[layer]['numel']])
                else:
                    child_flat_params = child_flat_params+list(second_parent[i_start:i_start+dict_sizes[layer]['numel']])
                i_start+=dict_sizes[layer]['numel']
        
            
        cross_bots.append(torch.Tensor(child_flat_params))
    return cross_bots#[:30] # truncate to leave some spots for mutants






def mutate_bots(orig_bots_flat, mut_rate, mut_strength, nb_new_bots):
    mutant_bots=[]
    for i in range(nb_new_bots):
        orig_bot = orig_bots_flat[i%len(orig_bots_flat)]
        mutant_flat_params = torch.Tensor([orig_gene.float() if random.random()>mut_rate else  orig_gene.float() + random.gauss(mu=0, sigma=mut_strength) for orig_gene in orig_bot])
        mutant_bots.append(mutant_flat_params)
    return mutant_bots
    


def compute_ANE(all_earnings, BB, nb_bots=50, load = False, gen_dir = None, nb_opps = 4, normalize=True):
    if load:
        all_earnings = [0,]*nb_bots
        for bot_id in range (1,nb_bots+1):
            with open(gen_dir+'/bots/'+str(bot_id)+'/earnings.pkl', 'rb') as f:  
                all_earnings[bot_id-1] = pickle.load(f)
        
    earnings_arr = np.array([list(earning.values()) for earning in all_earnings])
    
    if normalize==True:
        #set all values to positive
       # earnings_arr = [list(earning) for earning in earnings_arr]   
        n_j_pos = np.max([BB*np.ones(nb_opps),np.max(earnings_arr,axis=0)], axis=0)
        n_j_neg = np.max([BB*np.ones(nb_opps),np.abs(np.min(earnings_arr,axis=0))], axis=0)
        print('ANEs positive normalization factors: ' +str(n_j_pos))
        print('ANEs begative normalization factors: ' +str(n_j_neg))
        #alternative approach
    
        #use average earnings
        #n_j = np.max([np.sqrt(BB*np.ones(nb_opps)),np.average(earnings_arr,axis=0)], axis=0)
        
        ANEs = np.sum(np.where(earnings_arr>0, earnings_arr/n_j_pos, earnings_arr/n_j_neg), axis = 1)/nb_opps
    else:
        ANEs = np.sum(earnings_arr, axis = 1)/nb_opps
    return ANEs


def get_flat_params(full_dict):
    params = torch.Tensor(0)
    for key in sorted(full_dict.keys()):
        params = torch.cat((params, full_dict[key].view(-1)),0)  
    return params

def get_full_dict(all_params, m_sizes_ref):
    dict_sizes=get_dict_sizes(m_sizes_ref.state_dict,m_sizes_ref.model.i_opp,m_sizes_ref.model.i_gen)
    full_dict = OrderedDict()
    i_start = 0
    for layer in sorted(dict_sizes.keys()):
        full_dict[layer] = torch.Tensor(all_params[i_start:i_start+dict_sizes[layer]['numel']]).view(dict_sizes[layer]['shape'])
        i_start+=dict_sizes[layer]['numel']
    return full_dict


def get_dict_sizes(state_dict, i_opp, i_gen):
    dict_sizes = OrderedDict()
    all_dicts = state_dict.copy()
    all_dicts.update(i_opp), all_dicts.update(i_gen)
    for key in all_dicts.keys():
        dict_sizes[key] = {}
        dict_sizes[key]['numel'] = all_dicts[key].numel()
        dict_sizes[key]['shape'] = list(all_dicts[key].shape)
    return dict_sizes

def get_best_ANE_earnings(all_earnings, BB=100, nb_bots = 50, nb_opps=4, normalize=True):
    ANEs = compute_ANE(all_earnings=all_earnings, BB=BB, nb_bots=nb_bots, nb_opps=nb_opps, normalize=normalize)
    best_bot_id = [el for el in sorted(range(len(ANEs)), key=lambda i:ANEs[i], reverse=True)][0]
    return all_earnings[best_bot_id]
    #print('Highest ANE is ' + str(max(ANEs) )
    