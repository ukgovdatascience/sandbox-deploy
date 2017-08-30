'''Deploy Sandboxes to Kubernetes (and other operations)'''
import os
import argparse
import subprocess
import sys

assert sys.version_info.major == 3, 'Use Python 3'


def deploy(args):
    run_script('deploy.sh', args)

def run_script(filename, env_overrides):
    command_env = os.environ.copy()
    for key in ('username', 'email', 'fullname',
                'platform_env', 'chart_env_config_dir', 'helm'):
        if getattr(env_overrides, key):
            command_env[key.upper().replace('-', '_')] = \
                getattr(env_overrides, key)
    this_dir = os.path.dirname(os.path.realpath(__file__))
    try:
        output = subprocess.run(
            [os.path.join(this_dir, filename)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # so errors are not swallowed
            check=True,
            env=command_env)
    except subprocess.CalledProcessError as err:
        print(err.output.decode('utf-8'))
        print('ERROR:', err)
        return False
    print(output.stdout.decode('utf-8'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform-env',
                        default=os.environ.get('SANDBOX') or 'sandbox')
    parser.add_argument('--chart-env-config-dir',
                        default=os.environ.get('CHART_ENV_CONFIG') or
                        'chart-env-config')
    parser.add_argument('--helm', default=os.environ.get('HELM') or 'helm')
    subparsers = parser.add_subparsers()

    parser_ = subparsers.add_parser('deploy',
                                    help='Create/update user & rstudio')
    parser_.add_argument('--username')
    parser_.add_argument('--email')
    parser_.add_argument('--fullname')
    parser_.set_defaults(func=deploy)

    parser_ = subparsers.add_parser('list',
                                    help='Get a list of all the sandboxes')
    parser_.set_defaults(func=deploy)

    args = parser.parse_args()
    if 'func' not in args:
        parser.error('You need to specify a command')
    args.func(args)
