from abc import ABCMeta, abstractmethod # Used to define abstract classes which is needed for the MGA class
import random # Some of the instance methods from the WholeCellModelBase class need the random library

class MGA(metaclass=ABCMeta):
    """
    This is an abstract class that all multi-generation algorithms inherit from. The idea is that the multi generation algorithm will want to repeatedly send jobs to (potentially multiple) computer clusters. With each generation the previous generation is made up of the parentjobs and the new generation is made up of the child jobs. This is so that information can be passed from generation to generation should the algorithm wish to do so.
    
    This class will assume that all connections are child classes of the base_connection.Connection class and all job submissions and job submission management classes are children of the relavent base_cluster_submissions class.
    """
    def __init__(self, dict_of_cluster_instances, MGA_name, relative2clusterBasePath_simulation_output_path, repetitions_of_a_unique_simulation, checkStopFunction, getNewGenerationFunction):
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
        self.checkStopFunction = checkStopFunction
        self.getNewGenerationFunction = getNewGenerationFunction

    # instance methods
    def run(self):
        if self.generation_counter == None:
            self.generation_counter = 0
        while self.checkStopFunction() != True:
            self.run_sim_out = self.runSimulations() 
            self.generation_counter += 1
            print('Next generation is ', self.generation_counter)

    def spreadChildrenAcrossClusters(self, child_name_to_set_dict):
        child_names_list = list(child_name_to_set_dict.keys())
        no_of_children = len(child_names_list)
        # split them across clusters
        no_of_clusters = len(self.cluster_instances_dict.keys())
        kos_per_cluster = int(no_of_children/no_of_clusters)
        # calculate the remainder
        remainder = no_of_children - (no_of_clusters * kos_per_cluster)
        child_name_to_set_dict_per_cluster = {}
        previous_idx = 0
        list_of_cluster_instance_keys = list(self.cluster_instances_dict.keys()) # we create this list because in most version of Python dictionary keys have no order so here we force a consistent order.
        for cluster_idx in range(len(self.cluster_instances_dict.keys())):
            cluster = list_of_cluster_instance_keys[cluster_idx]
            last_name_idx = (cluster_idx + 1) * kos_per_cluster
            if remainder > 0:
                last_name_idx += 1
                remainder -= 1

            child_name_to_set_dict_per_cluster[cluster] = {child_names_list[idx]: child_name_to_set_dict[child_names_list[idx]] for idx in range(previous_idx, last_name_idx)}
            previous_idx = last_name_idx

        return child_name_to_set_dict_per_cluster

    def spreadChildrenAcrossJobs(self, child_name_to_set_dict_per_cluster, max_children_per_job):
        child_name_to_set_dict_per_job_per_cluster = {}
        for cluster in child_name_to_set_dict_per_cluster.keys():
            if len(child_name_to_set_dict_per_cluster[cluster]) <= max_children_per_job:
                child_name_to_set_dict_per_job_per_cluster[cluster] = [child_name_to_set_dict_per_cluster[cluster]]
            else:
                list_of_children_names = list(child_name_to_set_dict_per_cluster[cluster].keys())
                # create a list of lists where each inner-list is a set of max_children_per_job children names - excpet the last one which could be a remainder
                children_names_split = [list_of_children_names[i:i + max_children_per_job] for i in range(0, len(list_of_children_names), max_children_per_job)]
                # This is a dictionary comprehension inside a list comprehension. The list comprehension loops through each inner-list from list_of_children_names and presents it to the dictionary comprehension. The dictionary comprehension then loops through each of the elements inside inner-list and creates a dictionary of children names to sets. This results in a list of dictionaries.
                child_name_to_set_dict_per_job_per_cluster[cluster] = [{child_name: child_name_to_set_dict_per_cluster[cluster][child_name] for child_name in child_name_set} for child_name_set in children_names_split]

        return child_name_to_set_dict_per_job_per_cluster

    def runSimulations(self):
        # get the new children
        # The child name (i.e. key) will be the name used to describe the individual child. The value must contaiin all the arguements neccessary to create a job on the cluster to simulate (or whatever else it might be) the child.
        child_name_to_set_dict = self.getNewGenerationFunction()
        
        # spread the children across clusters
        child_name_to_set_dict_per_cluster = self.spreadChildrenAcrossClusters(child_name_to_set_dict)

        # spread children-by-cluster across jobs
        child_name_to_set_dict_per_cluster = self.spreadChildrenAcrossJobs(child_name_to_set_dict_per_cluster, self.max_children_per_job)

        # submit generation to the cluster
        dict_of_job_submission_insts = {}
        dict_of_job_management_insts = {}
        list_of_cluster_instance_keys = list(self.cluster_instances_dict.keys()) 
        # create submission instances
        for cluster_connection in list_of_cluster_instance_keys:
            if type(child_name_to_set_dict_per_cluster[cluster_connection]) is not list:
                raise TypeError('child_name_to_set_dict_per_cluster[cluster_connection] must be a list! This is because there can potentially be more than one dictionary of jobs passed to one cluster and so (even if there is only one ditionary) the dictionaries must be in a list. Here type(child_name_to_set_dict_per_cluster[cluster_connection]) = ', type(child_name_to_set_dict_per_cluster[cluster_connection]))

            inner_loop_counter = 1
            for single_child_name_to_set_dict in child_name_to_set_dict_per_cluster[cluster_connection]:
                dict_of_job_submission_insts[cluster_connection + '_' + inner_loop_counter] = self.createJobSubmissionInstance(self.cluster_instances_dict[cluster_connection], single_child_name_to_set_dict)
                inner_loop_counter += 1

        # send all jobs to clusters 
        list_of_dict_of_job_management_instances = self.submitAndMonitorJobsOnCluster(dict_of_job_submission_insts)

        # convert list into the dict that the rest of the library is expecting
        dict_of_job_management_insts = {list_of_cluster_instance_keys[idx]: list_of_dict_of_job_management_instances[idx] for idx in range(len(list_of_dict_of_job_management_instances))}

        # Perform all tasks neccessary after a generation of simulations has finished
        for cluster_connection in list_of_cluster_instance_keys:
            self.postSimulationFunction(dict_of_job_submission_insts[cluster_connection], dict_of_job_management_insts[cluster_connection])

        return

    # ABSTRACT METHODS
    @abstractmethod
    def postSimulationFunction(self, dict_of_job_submission_insts[cluster_connection], dict_of_job_management_insts[cluster_connection])
        pass

    @abstractmethod
    def submitAndMonitorJobsOnCluster(self, dict_of_job_submission_insts):
        # The job submission instance is an object that inherits from the base_cluster_submissions.BaseJobSubmission class. This takes a dictionary of job submission instance as an argument and then uses their methods to prepare and submit the jobs. From there this function can monitor the progress of the submission and do any other related work like process data and update databases etc. What needs to be done in this function needs to be defined at a higher level so this is left as an abstract method here.
        pass

    @abstractmethod
    def createJobSubmissionInstance(self, cluster_connection, child_name_to_set_dict_per_cluster[cluster_connection]):
        # The job submission instance is an object that inherits from the base_cluster_submissions.BaseJobSubmission class. This is left as an abstract method so that higher level programs can choose what kind of job submissions they want to create.
        pass

