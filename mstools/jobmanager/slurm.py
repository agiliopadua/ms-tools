import math
import subprocess
from collections import OrderedDict
from subprocess import Popen

from .pbsjob import PbsJob
from .jobmanager import JobManager
from ..errors import JobManagerError


class Slurm(JobManager):
    def __init__(self, queue_dict: OrderedDict, **kwargs):
        # Current only support one queue
        super().__init__(queue=list(queue_dict.keys())[0], nprocs=list(queue_dict.values())[0], **kwargs)
        self.sh = '_job_slurm.sh'

    def replace_mpirun_srun(self, commands) -> (int, [str]):
        n_process = 1
        cmds_replaced = []
        for cmd in commands:
            if cmd.startswith('mpirun'):
                n_process = int(cmd.split()[2])
                cmd_srun = 'srun ' + ' '.join(cmd.split()[3:])
                cmds_replaced.append(cmd_srun)
            else:
                cmds_replaced.append(cmd)
        return n_process, cmds_replaced

    def generate_sh(self, workdir, commands, name, sh=None, n_thread=None, exclusive=False, **kwargs):
        if sh is None:
            sh = self.sh
        out = sh[:-2] + 'out'
        err = sh[:-2] + 'err'

        n_process, srun_commands = self.replace_mpirun_srun(commands)
        if n_thread is None:
            n_thread = self.nprocs // n_process

        if exclusive:
            n_node = math.ceil(n_process * n_thread / self.nprocs)
            node_cmd = '#SBATCH --nodes=%i\n' % n_node
            exclusive_cmd = '#SBATCH --exclusive\n'
        else:
            node_cmd = ''
            exclusive_cmd = ''

        with open(sh, 'w') as f:
            f.write('#!/bin/bash\n'
                    '#SBATCH -D %(workdir)s\n'
                    '#SBATCH -J %(name)s\n'
                    '#SBATCH -o %(out)s\n'
                    '#SBATCH -e %(err)s\n'
                    '#SBATCH -p %(queue)s\n'
                    '#SBATCH --ntasks=%(n_process)s\n'
                    '#SBATCH --cpus-per-task=%(n_thread)s\n'
                    '%(node_cmd)s'
                    '%(exclusive_cmd)s'
                    '\n\n'
                    '%(env_cmd)s\n\n'
                    % ({'name': name,
                        'out': out,
                        'err': err,
                        'queue': self.queue,
                        'n_process': n_process,
                        'n_thread': n_thread,
                        'node_cmd': node_cmd,
                        'exclusive_cmd': exclusive_cmd,
                        'env_cmd': self.env_cmd,
                        'workdir': workdir
                        })
                    )
            for cmd in srun_commands:
                f.write(cmd + '\n')

    def submit(self, sh=None):
        if sh is None:
            sh = self.sh
        sp = Popen(['sbatch', sh])
        sp.communicate()
        if sp.returncode == 0:
            return True
        else:
            return False

    def kill_job(self, name) -> bool:
        id = self.get_id_from_name(name)
        if id == None:
            return False
        try:
            subprocess.check_call(['scancel', str(id)])
        except:
            raise JobManagerError('Cannot kill job: %s' % name)

        return True

    def get_all_jobs(self):
        def get_job_from_str(job_str) -> PbsJob:
            for line in job_str.split():  # split properties
                key = line.split('=')[0]
                val = line.split('=')[1]
                if key == 'JobId':
                    id = int(val)
                elif key == 'Name':
                    name = val
                elif key == 'JobState':
                    state_str = val
                    if val == 'PENDING':
                        state = PbsJob.State.PENDING
                    elif val in ('CONFIGURING', 'RUNNING', 'COMPLETING', 'STOPPED', 'SUSPENDED'):
                        state = PbsJob.State.RUNNING
                    else:
                        state = PbsJob.State.DONE
                elif key == 'WorkDir':
                    workdir = val
            job = PbsJob(id=id, name=name, state=state, workdir=workdir)
            job.state_str = state_str
            return job

        # TODO Only show jobs belong to self.username
        cmd = 'scontrol show job'
        try:
            output = subprocess.check_output(cmd.split())
        except Exception as e:
            raise JobManagerError(str(e))

        jobs = []
        for job_str in output.decode().split('\n\n'):  # split jobs
            if job_str.startswith('JobId'):
                job = get_job_from_str(job_str)
                jobs.append(job)
        return jobs
