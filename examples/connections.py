from computer_communication_framework.base_connection import Connection
import subprocess
import re
import datetime
class BasePbs(Connection):
    """
    This is meant to be a template to create a connection object for a standard PBS/TORQUE cluster. This inherits from the base_connect.Connection class in base_connection.py. It will not define ALL of the abstract classes specified in base_connection.Connection and so you will not be able to create an instance of it. One should create a class that inherits this class and add all the neccessary methods to statisfy the base_connection.Connection abstract methods.

    This is meant to contain the BASIC commands that can be used by programs to control the remote computer (that aren't already included in base_connection.Connection). This is atomistic level commands that form the basis of more complex and specific programs.

    Abstract methods that are left out are:
         - checkDiskUsage
    """

    def __init__(self, cluster_user_name, ssh_config_alias, path_to_key, forename_of_user, surname_of_user, user_email, base_output_path = '/base/output/path', base_runfiles_path = '/base/run/file/path', master_dir = '/master/dir', info_about_cluster = 'Example Cluster Name (ECN): Advanced Computing Research Centre, somewhere.', activate_virtual_environment_list = ['module add python-anaconda-4.2-3.5', 'source activate virtual_environment_name']):
        Connection.__init__(self, cluster_user_name, ssh_config_alias, path_to_key, forename_of_user, surname_of_user, user_email)
        self.submit_command = 'qsub'
        self.information_about_cluster = info_about_cluster
        self.base_output_path = base_output_path
        self.base_runfiles_path = base_runfiles_path
        self.master_dir = master_dir
        self.activate_venv_list = activate_virtual_environment_list

    # INSTANCE METHODS
    def checkQueue(self, job_number):
        """
        This function must exist to satisfy the abstract class that it inherits from. In this case it takes a job number and returns a list of all the array numbers of that job still running.
        
        Args:
            job_number (int): PBS assigns a unique integer number to each job. Remeber that a job can actually be an array of jobs.

        Returns:
            output_dict (dict): Has keys 'return_code', 'stdout', and 'stderr'.
        """

                # -t flag shows all array jobs related to one job number, if that job is an array.
        grep_part_of_cmd = "qstat -tu " + self.user_name + " | grep \'" + str(job_number) + "\' | awk \'{print $1}\' | awk -F \"[][]\" \'{print $2}\'"

        output_dict = self.checkSuccess(self.sendCommand([grep_part_of_cmd])) # Remember that all commands should be passed through the "checkSuccess" function that is inherited from the Connection class.

        return output_dict

