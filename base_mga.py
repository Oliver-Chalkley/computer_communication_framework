from abc import ABCMeta, abstractmethod # Used to define abstract classes which is needed for the MGA class
import random # Some of the instance methods from the WholeCellModelBase class need the random library
import re
import operator
import numpy as np

class MGA(metaclass=ABCMeta):
    """
    This is an abstract class that all multi-generation algorithms inherit from. The idea is that the multi generation algorithm will want to repeatedly send jobs to (potentially multiple) computer clusters. With each generation the previous generation is made up of the parentjobs and the new generation is made up of the child jobs. This is so that information can be passed from generation to generation should the algorithm wish to do so.
    
    This class will assume that all connections are child classes of the base_connection.Connection class and all job submissions and job submission management classes are children of the relavent base_cluster_submissions class.
    """
    def __init__(self, dict_of_cluster_instances, MGA_name, relative2clusterBasePath_simulation_output_path, repetitions_of_a_unique_simulation, checkStopFuncName, checkStop_params_dict, getNewGenerationFuncName, newGen_params_dict, runSimulationsFuncName, runSims_params_dict, temp_storage_path):
        """
        This creates a basis for a multi-generation algorithm class.

        Args:
            dict_of_cluster_instances (dict): Each cluster instance is an object that is a child class of the base_connection.Connection class and represents a portal to a cluster or remote computer. The cluster instances are the values of the dictionary and the corresponding key is some string that represents some label of the cluster (these should be unique and it would be good for your records if you are consistent).
            MGA_name (str): The name of the multi-generation algorithm to be used as labels and names and records etc.
            relative2clusterBasePath_simulation_output_path (str): Each cluster connection instance has a base path depending on the cluster. This is the base path (i.e. the initial directory of this multi-generation algorithm) that will be apended to the cluster base path. More sub-directories will be created for each generation etc.
            repetitions_of_a_unique_simulation (int): The number of times each simulation needs to be repeated.
        """
        self.cluster_instances_dict = dict_of_cluster_instances
        self.generation_counter = None
        self.MGA_name = MGA_name
        self.relative2clusterBasePath_simulation_output_path = relative2clusterBasePath_simulation_output_path
        self.reps_of_unique_sim = repetitions_of_a_unique_simulation
        self.checkStopFuncName = checkStopFuncName
        self.checkStop_params_dict = checkStop_params_dict
        self.getNewGenerationFuncName = getNewGenerationFuncName
        self.newGen_params_dict = newGen_params_dict
        self.runSimulationsFuncName = runSimulationsFuncName
        self.runSims_params_dict = runSims_params_dict
        self.temp_storage_path = temp_storage_path

    # instance methods
    def run(self):
        if self.generation_counter == None:
            self.generation_counter = 0
        while getattr(self, self.checkStopFuncName)(self.checkStop_params_dict) != True:
            self.run_sim_out = self.runSimulations(self.runSimulationsFuncName, self.runSims_params_dict) 
            self.generation_counter += 1
            print('Next generation is ', self.generation_counter)

        # generation counter is one too high so remove it
        self.generation_counter -= 1

    def runSimulations(self, runSimulationsFuncDict, runSims_params_dict):
        return getattr(self, runSimulationsFuncDict)(runSims_params_dict)

    def standardRunSimulationsUT(self, runSims_params_dict):
        # This is just to test that the run method works OK
        pass

    def standardRunSimulations(self, runSims_params_dict):
        # get the new children
        # The child name (i.e. key) will be the name used to describe the individual child. The value must contaiin all the arguements neccessary to create a job on the cluster to simulate (or whatever else it might be) the child.
        child_name_to_genome_dict = self.getNewGenerationFunction(self.getNewGenerationFuncName, self.newGen_params_dict)
        
        # spread the children across clusters
        child_name_to_genome_dict_per_cluster = self.spreadChildrenAcrossClusters(child_name_to_genome_dict)

        # spread children-by-cluster across jobs
        child_name_to_genome_dict_per_cluster = self.spreadChildrenAcrossJobs(child_name_to_genome_dict_per_cluster)

        # submit generation to the cluster
        dict_of_job_submission_insts = {}
        dict_of_job_management_insts = {}
        list_of_cluster_instance_keys = list(self.cluster_instances_dict.keys()) 
        # create submission instances
        for cluster_connection in list_of_cluster_instance_keys:
            if type(child_name_to_genome_dict_per_cluster[cluster_connection]) is not list:
                raise TypeError('child_name_to_genome_dict_per_cluster[cluster_connection] must be a list! This is because there can potentially be more than one dictionary of jobs passed to one cluster and so (even if there is only one ditionary) the dictionaries must be in a list. Here type(child_name_to_genome_dict_per_cluster[cluster_connection]) = ', type(child_name_to_genome_dict_per_cluster[cluster_connection]))

            inner_loop_counter = 1
            for single_child_name_to_genome_dict in child_name_to_genome_dict_per_cluster[cluster_connection]:
                createJobSubmisions_params_dict = runSims_params_dict['createJobSubmisions_params_dict'].copy()
                createJobSubmisions_params_dict['cluster_conn'] = self.cluster_instances_dict[cluster_connection]
                createJobSubmisions_params_dict['single_child_name_to_genome_dict'] = single_child_name_to_genome_dict.copy()
                dict_of_job_submission_insts[cluster_connection + '_' + str(inner_loop_counter)] = self.createJobSubmissionInstance(runSims_params_dict['createJobSubmissionFuncName'], createJobSubmisions_params_dict)
                #, self.cluster_instances_dict[cluster_connection], single_child_name_to_genome_dict)
                inner_loop_counter += 1

        # send all jobs to clusters 
        list_of_dict_of_job_management_instances = self.submitAndMonitorJobsOnCluster(dict_of_job_submission_insts)

        # convert list into the dict that the rest of the library is expecting
        dict_of_job_management_insts = {list(dict_of_job_submission_insts.keys())[idx]: list_of_dict_of_job_management_instances[idx] for idx in range(len(dict_of_job_submission_insts))}

        # Perform all tasks neccessary after a generation of simulations has finished
        for cluster_connection in dict_of_job_submission_insts.keys():
            self.postSimulationFunction(dict_of_job_submission_insts[cluster_connection], dict_of_job_management_insts[cluster_connection])

        return

    def getNewGenerationFunction(self, getNewGenerationFuncName, newGen_params_dict):
        return getattr(self, getNewGenerationFuncName)(newGen_params_dict)

    ### METHODS THAT DECIDE WHEN TO STOP

    def checkStop(self, checkStopFuncName, checkStop_params_dict):
        return getattr(self, checkStopFuncName)(checkStop_params_dict)

    def stopAtMaxGeneration(self, max_gen_dict):
        if 'max_generation' in max_gen_dict:
            if self.generation_counter <= max_gen_dict['max_generation']:
                output = False
            else:
                output = True
        else:
            raise ValueError('You have not input a valid type of stopping the multi-generation algorithm. Here max_gen_dict[\'stop_type\'] =', max_gen_dict['stop_type'])

        return output
 
    ### METHODS TO GET THE POPULATION SIZE

    def getPopulationSize(self, getPopulationSizeFuncName, popSize_params_dict):
        return getattr(self, getPopulationSizeFuncName)(popSize_params_dict)

    def getPopulationSizeFromDict(self, generation_num_to_gen_size_dict):
        """
        Returns the size of the current generation. The MGA that uses this function must have a class variable called self.generation_num_to_gen_size_dict where the keys are generation numbers and the value corresponds the size of that generation. If there is not a key equal to the current generation then self.generation_num_to_gen_size_dict[-1] will be used.

        Returns:
            generation_size (int): The number of children to be created in the current generation.
        """
        
        important_generation_numbers = list(generation_num_to_gen_size_dict.keys())
        if important_generation_numbers.count(self.generation_counter) > 0:
                generation_size = generation_num_to_gen_size_dict[self.generation_counter]
        else:   
                generation_size = generation_num_to_gen_size_dict[-1]

        return generation_size

    # METHODS TO GET GENERATION NAMES

    def getGenerationNameSimple(self, genName_params_dict):
        """
        Gives a name for a generation in the form of:
            generation_name = 'gen' + str(self.generation_counter)

        Returns:
            generation_name (str): A simple name for the current generation.
        """

        prefix = genName_params_dict['prefix']
        # set name prefix
        if prefix is None:
            prefix = 'gen'
        elif type(prefix) is str:
            pass
        else:
            raise TypeError('prefix must be either None or a string. prefix = ', prefix, ' and type(prefix) = ', type(prefix))

        generation_name = prefix + str(self.generation_counter)

        return generation_name

    def getGenerationName(self, getGenNameFuncName, genName_params_dict):
        return getattr(self, getGenNameFuncName)(genName_params_dict)

    # METHODS TO SPLIT JOBS OVER MULTIPLE CLUSTERS

    def spreadChildrenAcrossClusters(self, child_name_to_genome_dict):
        child_names_list = list(child_name_to_genome_dict.keys())
        no_of_children = len(child_names_list)
        # split them across clusters
        no_of_clusters = len(self.cluster_instances_dict.keys())
        children_per_cluster = int(no_of_children/no_of_clusters)
        # calculate the remainder
        remainder = no_of_children - (no_of_clusters * children_per_cluster)
        child_name_to_genome_dict_per_cluster = {}
        previous_idx = 0
        list_of_cluster_instance_keys = list(self.cluster_instances_dict.keys()) # we create this list because in most version of Python dictionary keys have no order so here we force a consistent order.
        for cluster_idx in range(len(self.cluster_instances_dict.keys())):
            cluster = list_of_cluster_instance_keys[cluster_idx]
            last_name_idx = (cluster_idx + 1) * children_per_cluster
            if remainder > 0:
                last_name_idx += 1
                remainder -= 1

            child_name_to_genome_dict_per_cluster[cluster] = {child_names_list[idx]: child_name_to_genome_dict[child_names_list[idx]] for idx in range(previous_idx, last_name_idx)}
            previous_idx = last_name_idx

        return child_name_to_genome_dict_per_cluster

    def spreadChildrenAcrossJobs(self, child_name_to_genome_dict_per_cluster):
        child_name_to_set_dict_per_job_per_cluster = {}
        for cluster in child_name_to_genome_dict_per_cluster.keys():
            if len(child_name_to_genome_dict_per_cluster[cluster]) <= self.cluster_instances_dict[cluster].max_array_size:
                child_name_to_set_dict_per_job_per_cluster[cluster] = [child_name_to_genome_dict_per_cluster[cluster]]
            else:
                list_of_children_names = list(child_name_to_genome_dict_per_cluster[cluster].keys())
                # create a list of lists where each inner-list is a set of self.cluster_instances_dict[cluster].max_array_size children names - excpet the last one which could be a remainder
                children_names_split = [list_of_children_names[i:i + self.cluster_instances_dict[cluster].max_array_size] for i in range(0, len(list_of_children_names), self.cluster_instances_dict[cluster].max_array_size)]
                # This is a dictionary comprehension inside a list comprehension. The list comprehension loops through each inner-list from list_of_children_names and presents it to the dictionary comprehension. The dictionary comprehension then loops through each of the elements inside inner-list and creates a dictionary of children names to sets. This results in a list of dictionaries.
                child_name_to_set_dict_per_job_per_cluster[cluster] = [{child_name: child_name_to_genome_dict_per_cluster[cluster][child_name] for child_name in child_name_set} for child_name_set in children_names_split]

        return child_name_to_set_dict_per_job_per_cluster

    # METHODS RELATED TO SENDING JOBS TO CLUSTERS

    def createJobSubmissionInstance(self, createJobSubmissionFuncName, jobSubmission_params_dict):
        return getattr(self, createJobSubmissionFuncName)(jobSubmission_params_dict)


    # ABSTRACT METHODS
    @abstractmethod
    def postSimulationFunction(self, job_submission_info, job_manage_info):
        pass

    @abstractmethod
    def submitAndMonitorJobsOnCluster(self, dict_of_job_submission_insts):
        # The job submission instance is an object that inherits from the base_cluster_submissions.BaseJobSubmission class. This takes a dictionary of job submission instance as an argument and then uses their methods to prepare and submit the jobs. From there this function can monitor the progress of the submission and do any other related work like process data and update databases etc. What needs to be done in this function needs to be defined at a higher level so this is left as an abstract method here.
        pass

