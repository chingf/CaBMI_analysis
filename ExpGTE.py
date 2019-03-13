import warnings
import h5py
import numpy as np
from utils_gte import *
from utils_cabmi import *

class ExpGTE:
    """A class that wraps around an experiment and runs GTE in various ways"""

    whole_exp_results = None
    reward_end_results = None
    reward_sliding_results = None
    reward_shuffled = None

    def __init__(self, folder, animal, day, sec_var=''):
        self.folder = folder
        self.animal = animal
        self.day = day
        self.parameters = {
            'bins':5, 'SourceMarkovOrder':2, 'TargetMarkovOrder':2
            }
        folder_path = folder +  'processed/' + animal + '/' + day + '/'
        self.exp_file = h5py.File(
            folder_path + 'full_' + animal + '_' + day + '_' +
            sec_var + '_data.hdf5', 'r'
            )

    def whole_experiment(self, parameters=None,
        to_plot=True, pickle_results = True):
        '''
        Run GTE over all neurons, over the whole experiment.
        Inputs:
            PARAMETERS: Dictionary; parameters for GTE
            TO_PLOT: Boolean; whether or not to call the visualization script
            PICKLE_RESULTS: Boolean; whether or not to save the results matrix
        Outputs:
            RESULTS: An array of numpy matrices (GTE connectivity matrices)
        '''
        exp_name = self.animal + '_' + self.day + '_' + 'whole'
        exp_data = np.array(self.exp_file['C']) # (neurons x frames)
        exp_data = np.expand_dims(exp_data, axis=0) # (1 x neurons x frames)
        neuron_locations = np.array(self.exp_file['com_cm'])
        if parameters is None:
            parameters = self.parameters
        control_file_names, exclude_file_names, output_file_names = \
            create_gte_input_files(exp_name, exp_data, parameters)
        results = run_gte(control_file_names, exclude_file_names,
            output_file_names, pickle_results)
        if to_plot:
            visualize_gte_results(results, neuron_locations)
        delete_gte_files(exp_name, delete_output=False)
        self.whole_exp_results = results
        return results
    
    def reward_end(self, frame_size, parameters=None,
        to_plot=True, pickle_results=True):
        '''
        Run general transfer of entropy in the last FRAME_SIZE frames before
        a hit, over all reward trials. Return an array of connectivity matrices
        over each reward trial.
        Inputs:
            FRAME_SIZE: Integer; number of frames before the hit to consider.
            PARAMETERS: Dictionary; parameters for GTE
            TO_PLOT: Boolean; whether or not to call the visualization script
            PICKLE_RESULTS: Boolean; whether or not to save the results matrix 
        Outputs:
            RESULTS: An array of numpy matrices (GTE connectivity matrices) 
        '''
        exp_name = self.animal + '_' + self.day + '_' + 'rewardend'
        exp_data = time_lock_activity(self.exp_file, t_size=[frame_size,0])
        array_t1 = np.array(self.exp_file['array_t1'])
        exp_data = exp_data[array_t1,:,:] 
        neuron_locations = np.array(self.exp_file['com_cm'])
        if parameters is None:
            parameters = self.parameters

        control_file_names, exclude_file_names, output_file_names = \
            create_gte_input_files(exp_name, exp_data, parameters)
        results = run_gte(control_file_names, exclude_file_names,
            output_file_names, pickle_results)
        if to_plot:
            visualize_gte_results(results, neuron_locations)
        delete_gte_files(exp_name, delete_output=False)
        self.reward_end_results = results
        return results

    def reward_sliding(self, frame_size, frame_step, parameters=None,
        to_plot=True, pickle_results=True):
        '''
        Run general transfer of entropy over each reward trial, with a sliding
        window of size FRAME_SIZE.
        Inputs:
            FRAME_SIZE: Integer; number of frames to process in GTE.
            FRAME_STEP: Integer; number of frames for each step through signal.
            PARAMETERS: Dictionary; parameters for GTE.
            TO_PLOT: Boolean; whether or not to call the visualization script.
            PICKLE_RESULTS: Boolean; whether or not to save the results matrix.
        Outputs:
            RESULTS: An array of arrays of numpy matrices; e.g., RESULTS[i]
                is the array of numpy matrices for running sliding GTE over the
                ith reward trial. For some reward trial i, if the length of the
                trial is too short to run GTE of length FRAME_SIZE, then
                RESULTS[i] = [].
        '''
        exp_name = self.animal + '_' + self.day + '_' + 'rewardsliding'
        exp_data = time_lock_activity(self.exp_file)
        array_t1 = np.array(self.exp_file['array_t1'])
        exp_data = exp_data[array_t1,:,:]
        num_rewards, num_neurons, num_frames = exp_data.shape
        neuron_locations = np.array(self.exp_file['com_cm'])
        if parameters is None:
            parameters = self.parameters
        results = []

        # Try to run sliding GTE over each reward trial.
        for reward_idx in range(num_rewards):
            # Chop off the NaN sections of the reward trial.
            reward_data = exp_data[reward_idx,:,:]
            if np.sum(np.isnan(reward_data[0,:])) == 0:
                non_nan_idx = 0
            else:
                non_nan_idx = np.where(np.isnan(reward_data[0,:]))[0][-1] + 1
            reward_data = reward_data[:,non_nan_idx:]

            # If the reward trial is too short, skip it.
            if reward_data.shape[1] > frame_size:
                results.append([])
                continue

            # Otherwise, run GTE as normal
            control_file_names, exclude_file_names, output_file_names = \
                create_gte_input_files(
                    exp_name, reward_data, parameters, frame_size, frame_step
                    )
            result = run_gte(
                control_file_names, exclude_file_names,
                output_file_names, pickle_results
                )
            if to_plot:
                print("Plotting reward trial " + str(reward_idx) + ".")
                visualize_gte_results(result, neuron_locations)
            delete_gte_files(exp_name, delete_output=False)
            results.append(result)
        self.reward_sliding_results = results
        return results

    def group_results(self, results_type, grouping, to_plot=True):
        '''
        Groups an existing GTE connectivity matrix by averaging scores
        over user-defined groupings of neurons. Here it is assumed that GTE
        is already run; otherwise, an exception is thrown.
        Inputs:
            RESULTS_TYPE: a String; indicates which matrix to use for grouping.
            GROUPING: Numpy array of NUM_NEURONS size; an integer ID is given
                to each neuron, defining their group. This array is 0-indexed.
        Outputs:
            GROUPED_RESULTS: An array of numpy matrices (GTE connectivity matrices) 
        '''
        results = None
        if results_type == "whole":
            results = self.whole_exp_results
        elif results_type == "reward_end":
            results = self.reward_end_results
        elif results_type == "reward_early":
            results = self.reward_early_results
        elif results_type == "reward_late":
            results = self.reward_late_results
        if results is None:
            raise RuntimeError('No results for the function to load. ' +
                'Please check that GTE is already run and check the correct ' +
                'key word was used in function GROUP_RESULTS.')
        num_neurons = results[0].shape[0]
        num_groups = np.unique(grouping).size
        if grouping.size != num_neurons:
            raise RuntimeError('Wrong dimensions for GROUPING')

        grouped_results = []
        for result in results:
            grouped_result = np.zeros((num_groups, num_groups))
            for i in range(num_groups):
                for j in range(num_groups):
                    if i == j:
                        continue
                    relevant_vals = []
                    for k in range(num_neurons):
                        if grouping[k] != i:
                            continue
                        for l in range(num_neurons):
                            if grouping[l] != j:
                                continue
                            relevant_vals.append(result[k, l])
                    grouped_result[i, j] = np.mean(relevant_vals)
            grouped_results.append(grouped_result)
        if to_plot:
            visualize_gte_matrices(grouped_results)
        return grouped_results

    def shuffled_results(self, frame_size, parameters=None,
        iters=100):
        '''
        Runs GTE over 'shuffled' instances of neurons over the whole experiment.
        Returns the average over many of these results.
        Inputs:
            FRAME_SIZE: Integer; number of frames to process in GTE
            PARAMETERS: Dictionary; parameters for GTE.
            ITERS: Number of 'shuffled' samples to take and average over.
        Outputs:
            RESULT: A GTE connectivity matrix
        '''

        exp_name = self.animal + '_' + self.day + '_' + 'rewardshuffled'
        exp_data = time_lock_activity(self.exp_file, t_size=[300,0])
        array_t1 = np.array(self.exp_file['array_t1'])
        exp_data = exp_data[array_t1,:,:]

        # Extract only reward trials that are long enough to sample from
        sufficient_trials = []
        for i in range(exp_data.shape[0]):
            if np.sum(np.isnan(exp_data[i,0,:])) == 0:
                sufficient_trials.append(i)
                continue
            non_nan_idx = np.where(np.isnan(exp_data[i,0,:]))[0][-1] + 1
            if (exp_data.shape[2] - non_nan_idx) >= frame_size:
                sufficient_trials.append(i)
        exp_data = exp_data[sufficient_trials,:,:]
        
        # Extract out 'shuffled' windows to use
        num_rewards = exp_data.shape[0]
        num_neurons = exp_data.shape[1]
        num_frames = exp_data.shape[2]
        shuffled_data = np.zeros((iters, num_neurons, num_frames))
        for i in range(iters):
            for j in range(num_neurons):
                # Sample the reward trial to use
                reward_idx = np.random.choice(num_rewards)
                # Sample the frame to start on, excluding Nans
                full_signal = exp_data[reward_idx,j,:]
                if np.sum(np.isnan(full_signal)) > 0:
                    non_nan_idx = np.where(np.isnan(full_signal))[0][-1] + 1
                else:
                    non_nan_idx = 0
                valid_frame_idxs = \
                    np.arange(non_nan_idx, num_frames-frame_size+1)
                frame_idx = np.random.choice(valid_frame_idxs)
                shuffled_data[i,j,:] = exp_data[reward_idx, j, frame_idx]
        neuron_locations = np.array(self.exp_file['com_cm'])
        if parameters is None:
            parameters = self.parameters
        
        # Run GTE on shuffled data
        control_file_names, exclude_file_names, output_file_names = \
            create_gte_input_files(exp_name, shuffled_data, parameters)
        results = run_gte(control_file_names, exclude_file_names,
            output_file_names, pickle_results)
        delete_gte_files(exp_name, delete_output=False)
        self.reward_shuffled = np.mean(results) #TODO: fix
        return self.reward_shuffled