# STUFF FOR THE BCS CHILD CLASS!!!
#            no_of_unique_jobs (int): Total amount of jobs to run.
#            no_of_repetitions_of_each_job (int): Total amount of repetitions of each job.
#            master_dir (str): The directory on the remote computer that you want the submission script to start in.

    def createPbsSubmissionScriptTemplate(self, pbs_job_name, no_of_nodes, no_of_cores, walltime, queue_name, job_number, outfile_name_and_path, errorfile_name_and_path, initial_message_in_code = None, shebang = "#!/bin/bash"):
        """
        This creates a template for a submission script for the cluster however it does not contain any code for specific jobs (basically just the PBS commands and other bits that might be useful for debugging). It puts it all into a list where list[0] will be line number one of the file and list[2] will be line number two of the file etc and returns that list.

        Args:
            pbs_job_name (str): The name given to the queuing system.
            no_of_nodes (int): The number of nodes that the user would like to request.
            no_of_cores (int): The number of cores that the user would like to request.
            walltime (str): The maximum amount of time the job is allowed to take. Has the form 'HH:MM:SS'.
            queue_name (str): PBS/Torque clusters have a choice of queues and this variable specifies which one to use.
            outfile_name_and_path (str): Absolute path and file name of where you want the outfiles of each job array stored.
            errorfile_name_and_path (str): Absolute path and file name of where you want to store the errorfiles of each job array stored.
            initial_message_in_code (str): The first comment in the code normally says a little something about where this script came from. NOTE: You do not need to include a '#' to indicat it is a comment.
            initial_message_in_code == None (str): Should the user wish to put a meaasge near the top of the script (maybe explanation or something) then they can add it here as a string. If it's value is None (the default value) then the line is omitted.

        Returns:
            list_of_pbs_commands (list of strings): Each string represents the line of a submission file and the list as a whole is the beginning of a PBS submission script.
        """

        # add the first part of the template to the list
        list_of_pbs_commands = [shebang + "\n", "\n", "# This script was created using Oliver Chalkley's computer_communication_framework library - https://github.com/Oliver-Chalkley/computer_communication_framework." + "\n", "# "]
        
        
        # Only want to put the users initial message if she has one
        if initial_message_in_code is not None:
            list_of_pbs_commands += [initial_message_in_code + "\n"]

        # add the next part of the template
        list_of_pbs_commands = ["# Title: " + pbs_job_name + "\n", "# User: " + self.forename_of_user + ", " + self.surename_of_user + ", " + self.user_email + "\n"]

        # Only want to put affiliation if there is one
        if type(self.affiliation) is not None: 
            list_of_pbs_commands += ["# Affiliation: " + self.affiliation + "\n"]
            
        # add the next part of the template to the list
        list_of_pbs_commands += ["# Last Updated: " + str(datetime.datetime.now()) + "\n", "\n", "## Job name" + "\n", "#PBS -N " + pbs_job_name + "\n", "\n", "## Resource request" + "\n", "#PBS -l nodes=" + str(no_of_nodes) + ":ppn=" + str(no_of_cores) + ",walltime=" + walltime + "\n", "#PBS -q " + queue_name + "\n", "\n", "## Job array request" + "\n", "#PBS -t " + job_array_numbers + "\n", "\n", "## designate output and error files" + "\n", "#PBS -e " + outfile_name_and_path + "\n", "#PBS -o " + errorfile_name_and_path + "\n", "\n", "# print some details about the job" + "\n", 'echo "The Array ID is: ${PBS_ARRAYID}"' + "\n", 'echo Running on host `hostname`' + "\n", 'echo Time is `date`' + "\n", 'echo Directory is `pwd`' + "\n", 'echo PBS job ID is ${PBS_JOBID}' + "\n", 'echo This job runs on the following nodes:' + "\n", 'echo `cat $PBS_NODEFILE | uniq`' + "\n", "\n"]

        return list_of_pbs_commands

    def createStandardSubmissionScript(self, file_name_and_path, list_of_job_specific_code, pbs_job_name, no_of_nodes, no_of_cores, queue_name, outfile_name_and_path, errorfile_name_and_path, walltime, initial_message_in_code = None, file_permissions = "700", shebang = "#!/bin/bash"):
        """
        This creates a PBS submission script based on the resources you request and the job specific code that you supply. It then writes this code to a file that you specify.

        Args:
            file_name_and_path (str): Absolute path plus filename that you wish to save the PBS submission script to e.g. /path/to/file/pbs_submission_script.sh.
            list_of_job_specific_code (list of strings): Each element of the list contains a string of one line of code. Note: This code is appended to the end of the submission script.
            pbs_job_name (str): The name given to this job.
            no_of_nodes (int): The number of nodes that the user would like to request.
            no_of_cores (int): The number of cores that the user would like to request.
            queue_name (str): PBS/Torque clusters have a choice of queues and this variable specifies which one to use.
            outfile_name_and_path (str): Absolute path and file name of where you want the outfiles of each job array stored.
            errorfile_name_and_path (str): Absolute path and file name of where you want to store the errorfiles of each job array stored.
            walltime (str): The maximum amount of time the job is allowed to take. Has the form 'HH:MM:SS'.
            initial_message_in_code == None (str): Should the user wish to put a meaasge near the top of the script (maybe explanation or something) then they can add it here as a string. If it's value is None (the default value) then the line is omitted.
            file_permissions = "700" (str): The file permissions that the user would like the PBS submission script to have. If it is None then it will not attempt to change the settings. The default setting, 700, makes it read, write and executable only to the user. NOTE: For the submission script to work one needs to make it executable.
            shebang = "#!/bin/bash" (str): The shebang line tells the operating system what interpreter to use when executing this script. The default interpreter is BASH which is normally found in /bin/bash.
        """

        # Create the PBS template
        pbs_script_list = self.createPbsSubmissionScriptCommands(initial_message_in_code, pbs_job_name, no_of_nodes, no_of_cores, walltime, queue_name, job_number, outfile_name_and_path, errorfile_name_and_path, shebang = "#!/bin/bash")
        # Add the code that is specific to this job
        pbs_script_list += list_of_job_specific_code
        
        # write the code to a file
        Connection.createLocalFile(file_name_and_path, pbs_script_list, file_permisions = "700")

        # change the permissions if neccessary
        if file_permissions != None:
            subprocess.check_call(["chmod", str(file_permissions), str(output_filename)])

        return