class GeneticAlgorithmBase(MGA):
    def __init__(self, dict_of_cluster_instances, MGA_name, relative2clusterBasePath_simulation_output_path, repetitions_of_a_unique_simulation, checkStopFuncName, checkStop_params_dict, getNewGenerationFuncName, newGen_params_dict, runSimulationsFuncName, runSims_params_dict, max_no_of_fit_individuals, temp_storage_path):
        MGA.__init__(self, dict_of_cluster_instances, MGA_name, relative2clusterBasePath_simulation_output_path, repetitions_of_a_unique_simulation, checkStopFuncName, checkStop_params_dict, getNewGenerationFuncName, newGen_params_dict, runSimulationsFuncName, runSims_params_dict, temp_storage_path)
        self.fittest_individuals = {}
        self.max_no_of_fit_individuals = max_no_of_fit_individuals

    def mateTheFittest(self, mateFittest_params_dict):
        # check the right mateFittest_params_dict have been passed
        set_of_neccessary_of_mateFittest_params_dict_keys = {'getFittestProbabilitiesFuncName', 'fittestProbabilities_params_dict', 'populationSize_params_dict', 'getPopulationSizeFuncName', 'mateTwoParentsFuncName', 'mateTwoParents_params_dict', 'mutateChildFuncName', 'mutateChild_params_dict'}
        if set_of_neccessary_of_mateFittest_params_dict_keys != set(mateFittest_params_dict.keys()):
            raise ValueError('mateFittest_params_dict must have certain keys. Here mateFittest_params_dict = ', mateFittest_params_dict, ' required keys are: ', set_of_neccessary_of_mateFittest_params_dict_keys)

        # get the fittest 
        fittest_individuals = self.fittest_individuals.copy()
        fittest_genomes = list(fittest_individuals.keys())
        fittest_scores = [fittest_individuals[genome][-1] for genome in fittest_genomes]
        print("fittest_genomes = ", fittest_genomes)
        print("fittest_scores = ", fittest_scores)
        # create a tuple of probabilities that correspond to the probability of picking the corresponding individual from the fittest list
        tuple_of_probabilities = getattr(self, mateFittest_params_dict['getFittestProbabilitiesFuncName'])(mateFittest_params_dict['fittestProbabilities_params_dict'])

        # create new generation
        pop_size = getattr(self, mateFittest_params_dict['getPopulationSizeFuncName'])(mateFittest_params_dict['populationSize_params_dict'])
        list_of_children = [float('NaN') for i in range(pop_size)]
        list_of_child_names = [float('NaN') for i in range(pop_size)]
        for child_idx in range(pop_size):
            parent1_genome = list(fittest_genomes[np.random.choice(len(fittest_genomes), p=tuple_of_probabilities)]) # we convert from tuple to list because creating the child involves changing elements which you can't do with a tuple. fittest_individuals are always tuples though to ensure there is not accidental changes
            parent2_genome = parent1_genome.copy()
            while parent2_genome == parent1_genome:
                parent2_genome = list(fittest_genomes[np.random.choice(len(fittest_genomes), p=tuple_of_probabilities)])

