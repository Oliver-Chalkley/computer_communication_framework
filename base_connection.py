from abc import ABCMeta, abstractmethod
import subprocess
import time
import re
import datetime
class Connection(metaclass=ABCMeta):
    """
    This is an abstract class that all connection classes inherit from. The purpose of this class is to act as a template with which to communicate with other computers in a rigid manner so that other programs can be built on top of it, without knowing what computers it might connect to iin the future.
    
    REMEMBER that all connections to remote computers should go through the 'checkSuccess' function so that connection errors can be dealt with robustly.

    The general idea is that when communicating between computers it is often useful to be able to control them, send files to them and check how much storage space you need. If connecting to computing clusters you may also wish to be able to check the job queue.

    MOST IMPORTANTLY whenever you make any kind of connection to the remote computer you want to make sure that the remote computer got the messge and if it didn't then you need to be able to keep retrying without overloading the remote computer with connection requests (i.e. DDoS attack).
    """
    
    def __init__(self, remote_user_name, ssh_config_alias, path_to_key, forename_of_user, surname_of_user, user_email, affiliation = None):
        """
        In order to initiate this class the user must have their ssh config file set up to have their cluster connection as an alias. It is best to set this up on a secure ccomputer that you trusst and have an encryption key without a password. Details about setting up the SSH config file can be found at my website.
        
        To better explain things I will describe a toy example that all doc strings in this class will refer to. The user has set up an easy connecttion to the remote computer by setting up their ~/.ssh/config file (either directly or through a tunnel) like:

        Host ssh_alias
            User user_name
            HostName address_to_remote_computer
            IdentityFile /home/local_user_name/.ssh/path_to_key/key_name

        Args:
            remote_user_name (str): The username used on the remote computer, (i.e. user_name).
            ssh_config_alias (str): The name given to the SSH connection (i.e. ssh_config_alias).
            path_to_key (str): The path, and name, to the encryption key (i.e. /home/local_user_name/.ssh/path_to_key/key_name).
            forename_of_user (str): Your first name.
            surname_of_user (str): Your surname.
            user_email (str): Your email address.
        """

        self.user_name = remote_user_name
        self.ssh_config_alias = ssh_config_alias
        self.path_to_key = path_to_key
        self.forename_of_user = forename_of_user
        self.surename_of_user = surname_of_user
        self.user_email = user_email
        self.affiliation = affiliation

    # ABSTRACT METHODS
    @abstractmethod
    def checkQueue(self):
        # Often a program needs to monitor the job queue of a cluster, queuing systems vary so this is left as an abstract method.
        pass

    @abstractmethod
    def checkDiskUsage(self):
        # To avoid running out of disk space on the remote computer one can call this function to find out how much is used and how much is available. Whilst this is fairly standard across *NIX home computers clusters and any kind of computer with multi-user storage often has custom functions for this and so is left as an abstract function.
        pass

    # STATIC METHODS
    @staticmethod
    def createLocalFile(file_name_and_path, list_of_lines_of_file, file_permisions = None, file_open_mode = 'wt', file_encoding = 'utf-8'):
        """
        Creates a file on the local computer.

        Args:
            file_name_and_path (str): The absolute file path and desired name of the file i.e. "/path/to/file/file.txt".
            list_of_lines_of_file (list of strings): The contents of the file should be put into a list where element zero is the first line of the file, element 1 is the second line of the file etc.
            file_permisions = None (str): If you wish to set specific permissions on the file you enter them as a string here e.g. "700" or "u+x". The default is None which will not change the permissions of the file,
            file_open_mode = 'wt': This is an option to change the mode that the file is opened. The default is to "write text" ('wt').
            file_encoding = 'utf-8': This is an option to change the encoding of the file. The default is 'utf-8'.

        Raises:
            OSError if the file can't be opened.
            subprocess.SubprocessError if subprocess.check_call cannot change the permissions of the file.
        """
        with open(file_name_and_path, mode = file_open_mode, encoding = file_encoding) as myfile:
            for line in list_of_lines_of_file:
                myfile.write(line + "\n")

        # set file permissions if specified
        if file_permisions != None:
            subprocess.check_call(["chmod", str(file_permisions), str(file_name_and_path)])

        return

    # INSTANCE METHODS
    def transferFile(self, source, destination, rsync_flags = "-aP", remote = True):
        """
        Uses rsync with specified flags (unspecified uses "-aP") to send a file to the remote computer. Source and destination only need the actual paths as the SSH connection will be done automatically.

        IMPORTANT: If you are unfamiliar with rsync then please read the manual or an introductory guide before using this function. Please remeber that a directory ending with no forward-slash indicates to copy the the directory and a directory ending with a forward-slash indicates to copy just the contents of the directory.

        Args:
            source (str): path and filename of the file to transfer.
            destination (str): path to the destination directory.
            rsync_flags (str): any flags that you would like when copying. This defaults to -aP (a is archive mode i.e. -rlptgoD (see manual for more information) and P is --progress which produces a progress bar.
            remote = True (bool): This says indicates whether you want to do a local or remote file transfer. Default is set to remote so will look in the class variables for the connection details.

        Returns:
            output_dict (dict): returns the 'return_code' from subprocess.call(rsync_cmd, shell=True).
        """
        if remote:
            rsync_cmd = "rsync " + rsync_flags + " " + source + " " + self.ssh_config_alias + ":" + destination
            output = subprocess.call(rsync_cmd, shell=True)
            output_dict = {}
            output_dict['return_code'] = output
        else:
            rsync_cmd = "rsync " + rsync_flags + " " + source + " " + destination
            output = subprocess.call(rsync_cmd, shell=True)
            output_dict = {}
            output_dict['return_code'] = output

        return output_dict

    def remoteConnection(self, list_of_remote_commands):
        """
        This sends a list of commands to a remote computer. It is hard to use the localShellCommand to send remote commands, there are warnings about using the sendCommand function due to malicious injection but subprocess.Popen seems to not suffer from these problems (I don't see how this is any more proteted from malicious inject than sendCommand but there doesn't seem to be warnings). As a result of the above this should be the prefered method to send commands to the remote computer.

        Args:
            list_of_remote_commands (list of strings): Each string is a whole command that you wish to be sent to the remote computer e.g. ['ls -l', 'df -h ./'].

        Returns:
            output_dict (dict): Is a dictionary which contains lists of the stdout, stdin and stderr.
        """

        ssh = subprocess.Popen(["ssh",
                                self.ssh_config_alias],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                bufsize=0)
         
        # send ssh commands to stdin
        input_cmd = "\n".join(list_of_remote_commands) + "\n"
        output, error = ssh.communicate(input_cmd)
         
        output_dict = {'return_code': ssh.returncode, 'stdin': input_cmd, 'stdout': output, 'stderr': error}

        return output_dict

    def sendCommand(self, list_of_shell_commands):
        """
        'sendCommand', 'remoteConnection' and 'localShellCommand' are the two commands to communicate with a remote computer. This is easier for more complex commands. Note that the SSH connection is created automatically using the class variables and so does not need to be in the list_of_shell_commands.

        BEWARE: 'list_of_shell_commands' could be used as a vector for malicious injection and so in certain projects (specifically when untrusted users have direct access to this) could pose significant security risks.

        Args:
            list_of_shell_commands (list of strings): Each string in the list should be one whole command that will run in the shell language that runs on the remote computer. This list should NOT contain the SSH connection command. For example ['mkdir -p new_dir', 'cd new_dir'] will create the new_dir directory on the remote machine and the move into it.

        Returns:
            output_dict (dict): Has keys 'return_code', 'stdout', and 'stderr'.
        """

        # the -T flag in ssh is there because if you don't it opens a new instance of ssh everytime this function is run. It doesn't take long until your computer reaches it's maximum processes and then suddenly nothing can do anything because all the possible processes are being taken up by ssh instances not doing anything.
        sshProcess = subprocess.Popen(['ssh', '-T', self.ssh_config_alias], stdin=subprocess.PIPE, stdout = subprocess.PIPE, universal_newlines=True, bufsize=0)
        command = '\n'.join(list_of_shell_commands)
        print("command = ", command)
        out, err = sshProcess.communicate(command)
        return_code =  sshProcess.returncode
        sshProcess.stdin.close()
        output_dict = {}
        output_dict['return_code'] = return_code
        output_dict['stdout'] = out
        output_dict['stderr'] = err

        return output_dict

    # STATIC METHODS - I made these all static methods because I thought it might be handy to be able to use them without creating an instance.
    @staticmethod
    def checkSuccess(function, *args):
        """
        This function takes a function that requires a remote connection and makes sure that the actual command completes. If the connection can't be made then it it keeps trying whilst avoiding fast repeated connection attempts. After a connection can't be made for a whole day it trys once every 12 hours.
        
        Args:
            function (function): A function that makes a connection to a remote computer. This function MUST return a dictionary with atleast one element. This element have the key 'return_code' which returns the return code from the connection to the remote computer.
            *args (any combination of arguements): These will be the arguements needed to pass to function.
        Returns:
            output (unknown): Whatever function returns is saved as output and is returned.
            """

        # a list of the wait times (in seconds) between each loop should the connection keep failing
        # accumulative time:     15s 30s 45s  1m   6m  16m  30m   1hr   2hr   4hr    8hr   16hr   1day   2day   3day   4day   5day  6 day  7day
        wait_times = (3, 3, 3, 3, 3, 15, 15, 15, 300, 600, 840, 1800, 3600, 7200, 14400, 28800, 28800) #, 86400, 86400, 86400, 86400, 86400, 86400)

        # set flag to no successful connection attempt (successful exit code = 0)
        connection_success = 13
        for wait in wait_times:
            if connection_success != 0:
                try:
                    output = function(*args)
                    connection_success = output['return_code']
                except:
                    connection_success = 13

            else:
                break

            if connection_success !=0:
                print('Connection failed. Waiting ' + str(wait) + ' seconds before attempting to reconnect.')
                time.sleep(wait)

        # depending on the result either output the data or stop the simulation
        while connection_success != 0:
            try:
                output = function(*args)
                connection_success = output['return_code']
            except:
                connection_success = 13

            if connection_success !=0:
                print('Connection failed. Waiting ' + str(43200) + ' seconds before attempting to reconnect.')
                time.sleep(43200)

        return output

    @staticmethod
    def localShellCommand(commands_as_a_list):
        """
        This takes a list of commands (in the subprocess module style shell=False) and sends them via subprocess.check_output(commands_as_a_list). Note that if the commands_as_a_list does not start with an SSH command then the commands will be performed in a local shell.

        The shell=False is Python's prefered method to avoid malicious code injections.

        Args:
            commands_as_a_list (list of strings): Each contains a command, flag or option. For example ['mkdir', '-p', 'new_dir'] will create a new directory called new_dir on the local computer.
        Returns:
            raw_output (binary string): Returns the stdout as a binary string.
        """
        # if the return code is zero then subprocess returns the output of the command or otherwise raises an exception. We want to keep trying if there is an exception and so use the following code.
        try:
            raw_output = [0, subprocess.check_output(commands_as_a_list)]
        except Exception:
            raw_output = [1, None]
        return raw_output

