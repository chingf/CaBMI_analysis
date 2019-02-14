# 


#*************************************************************************
#************************ UTILS *****************
#*************************************************************************


__author__ = 'Nuria'


import numpy as np
import pdb       

def calc_pvalue(p_value):
    if p_value < 0.0005:
        p = '***'
    elif p_value < 0.005:
        p = '**'
    elif p_value < 0.05:
        p = '*'
    else:
        p = 'ns'
    return p


def sliding_mean(data_array, window=5):
    # program to smooth a graphic
    data_array = np.array(data_array)
    new_list = []
    for i in range(np.size(data_array)):
        indices = range(max(i - window + 1, 0),
                        min(i + window + 1, np.size(data_array)))
        avg = 0
        for j in indices:
            avg = np.nansum([avg, data_array[j]])
        avg /= float(np.size(indices))
        new_list.append(avg)
    return np.array(new_list)

def time_lock_activity(f, t_size=[30,3], tbin=10):
    '''
    Creates a 3d matrix time-locking activity to trial end.
    Input:
        F: a File object; the experiment HDF5 file
        T_SIZE: an array; the first value is the number of
            seconds total to keep. The second value
            is the number of seconds after the trial end to keep.
        T_BIN: an integer; the number of frames per second

    Output:
        NEURON_ACTIVITY: a numpy matrix; (trials x neurons x frames)
            in size.
    '''
    trial_start = np.asarray(f['trial_start']).astype('int')
    trial_end = np.asarray(f['trial_end']).astype('int')

    C = np.asarray(f['C'])
    neuron_activity = np.ones(
        (trial_end.shape[0], C.shape[0], np.sum(t_size)*tbin)
        )*np.nan # (num_trials x num_neurons x num_frames)
    for ind, trial in enumerate(trial_end):
        aux_act = C[:, trial_start[ind]:trial + t_size[1]*tbin]
        neuron_activity[ind, :, -aux_act.shape[1]:] = aux_act
    return neuron_activity
