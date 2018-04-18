import unittest
import base_connection
import pathlib
import shutil
import os
import random
import subprocess

# ABSTRACT CLASSES
class LocalBaseConnectionTest(unittest.TestCase):
    """
    This unit test is the first that should be performed. It will only check things that can be checked on the local computer. Tests that require a remote computer to connect to will be done in RemoteBaseConnectionTest.
    """
    # CLASS METHODS
    @classmethod
    def setUpClass(cls):
        # define  class variables needed throughout testing
        cls.fname = 'base_connection_test_directory/test_createLocalFile/test_file.txt'
        cls.move_fname = 'test_rsync.txt'
        cls.base_dir = 'base_connection_test_directory'
        cls.move_dir1 = 'base_connection_test_directory/test_createLocalFile/test_directory1'
        cls.move_dir2 = 'base_connection_test_directory/test_createLocalFile/test_directory2'
        if os.path.isdir(cls.base_dir):
            raise ValueError('The directory base_connection_test_directory must not exist, please move some where else.')

        # create directories needed for test
        pathlib.Path(cls.move_dir1).mkdir(parents=True, exist_ok=True)
        pathlib.Path(cls.move_dir2).mkdir(parents=True, exist_ok=True)
        # create a file for transfer tests
        list_of_lines_of_file = ['This', 'is', 'a', 'test']
        with open(cls.move_dir1 + "/" + cls.move_fname, mode = 'wt', encoding = 'utf-8') as myfile:
            for line in list_of_lines_of_file:
                myfile.write(line + "\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base_dir)

    # TEST METHODS
    def test_localShellCommand(self):
        test_dir = self.base_dir + '/test_localShellCommand'
        if os.path.isdir(test_dir):
            raise ValueError('The directory ', test_dir, ' must not exist, please delete or move some where else.')
        test_cmds = ['mkdir', test_dir]
        raw_out = base_connection.Connection.localShellCommand(test_cmds)
        self.assertTrue(os.path.isdir(test_dir))
        test_cmds = ['rmdir', test_dir]
        raw_out1 = base_connection.Connection.localShellCommand(test_cmds)
        if raw_out1[0] != 0:
            raise ValueError('Test dir could not be removed! raw_out1 = ', raw_out1)


    def test_createLocalFile(self):
        # test that a file of thesame name doesn't already exist
        with pathlib.Path(self.fname) as test_file:
            if test_file.is_file():
                raise ValueError('This file should not exist - please move it: ', self.fname)

        # create file
        list_of_lines_of_file = ['This', 'is', 'a', 'test']
        base_connection.Connection.createLocalFile(self.fname, list_of_lines_of_file)
        # test file exists
        with pathlib.Path(self.fname) as test_file:
            self.assertTrue(test_file.is_file())

        # remove the file so similar tests can be done
        os.remove(self.fname)

    def test_checkLocalFileContents(self):
        # test that a file of thesame name doesn't already exist
        with pathlib.Path(self.fname) as test_file:
            if test_file.is_file():
                raise ValueError('This file should not exist - please move it: ', self.fname)

        # create file
        list_of_lines_of_file = ['This', 'is', 'a', 'test']
        base_connection.Connection.createLocalFile(self.fname, list_of_lines_of_file)
        # check the contents of the file is correct
        with open(self.fname, 'r') as test_file:
            raw_string = test_file.read().strip()

        list_of_lines = raw_string.split("\n")

        self.assertTrue(list_of_lines_of_file == list_of_lines)

        # remove the file
        os.remove(self.fname)

    def test_moveFileLocally(self):
        # leave remote stuff for a different test class
        # test that a file of thesame name doesn't already exist
        tfile = self.move_fname
        with pathlib.Path(self.move_dir2, "/", tfile) as test_file:
            if test_file.is_file():
                raise ValueError('This file should not exist - please move it: ', tfile)

        source = self.move_dir1 + "/" + tfile
        destination = self.move_dir2
        faux_self = None
        base_connection.Connection.transferFile(faux_self, source, destination, rsync_flags = "-aP", remote = False)
        with pathlib.Path(self.move_dir2 + "/" + tfile) as test_file:
            self.assertTrue(test_file.is_file())

        # remove the file so similar tests can be done
        os.remove(self.move_dir2 + "/" + tfile)

    def test_checkSuccess(self):
        # This is hard to test for because if it can't connect it goes into an infinite loop so to test for that would mean that the unit test would have to turm the network access on and off whilst testing the function in parallel - I don't have time to figure this out so wil only test the working case.
        output_dict = base_connection.Connection.checkSuccess(self.returnZeroIfFiveIsPassed, 5)
        self.assertTrue(output_dict['return_code'] == 0)

    # METHODS THAT ASSIST THE TEST METHODS
    def returnZeroIfFiveIsPassed(self, input_integer):
        output = {}
        if input_integer == 5:
            output['return_code'] = 0
            return output
        else:
            output['return_code'] = random.randint(1,13)
            return output

class RemoteBaseConnectionTest(unittest.TestCase):
    """
    This unit test is the first that should be performed. It will only check things that can be checked on the local computer. Tests that require a remote computer to connect to will be done in RemoteBaseConnectionTest.
    """
    # CLASS METHODS
    @classmethod
    def setUpClass(cls):
        # define  class variables needed throughout testing
        cls.base_dir = 'base_connection_test_directory'
        cls.move_fname = 'base_connection_test_rsync_remote_transfer_file.txt'
        cls.move_dir1 = 'base_connection_test_directory/test_createLocalFile/test_directory1'
        cls.move_dir2 = 'base_connection_test_directory/test_createLocalFile/test_directory2'
        ssh_config_alias = input('Please enter the name in your .ssh/config file that you want to connect to (i.e. the host): ')
        cls.ssh_config_alias = ssh_config_alias
        ssh_user_name = input('Please enter the user name on the remote computer: ')
        cls.ssh_user_name = ssh_user_name
        cls.faux_connection = FakeBaseConnection(cls.ssh_config_alias, cls.ssh_user_name, 'test_forename', 'test_surname', 'test_email', 'test_affiliation')

        # check that the base connection test directoy doesn't already exist
        if os.path.isdir(cls.base_dir):
            raise ValueError('The directory base_connection_test_directory must not exist, please move some where else.')

        # create directories needed for test
        pathlib.Path(cls.move_dir1).mkdir(parents=True, exist_ok=True)
        pathlib.Path(cls.move_dir2).mkdir(parents=True, exist_ok=True)
        # create a file for transfer tests
        list_of_lines_of_file = ['This', 'is', 'a', 'test']
        with open(cls.move_dir1 + "/" + cls.move_fname, mode = 'wt', encoding = 'utf-8') as myfile:
            for line in list_of_lines_of_file:
                myfile.write(line + "\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base_dir)

    # TEST METHODS

    # CONNECTION CLASS

    def test_remoteConnection(self):
        shell_cmds = ['ls', 'df -h ./']
        output_dict = base_connection.Connection.remoteConnection(self.faux_connection, shell_cmds)
        self.assertTrue(output_dict['return_code'] == 0)

    def test_sendCommand(self):
        shell_cmds = ['ls', 'df -h ./']
        raw_out = base_connection.Connection.sendCommand(self.faux_connection, shell_cmds)
        self.assertTrue(raw_out['return_code'] == 0)

    def test_remoteTransfer(self):
        # test that a file of thesame name doesn't already exist
        tfile = self.move_fname

        source = self.move_dir1 + "/" + tfile
        destination = '~'
        faux_self = self.faux_connection
        transfer_out = base_connection.Connection.transferFile(faux_self, source, destination, rsync_flags = "-aP", remote = True)
        self.assertTrue(transfer_out['return_code'] == 0)

        # remove the file so similar tests can be done
        bash_remove_file_cmd = ['rm ' + destination + '/' + tfile]
        raw_out = base_connection.Connection.sendCommand(self.faux_connection, bash_remove_file_cmd)
        if raw_out['return_code'] != 0:
            print('This is the output from deleting the file on the remote computer: ', raw_out['return_code'])
            raise ValueError('File was not deleted on the remote computer!')

    # BASE PBS CLASS

    # Cannot test checkQueue without creating an instance of the class so will have to wait for test on children
    # Cannot test createStandardSubmissionScript without creating an instance of the class so will have to wait for test on children.

    def test_createPbsSubmissionScriptTemplate(self):
        sub_template_dict = {}
        sub_template_dict['pbs_job_name'] = 'unit test'
        sub_template_dict['no_of_nodes'] = 1
        sub_template_dict['no_of_cores'] = 3
        sub_template_dict['walltime'] = '30:00:00'
        sub_template_dict['queue_name'] = 'short'
        sub_template_dict['job_number'] = 13
        sub_template_dict['outfile_name_and_path'] = '/out/path/test.out'
        sub_template_dict['errorfile_name_and_path'] = '/error/path/test.err'
        sub_template_dict['initial_message_in_code'] = 'Initial code test.'
        sub_template_dict['array_nos'] = '1-200'

        pbs_template_as_a_list = base_connection.BasePbs.createPbsSubmissionScriptTemplate(self.faux_connection, sub_template_dict['pbs_job_name'], sub_template_dict['no_of_nodes'], sub_template_dict['no_of_cores'], sub_template_dict['array_nos'], sub_template_dict['walltime'], sub_template_dict['queue_name'], sub_template_dict['job_number'], sub_template_dict['outfile_name_and_path'], sub_template_dict['errorfile_name_and_path'], sub_template_dict['initial_message_in_code'])

        string_test = [0 if type(line) is str else 1 for line in pbs_template_as_a_list]
        
        self.assertTrue((type(pbs_template_as_a_list) is list and sum(string_test) == 0))

        return

    def test_getJobIdFromSubStdOut(self):
        stdout = '  vfdnjkf vfdsbjkl 359 gydso  '
        output = base_connection.BasePbs.getJobIdFromSubStdOut(self.faux_connection, stdout)
        print('output = ', output)
        self.assertTrue(output == 359)

        return

# ADDITIONAL CLASSES
class FakeBaseConnection():
    """
    Because base connection is an abstract class it is not possible to create an instance of it to test that it works and also the format of the class then makes it hard to test the class remotely without creating an instance. My hack around this problem is to create a class that looks enough like the class that I can pass it as the 'self' variable so that all the tests work.

    Because this will test remote connections it means that you need a computer that you have SSH access to and set up an .ssh/config alias so that you can log into the other computer using only the alias and no passwords. There should be information about this at the beginning of the documentation or in about the library on PIP.
    """
    def __init__(self, ssh_config_alias, user_name, forename, surname, email, affiliation):
        self.ssh_config_alias = ssh_config_alias
        self.user_name = user_name
        self.forename_of_user = forename
        self.surname_of_user = surname
        self.user_email = email
        self.affiliation = affiliation


if __name__ == '__main__':
    unittest.main()