class GeneticAlgorithmBase(MGA):
    def __init__(self, dict_of_cluster_instances, MGA_name, relative2clusterBasePath_simulation_output_path, repetitions_of_a_unique_simulation, checkStopFunction, getNewGenerationFunction):
        MGA.__init__(self, dict_of_cluster_instances, MGA_name, relative2clusterBasePath_simulation_output_path, repetitions_of_a_unique_simulation, jobSubmissionClass, submissionManagementClass, checkStopFunction, getNewGenerationFunction)

    ### FUNCTIONS THAT GET A NEW GENERATION

    def getNewGeneration(self):
        try:
            len(self.fittest_individuals)
            has_length = True
        except:
            has_length = False

        if has_length == True:
            if self.generation_counter == 0:
                print("generation 0!")
                ko_name_to_set_dict = self.getRandomKos()
            elif len(self.fittest_individuals) == 0:
                print("No survivors!")
                ko_name_to_set_dict = self.getRandomKos()
	    elif len(self.fittest_individuals) < self.min_population_to_start_mating:
		print("Not enough survivors to start mating!")
		# NEED TO FIGURE THIS OUT!!! change the generation size to the same as generation 0 since we haven't got to matting mode yet
		#self.generation_num_to_gen_size_dict[self.generation_counter] = self.generation_num_to_gen_size_dict[0]
		ko_name_to_set_dict = self.getRandomKos()

		list_of_ko_numbers = [int(ko_name[2:]) for ko_name in ko_name_to_set_dict.keys()]
		for new_ind in range(len(self.fittest_individuals)):
		    new_ko_name = 'ko' + str(max(list_of_ko_numbers) + new_ind + 1)
		    ko_name_to_set_dict[new_ko_name] = self.fittest_individuals[new_ind]

            else:
                print("Normal mating!")
                ko_name_to_set_dict = self.mateTheFittest()
        elif has_length == False:
            print("No length!")
            ko_name_to_set_dict = self.getRandomKos()
        else:
            raise ValueError("self.fittest_individuals must either have length or not have length here self.fittest_individuals = ", self.fittest_individuals)

        return ko_name_to_set_dict

    def updateFittestPopulation(self, submission_instance, submission_management_instance):
	# create dictionary which will be used to store all viable sims from this generation
	dict_of_this_gen_viable_sims = {}
	# extract all the simulations that divided from this generation and record them in a tmp dict
	tmp_sim_results_dict = {ko: submission_management_instance.simulation_data_dict[ko] for ko in submission_management_instance.simulation_data_dict.keys() if sum([int(submission_management_instance.simulation_data_dict[ko][rep][1]) for rep in range(len(submission_management_instance.simulation_data_dict[ko]))]) != 0}
	# add all results to dict_of_this_gen_viable_sims
	for ko in tmp_sim_results_dict.keys():
	    if ko not in dict_of_this_gen_viable_sims:
		dict_of_this_gen_viable_sims[ko] = []

	    dict_of_this_gen_viable_sims[ko].append(tmp_sim_results_dict[ko])

	#combine with the current fittest population
	all_viable_kos = list(dict_of_this_gen_viable_sims.keys())
	all_viable_kos = all_viable_kos + self.fittest_individuals.copy()
	# get unique ko sets
	all_viable_kos = list(set(all_viable_kos))
	# sort all_viable_ids in order of length so that we can pick the fittest 100
	# create dict of ko set to length
	ko_codes_to_len_dict = {ko: len(ko) for ko in all_viable_kos}
	ko_codes_to_len_list_sorted = sorted(ko_codes_to_len_dict.items(), key=operator.itemgetter(1), reverse=True)

	# create a list of the fittest individuals
	fittest_individuals = [ko_set[0] for ko_set in ko_codes_to_len_list_sorted]
	if len(fittest_individuals) > self.max_no_of_fit_individuals:
		fittest_individuals = fittest_individuals[:(self.max_no_of_fit_individuals)]

	self.fittest_individuals = fittest_individuals.copy()

	return

    ### FUNCTIONS THAT MATE TWO PARENTS

    def sliceMate(self, parent1_genome, parent2_genome):
        # pick a idx to split the geneomes by
        split_idx = random.randint(0,len(parent1_genome) - 1)

        child = parent1_genome[:split_idx] + parent2_genome[split_idx:]

        return child

    def mixMate(self, parent1_genome, parent2_genome):
        # pick a idx to split the geneomes by
        split_idx = random.randint(0,len(parent1_genome) - 1)

        # randomly create the gene indexs to take from parent1
        parent1_idxs_to_inherit = random.sample(range(len(parent1_genome)), split_idx)
        # create tmp child genome from randomly selected choice of genes from both parents
        child = [parent1_genome[idx] if parent1_idxs_to_inherit.count(idx) > 0 else parent2_genome[idx] for idx in range(len(parent1_genome))]

        return child

    ### FUNCTIONS THAT MUTATE CHILDREN

    def singleMutation(child):
       # randomly pick index from child to mutate
       idx = random.randint(0, len(child) - 1)
       # flip the gene
       child[idx] = (child[idx] + 1) % 2

       return child

    def exponentialMutation(child):
        # pick the amount of gene mutations from a exponentially distributed random number with parameter self.exponential_parameter
        exponential_parameter = self.exponential_parameter
        # exp R.V. can produce zero, we don't want zeros
        number_of_gene_mutations = 0
        while number_of_gene_mutations == 0:
            number_of_gene_mutations = int(np.around(np.random.exponential(exponential_parameter)))

        # flip number_of_gene_mutations amount of genes randomly
        # create list of indexs to flip
        gene_idxs_to_flip = random.sample(range(len(child)), number_of_gene_mutations)
        # flip genes
        for idx in gene_idxs_to_flip:
            child[idx] = (child[idx] + 1) % 2

        return child

    def mateTheFittest(self):
	# get the fittest (note this is already in order of largest KO length at the top and smallest at the bottom)
	fittest = self.fittest_individuals.copy()
	print("fittest = ", fittest)
	# randomly pick a ko such that larger KOs are more likely to be picked
	ko_length_of_fittest = [len(ko) for ko in fittest]
	list_of_probabilities = [ko_length_of_fittest[idx]/sum(ko_length_of_fittest) for idx in range(len(ko_length_of_fittest))]
	# create new generation
	pop_size = self.getPopulationSizeFunction()
	list_of_children = [float('NaN') for i in range(pop_size)]
	ko_set_names = [float('NaN') for i in range(pop_size)]
	for child_idx in range(pop_size):
	    parent1_codes = np.random.choice(fittest, p=list_of_probabilities)
	    parent2_codes = parent1_codes
	    while parent2_codes == parent1_codes:
		parent2_codes = np.random.choice(fittest, p=list_of_probabilities)

	# convert parent ko codes to ids
	parent1_ids = [self.gene_code_to_id_dict[code] for code in parent1_codes]
	parent2_ids = [self.gene_code_to_id_dict[code] for code in parent2_codes]
	# convert parent KO sets to genomes
	parent1_genome = self.wt_genome.copy()
	parent2_genome = self.wt_genome.copy()
	for id in parent1_ids:
	    parent1_genome[self.id_to_genome_idx_dict[id]] = 0

	for id in parent2_ids:
	    parent2_genome[self.id_to_genome_idx_dict[id]] = 0

	# mate the genomes
	# create empty child genome
	tmp_child = []
	# make sure the child has at least 2 KOs
	while tmp_child.count(0) < 2:
            tmp_child = self.createChildFunction(parent1_genome, parent2_genome)

	# mutate genes randomly 10% of the time
	if random.random() < self.mutation_probability:

            tmp_child = self.mutateChildFunction(tmp_child)

	    # convert back into idxs, ids then codes
	    tmp_child = [i for i,x in enumerate(tmp_child) if x == 0]
	    tmp_child = [self.genome_idx_to_id_dict[idx] for idx in tmp_child]
	    tmp_child.sort()
	    tmp_child = tuple([self.gene_id_to_code_dict[gene_id] for gene_id in tmp_child])

	    # update children
	    list_of_children[child_idx] = tmp_child
	    # create ko set names
	    ko_set_names[child_idx] = 'ko' + str(child_idx + 1)

	ko_name_to_set_dict = {ko_set_names[idx]: list_of_children[idx] for idx in range(len(list_of_children))}

	return ko_name_to_set_dict