# DELETE THIS ONCE EVERYTHING HAS BEEN DONE

#    def createStandardSubmissionScript(self, output_filename, pbs_job_name, queue_name, no_of_unique_jobs, no_of_repetitions_of_each_job, master_dir, outfile_name_and_path, errorfile_name_and_path, walltime, initial_message_in_code, list_of_job_specific_code):
#        """
#        This acts as a template for a submission script for the cluster however it does not contain any code for specific jobs. This code is pass to the function through the list_of_job_specific_code variable.
#
#        The format for a submission in this case will be an array of jobs. Here we want to be able to specify a number of unique jobs and then the amount of times we wish to repeat each unique job. This will then split all the jobs across arrays and CPUs on the cluster depending on how many are given. Each unique job has a name and some settings, this is stored on the cluster in 2 files job_names_file and job_settings_file, respectively.
#
#        Args:
#            output_filename (str): The name of the submission script.
#            pbs_job_name (str): The name given to the queuing system.
#            queue_name (str): This cluster has a choice of queues and this variable specifies which one to use.
#            no_of_unique_jobs (int): Total amount of jobs to run.
#            no_of_repetitions_of_each_job (int): Total amount of repetitions of each job.
#            master_dir (str): The directory on the remote computer that you want the submission script to start in.
#            outfile_name_and_path (str): Absolute path and file name of where you want the outfiles of each job array stored.
#            errorfile_name_and_path (str): Absolute path and file name of where you want to store the errorfiles of each job array stored.
#            walltime (str): The maximum amount of time the job is allowed to take. Has the form 'HH:MM:SS'.
#            initial_message_in_code (str): The first comment in the code normally says a little something about where this script came from. NOTE: You do not need to include a '#' to indicat it is a comment.
#            list_of_job_specific_code (list of strings): Each element of the list contains a string of one line of code.
#
#        Returns:
#            output_dict (dict): Contains details of how it spread the jobs across arrays and CPUs. Has keys, 'no_of_arrays', 'no_of_unique_jobs_per_array_job', 'no_of_repetitions_of_each_job', 'no_of_sims_per_array_job', and 'list_of_rep_dir_names'.
#        """
#
#        # set job array numbers to None so that we can check stuff has worked later
#        job_array_numbers = None
#        # The maximum job array size on the cluster.
#        max_job_array_size = 500
#        # initialise output dict
#        output_dict = {}
#        # test that a reasonable amount of jobs has been submitted (This is not a hard and fast rule but there has to be a max and my intuition suggestss that it will start to get complicated around this level i.e. queueing and harddisk space etc)
#        total_sims = no_of_unique_jobs * no_of_repetitions_of_each_job
#        if total_sims > 20000:
#            raise ValueError('Total amount of simulations for one batch submission must be less than 20,000, here total_sims=',total_sims)
#
#        output_dict['total_sims'] = total_sims
#        # spread simulations across array jobs
#        if no_of_unique_jobs <= max_job_array_size:
#            no_of_unique_jobs_per_array_job = 1
#            no_of_arrays = no_of_unique_jobs
#            job_array_numbers = '1-' + str(no_of_unique_jobs)
#        else:
#            # job_array_size * no_of_unique_jobs_per_array_job = no_of_unique_jobs so all the factors of no_of_unique_jobs is
#            common_factors = [x for x in range(1, no_of_unique_jobs+1) if no_of_unique_jobs % x == 0]
#            # make the job_array_size as large as possible such that it is less than max_job_array_size
#            factor_idx = len(common_factors) - 1
#            while factor_idx >= 0:
#                if common_factors[factor_idx] < max_job_array_size:
#                    job_array_numbers = '1-' + str(common_factors[factor_idx])
#                    no_of_arrays = common_factors[factor_idx]
#                    no_of_unique_jobs_per_array_job = common_factors[(len(common_factors)-1) - factor_idx]
#                    factor_idx = -1
#                else:
#                    factor_idx -= 1
#
#            # raise error if no suitable factors found!
#            if job_array_numbers is None:
#                raise ValueError('job_array_numbers should have been assigned by now! This suggests that it wasn\'t possible for my algorithm to split the KOs across the job array properly. Here no_of_unique_jobs=', no_of_unique_jobs, ' and the common factors of this number are:', common_factors)
#
#        output_dict['no_of_arrays'] = no_of_arrays
#        output_dict['no_of_unique_jobs_per_array_job'] = no_of_unique_jobs_per_array_job
#        output_dict['no_of_repetitions_of_each_job'] = no_of_repetitions_of_each_job
#        # calculate the amount of cores per array job - NOTE: for simplification we only use cores and not nodes (this is generally the fastest way to get through the queue anyway)
#        no_of_cores = no_of_repetitions_of_each_job * no_of_unique_jobs_per_array_job
#        output_dict['no_of_sims_per_array_job'] = no_of_cores
#        output_dict['list_of_rep_dir_names'] = list(range(1, no_of_repetitions_of_each_job + 1))
#        no_of_nodes = 1
#        # write the script to file
#        with open(output_filename, mode='wt', encoding='utf-8') as myfile:
#            myfile.write("#!/bin/bash" + "\n")
#            myfile.write("\n")
#            myfile.write("# This script was created using Oliver Chalkley's computer_communication_framework library - https://github.com/OliCUoB/computer_communication_framework." + "\n")
#            myfile.write("# " + initial_message_in_code + "\n")
#            myfile.write("# Title: " + pbs_job_name + "\n")
#            myfile.write("# User: " + self.forename_of_user + ", " + self.surename_of_user + ", " + self.user_email + "\n")
#            if type(self.affiliation) is not None:
#                myfile.write("# Affiliation: " + self.affiliation + "\n")
#            myfile.write("# Last Updated: " + str(datetime.datetime.now()) + "\n")
#            myfile.write("\n")
#            myfile.write("## Job name" + "\n")
#            myfile.write("#PBS -N " + pbs_job_name + "\n")
#            myfile.write("\n")
#            myfile.write("## Resource request" + "\n")
#            myfile.write("#PBS -l nodes=" + str(no_of_nodes) + ":ppn=" + str(no_of_cores) + ",walltime=" + walltime + "\n")
#            myfile.write("#PBS -q " + queue_name + "\n")
#            myfile.write("\n")
#            myfile.write("## Job array request" + "\n")
#            myfile.write("#PBS -t " + job_array_numbers + "\n")
#            myfile.write("\n")
#            myfile.write("## designate output and error files" + "\n")
#            myfile.write("#PBS -e " + outfile_name_and_path + "\n")
#            myfile.write("#PBS -o " + errorfile_name_and_path + "\n")
#            myfile.write("\n")
#            myfile.write("# print some details about the job" + "\n")
#            myfile.write('echo "The Array ID is: ${PBS_ARRAYID}"' + "\n")
#            myfile.write('echo Running on host `hostname`' + "\n")
#            myfile.write('echo Time is `date`' + "\n")
#            myfile.write('echo Directory is `pwd`' + "\n")
#            myfile.write('echo PBS job ID is ${PBS_JOBID}' + "\n")
#            myfile.write('echo This job runs on the following nodes:' + "\n")
#            myfile.write('echo `cat $PBS_NODEFILE | uniq`' + "\n")
#            myfile.write("\n")
#            for line in list_of_job_specific_code:
#                myfile.write(line)
#
#        # give the file execute permissions
#        subprocess.check_call(["chmod", "700", str(output_filename)])
#
#        return output_dict

    def getJobIdFromSubStdOut(self, stdout):
        """
        When one submits a job to the cluster it returns the job ID to the stdout. This function takes that stdout and extracts the job ID so that it can be used to monitor the job if neccessary.

        Args:
            stdout (str): The stdout after submitting a job to the queue.

        Returns:
            return (int): The job ID of the job submitted which returned stdout.
        """
        
        return int(re.search(r'\d+', stdout).group())