#    # convert parent ko codes to ids
#    parent1_ids = [self.gene_code_to_id_dict[code] for code in parent1_codes]
#    parent2_ids = [self.gene_code_to_id_dict[code] for code in parent2_codes]
#    # convert parent KO sets to genomes
#    parent1_genome = self.wt_genome.copy()
#    parent2_genome = self.wt_genome.copy()
#    for id in parent1_ids:
#        parent1_genome[self.id_to_genome_idx_dict[id]] = 0
#
#    for id in parent2_ids:
#        parent2_genome[self.id_to_genome_idx_dict[id]] = 0

            # mate the genomes
            tmp_child = getattr(self, mateFittest_params_dict['mateTwoParentsFuncName'])(parent1_genome.copy(), parent2_genome.copy(), mateFittest_params_dict['mateTwoParents_params_dict'])

            # mutate child
            tmp_child = getattr(self, mateFittest_params_dict['mutateChildFuncName'])(tmp_child.copy(), mateFittest_params_dict['mutateChild_params_dict'])

#    # mutate genes randomly 10% of the time
#    if random.random() < self.mutation_probability:
#
#            tmp_child = self.mutateChildFunction(tmp_child)
#
#        # convert back into idxs, ids then codes
#        tmp_child = [i for i,x in enumerate(tmp_child) if x == 0]
#        tmp_child = [self.genome_idx_to_id_dict[idx] for idx in tmp_child]
#        tmp_child.sort()
#        tmp_child = tuple([self.gene_id_to_code_dict[gene_id] for gene_id in tmp_child])
#
        # update children
        list_of_children[child_idx] = tmp_child.copy()
        # create ko set names
        list_of_child_names[child_idx] = 'child' + str(child_idx + 1)

        child_name_to_genome_dict = {list_of_child_names[idx]: list_of_children[idx] for idx in range(len(list_of_children))}

        return child_name_to_genome_dict

    ### METHODS THAT GET A NEW GENERATION

    def standardGetNewGeneration(self, newGen_params_dict):
        """
        """
        print('self.fittest_individuals = ', self.fittest_individuals)
        # create a set of keys that MUST be present in newGen_params_dict
        neccessary_keys = set(('generationZeroFuncName', 'genZero_params_dict', 'noSurvivorsFuncName', 'noSurvivors_params_dict', 'minPopulationFuncName', 'minPopulation_params_dict', 'hasNoLengthFuncName', 'noLength_params_dict', 'mate_the_fittest_dict', 'min_population_to_start_mating'))
        # check that all neccessary keys are present in the dict
        if not neccessary_keys.issubset(newGen_params_dict.keys()): # i.e. is the LHS NOT a subset of the RHS?
            raise ValueError('newGen_params_dict must contain the keys: ', neccessary_keys, ' but newGen_params_dict is: ', newGen_params_dict)

        try:
            len(self.fittest_individuals)
            has_length = True
        except:
            has_length = False

        if has_length == True:
            if self.generation_counter == 0:
                print("generation 0!")
                child_name_to_genome_dict = getattr(self, newGen_params_dict['generationZeroFuncName'])(newGen_params_dict['genZero_params_dict'])
            elif len(self.fittest_individuals) == 0:
                print("No survivors!")
                child_name_to_genome_dict = getattr(self, newGen_params_dict['noSurvivorsFuncName'])(newGen_params_dict['noSurvivors_params_dict'])
            elif len(self.fittest_individuals) < newGen_params_dict['min_population_to_start_mating']:
                print("Not enough survivors to start mating!")
                child_name_to_genome_dict = getattr(self, newGen_params_dict['minPopulationFuncName'])(newGen_params_dict['minPopulation_params_dict'])

                # assuming that all childrens names are a string that ends in an ascending (integer) number we can now figure out what the highest number is and create names with higher numbers foor the survivors of the last generation
                list_of_child_suffix_numbers = [int(re.search(r'\d+$', name).group()) for name in child_name_to_genome_dict.keys()] # this regular expression returns the group of digits at the end of the name (fine if there is only one digit)
                list_of_child_prefixs = [re.sub(r'\d+$', '',name) for name in child_name_to_genome_dict.keys()] # this regular expression takes the whole name and then deletes the digits at the end
                # check that there is only one prefix (the numbering doesn'treally make sense if not prefixed by the same thing)
                unique_prefixs = set(list_of_child_prefixs)
                if len(unique_prefixs) != 1:
                    raise ValueError('Child names must be a string that we split into two parts the prefix and the suffix (note: prefix + suffix is the whole word!)i. The prefix can be anything as long as the last character is not a number. The suffix can be any characters that represent an integer. This in pseudo-regex has the form ^\d+[^0-9]\d+$ (^\d+[^0-9] is the prefix and \d+$ is the suffix). Here child_prefix_to_suffix_dict = ', child_prefix_to_suffix_dict)

                # create a list that is ordered with the highest suffix first
                child_prefix_to_suffix_list = list(zip(list_of_child_prefixs, list_of_child_suffix_numbers))
                child_prefix_to_suffix_list.sort(key = operator.itemgetter(1), reverse = True)
                for new_ind in range(len(self.fittest_individuals)):
                    new_child_name = child_prefix_to_suffix_list[0][0] + str(int(child_prefix_to_suffix_list[0][1]) + new_ind + 1)
                    child_name_to_genome_dict[new_child_name] = list(self.fittest_individuals.keys())[new_ind]

            else:
                print("Normal mating!")
                child_name_to_genome_dict = self.mateTheFittest(newGen_params_dict['mate_the_fittest_dict'])
        elif has_length == False:
            print("No length!")
            child_name_to_genome_dict = getattr(self, newGen_params_dict['hasNoLengthFuncName'])(newGen_params_dict['noLength_params_dict'])
        else:
            raise ValueError("self.fittest_individuals must either have length or not have length here self.fittest_individuals = ", self.fittest_individuals)

        return child_name_to_genome_dict

    def updateFittestPopulation(self, submission_instance, submission_management_instance, extractAndScoreContendersFuncName, extractContender_params_dict, max_or_min):
        # validate, score and extract children
        new_individuals = getattr(submission_management_instance, extractAndScoreContendersFuncName)(submission_management_instance.simulation_data_dict.copy(), extractContender_params_dict)
        new_genomes = list(new_individuals.keys())

        #  get the odl fittest individuals
        old_individuals = self.fittest_individuals.copy()
        old_genomes = list(old_individuals.keys())
        # get a unique list of all the old and new fitetst genomes
        all_genomes = list(set(new_genomes + old_genomes))
        # combine the list of scores from the old with the new so that both dictionaries are combined and no genome is repeated
        genome_to_scores_dict = {}
        for genome in all_genomes:
            if (genome in old_individuals) and (genome in new_individuals):
                genome_to_scores_dict[genome] = [old_individuals[genome][-2] + new_individuals[genome][-2], ()]
            elif genome in old_individuals:
                genome_to_scores_dict[genome] = [old_individuals[genome][-2], ()]
            elif genome in new_individuals:
                genome_to_scores_dict[genome] = [new_individuals[genome][-2], ()]
            else:
                raise ValueError('genome is neither in old_genomes nor new_genomes,this shouldn\'t be possible!')

        # whilst the dictionary only has unique genomes as keys, the values are lists of scores we want to add the overall score so that it has the form {(genome): [tuple_of_scores, overall_score]
        all_individuals = getattr(submission_management_instance, extractContender_params_dict['overallScoreFuncName'])(genome_to_scores_dict, extractContender_params_dict)
        # convert into a sorted list of the form [((genome), [tuple_of_scores, (overall_score,)]), ((genome), [tuple_of_scores, (overall_score,)])]
        if max_or_min == 'max':
            genome_to_score_list = sorted(all_individuals.items(), key=lambda kv: kv[1][-1][0], reverse=True)
        elif max_or_min == 'min':
            genome_to_score_list = sorted(all_individuals.items(), key=lambda kv: kv[1][-1][0], reverse=False)
        else:
            raise ValueError('max_or_min must be a string of either \'min\' or \'max\'. Here max_or_min = ', max_or_min)

        # create a list of the fittest individuals
        if len(genome_to_score_list) > self.max_no_of_fit_individuals:
                fittest_individuals = {genome_to_score_list[idx][0]: genome_to_score_list[idx][1] for idx in range(self.max_no_of_fit_individuals)}
        else:
            fittest_individuals = {genome_to_score_list[idx][0]: genome_to_score_list[idx][1] for idx in range(len(genome_to_score_list))}

        self.fittest_individuals = fittest_individuals.copy()

        return

    ### METHODS THAT MATE TWO PARENTS

    def sliceMate(self, parent1_genome, parent2_genome, mateTwoParents_params_dict):
        # note the mateTwoParents_params_dict parameter doesn't do anything. This is because this mthod doesn't need it but inorder to make it compatible with other methods it needs to be passed
        # test that the parents are of the same size other wise it doesn't make sense
        if len(parent1_genome) != len(parent2_genome):
            raise ValueError('parent1_genome must have equal length to parent2_genome! len(parent1_genome) = ', len(parent1_genome), ' parent2_genome = ', parent2_genome)

        # check that parents are lists of tuple since operators are different for numpy arrays
        if not ( (type(parent1_genome) is type(parent2_genome)) and ( (type(parent1_genome) is list) or (type(parent1_genome) is tuple) ) ):
            raise TypeError('parent1_genome and parent2_genome must both have the same class and must be either lists of tuples. type(parent1_genome) = ', type(parent1_genome), ' type(parent2_genome) = ', type(parent2_genome))

        # pick a idx to split the geneomes by
        split_idx = random.randint(0,len(parent1_genome) - 1)

        child = parent1_genome[:split_idx] + parent2_genome[split_idx:]

        return child

    def mixMate(self, parent1_genome, parent2_genome, mateTwoParents_params_dict):
        # note the mateTwoParents_params_dict parameter doesn't do anything. This is because this mthod doesn't need it but inorder to make it compatible with other methods it needs to be passed
        # test that the parents are of the same size other wise it doesn't make sense
        if len(parent1_genome) != len(parent2_genome):
            raise ValueError('parent1_genome must have equal length to parent2_genome! len(parent1_genome) = ', len(parent1_genome), ' parent2_genome = ', parent2_genome)

        # check that parents are lists of tuple since operators are different for numpy arrays
        if not ( (type(parent1_genome) is type(parent2_genome)) and ( (type(parent1_genome) is list) or (type(parent1_genome) is tuple) ) ):
            raise TypeError('parent1_genome and parent2_genome must both have the same class and must be either lists of tuples. type(parent1_genome) = ', type(parent1_genome), ' type(parent2_genome) = ', type(parent2_genome))

        # pick a idx to split the geneomes by
        split_idx = random.randint(0,len(parent1_genome) - 1)

        # randomly create the gene indexs to take from parent1
        parent1_idxs_to_inherit = random.sample(range(len(parent1_genome)), split_idx)
        # create tmp child genome from randomly selected choice of genes from both parents
        child = [parent1_genome[idx] if parent1_idxs_to_inherit.count(idx) > 0 else parent2_genome[idx] for idx in range(len(parent1_genome))]

        return child

    ### METHODS THAT MUTATE CHILDREN

    def uniformMutation(self, child, mutateChild_params_dict):
        if type(child) is not list:
            raise TypeError('child must be a list! type(child) = ', type(child))

        if random.random() < mutateChild_params_dict['mutation_probability']:
            mutation_probability = mutateChild_params_dict['mutation_probability']
            number_of_mutations = mutateChild_params_dict['number_of_mutations']

            # pick indexs to flip uniformly
            gene_idxs_to_flip = random.sample(range(len(child)), number_of_mutations)
            # flip the gene
            for idx in gene_idxs_to_flip:
                child[idx] = (child[idx] + 1) % 2

        return child

    def exponentialMutation(self, child, mutateChild_params_dict):
        if type(child) is not list:
            raise TypeError('child must be a list! type(child) = ', type(child))

        # create set of neccessary keys
        neccessary_keys = set(('mutation_probability', 'exponential_parameter'))
        if not neccessary_keys.issubset(mutateChild_params_dict.keys()):
            raise ValueError('mutateChild_params_dict must contain all the following keys: ', neccessary_keys, ' mutateChild_params_dict = ', mutateChild_params_dict)

        if random.random() < mutateChild_params_dict['mutation_probability']:
            # pick the amount of gene mutations from a exponentially distributed random number with parameter self.exponential_parameter
            exponential_parameter = mutateChild_params_dict['exponential_parameter']
            # exp R.V. can produce zero, we don't want zeros
            number_of_gene_mutations = 0
            while number_of_gene_mutations == 0:
                number_of_gene_mutations = int(np.around(np.random.exponential(exponential_parameter)))

            # flip number_of_gene_mutations amount of genes randomly
            # create list of indexs to flip
            gene_idxs_to_flip = random.sample(range(len(child)), min(number_of_gene_mutations, len(child)))
            # flip genes
            for idx in gene_idxs_to_flip:
                child[idx] = (child[idx] + 1) % 2

        return child

    ### METHODS FOR CREATING PROBABILITUES OF PICKING PARENTS FROM THE FITTEST INDIVIDUALS LIST
    
    def getLinearProbsForMaximising(self, linearProbs_params_dict):
        # get the fittest 
        fittest_individuals = self.fittest_individuals.copy()
        fittest_genomes = list(fittest_individuals.keys())
        fittest_scores = [fittest_individuals[genome][-1][0] for genome in fittest_genomes]

        # check they are the same length
        if len(fittest_scores) != len(fittest_genomes):
            raise ValueError('There should be an equal amount of fittest_genomes and fittest_scores! len(fittest_genomes) = ', len(fittest_genomes), ' and len(fittest_scores) = ', len(fittest_scores))

        # randomly pick a ko such that larger KOs are more likely to be picked
        tuple_of_probabilities = tuple([fittest_scores[idx]/sum(fittest_scores) for idx in range(len(fittest_genomes))])

        return tuple_of_probabilities