class BasePbs(Connection):
    """
    This is meant to be a template to create a connection object for a standard PBS/TORQUE cluster. This inherits from the base_connect.Connection class in base_connection.py. It will not define ALL of the abstract classes specified in base_connection.Connection and so you will not be able to create an instance of it. One should create a class that inherits this class and add all the neccessary methods to statisfy the base_connection.Connection abstract methods.

    This is meant to contain the BASIC commands that can be used by programs to control the remote computer (that aren't already included in base_connection.Connection). This is atomistic level commands that form the basis of more complex and specific programs.

    Abstract methods that are left out are:
         - checkDiskUsage
    """

    def __init__(self, remote_user_name, ssh_config_alias, path_to_key, forename_of_user, surname_of_user, user_email, base_output_path, base_runfiles_path, remote_computer_info):
        """
        This is called when the BasePbs class is initialised (remember that this can't be initialised directly because it inherits from base_connection.Connection but is missing some of the abstract classes described in base_connection.Connection).

        In order to initiate this class the user must have their ssh config file set up to have their cluster connection as an alias. It is best to set this up on a secure ccomputer that you trusst and have an encryption key without a password. Details about setting up the SSH config file can be found at my website.
        
        To better explain things I will describe a toy example that all doc strings in this class will refer to. The user has set up an easy connecttion to the remote computer by setting up their ~/.ssh/config file (either directly or through a tunnel) like:

        Host ssh_alias
            User user_name
            HostName address_to_remote_computer
            IdentityFile /home/local_user_name/.ssh/path_to_key/key_name

        Args:
            remote_user_name (str): The username used on the remote computer, (i.e. user_name).
            ssh_config_alias (str): The name given to the SSH connection (i.e. ssh_config_alias).
            path_to_key (str): The path, and name, to the encryption key (i.e. /home/local_user_name/.ssh/path_to_key/key_name).
            forename_of_user (str): Your first name.
            surname_of_user (str): Your surname.
            user_email (str): Your email address.
            base_output_path (str): Absolute path to where you want things saved on the remote computer.
            base_runfiles_path (str): Absolute path to where you want code files saved (i.e. submission scripts and Python files excecuted remotely etc)
            remote_computer_info (str): This is information about the remote computer that can be used for identification and for giving credit on scripts etc. For example if it was a cluster then it might be something like: Example Cluster Name (ECN): Advanced Computing Research Centre, Somewhere.
            
        """
        
        Connection.__init__(self, remote_user_name, ssh_config_alias, path_to_key, forename_of_user, surname_of_user, user_email)
        self.submit_command = 'qsub'
        self.remote_computer_info = remote_computer_info
        self.base_output_path = base_output_path
        self.base_runfiles_path = base_runfiles_path

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
        grep_part_of_cmd = "qstat -tu " + self.user_name + " | grep " + str(job_number) + " | awk \'{print $1}\' | awk -F \"[][]\" \'{print $2}\'"

        output_dict = self.checkSuccess(self.sendCommand([grep_part_of_cmd])) # Remember that all commands should be passed through the "checkSuccess" function that is inherited from the Connection class.

        return output_dict

# STUFF FOR THE BC3 CHILD CLASS!!!
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

