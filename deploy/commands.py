'''Deploy Sandboxes to Kubernetes (and other operations)'''
import os
import argparse
import subprocess
import sys
import json

assert sys.version_info.major == 3, 'Use Python 3'

DEFAULT_CHART_ENV_CONFIG = \
    '../data-science-sandbox-infrastucture/chart-env-config'
DEFAULT_PLATFORM_ENV = 'sandbox'
DEFAULT_HELM = 'helm'

# Command-line functions


def deploy_cmd(args):
    run_and_print_output_and_exit(deploy, args)


def list_(args):
    for sandbox in get_sandboxes(args):
        print(sandbox)


def pod_statuses(args):
    try:
        for pod_status in get_pod_statuses(args):
            print(pod_status)
    except subprocess.CalledProcessError as err:
        print(err.output.decode('utf-8'))
        print('ERROR:', err)
        sys.exit(1)



def delete_user_cmd(args):
    run_and_print_output_and_exit(delete_user, args)


def delete_chart_cmd(args):
    run_and_print_output_and_exit(delete_chart, args)


# Actions - can be called from either command-line OR the Flask API

def deploy(args):
    '''Runs the deploy script.
    This can be called from either the command-line OR the API.
    Returns a CompletedProcess
    Raises subprocess.CalledProcessError on non-zero exit code.
    '''
    set_defaults_from_environment(args)
    return run_script(
        command_line_from_local_file('deploy.sh'),
        args)


def get_sandboxes(args):
    output = run_(['kubectl', 'get', 'namespaces', '--output=json'])
    namespace_info = json.loads(output.stdout.decode('utf8'))
    sandboxes = []
    for item in namespace_info['items']:
        assert item['kind'] == 'Namespace', item
        name = item['metadata']['name']
        if name.startswith('user-'):
            assert item['status'] == {'phase': 'Active'}, item
            sandboxes.append(name.replace('user-', ''))
    return sandboxes


def get_pod_statuses(args):
    output = run_(
        ['kubectl', 'get', 'pods', '--all-namespaces', '--output=json'])
    pod_info = json.loads(output.stdout.decode('utf8'))
    pod_statuses = []
    for item in pod_info['items']:
        namespace = item['metadata']['namespace']
        if not namespace.startswith('user-'):
            continue
        pod = {}
        pod['user'] = namespace.replace('user-', '')
        if not 'app' in item['metadata']['labels']:
            # e.g. config-git-<username>-<hex>
            continue
        pod['app'] = item['metadata']['labels']['app']
        pod['phase'] = item['status']['phase']  # Running or Pending
        conditions = sorted(item['status']['conditions'],
                            key=lambda x: x['lastTransitionTime'])
        latest_status = conditions[-1]
        pod['status'] = latest_status['type']
        pod['lastTransitionTime'] = latest_status['lastTransitionTime']
        pod['error'] = any([
            condition['status'] == "False"
            for condition in item['status']['conditions']
            ])
        pod['messages'] = ';'.join([
            condition['message']
            for condition in item['status']['conditions']
            if condition['status'] == "False"
            ])
        pod_statuses.append(pod)
    return pod_statuses


def delete_user(args):
    # $HELM delete init-user-davidread --purge
    set_defaults_from_environment(args)
    return run_(
        [args['HELM'], 'delete', 'init-user-{}'.format(args['username']),
         '--purge'])


def delete_chart(args):
    # $HELM delete davidread-rstudio --purge
    set_defaults_from_environment(args)
    return run_(
        [args['HELM'], 'delete', '{}-{}'.format(args['username'], args['chart']),
         '--purge'])


# Action utils

def set_defaults_from_environment(args):
    arg_keys_and_defaults = (
        ('CHART_ENV_CONFIG', DEFAULT_CHART_ENV_CONFIG),
        ('PLATFORM_ENV', DEFAULT_PLATFORM_ENV),
        ('HELM', DEFAULT_HELM),
        )
    for key, default_value in arg_keys_and_defaults:
        set_default_from_environment(args, key, default_value)


def set_default_from_environment(dict_, key, default_value):
    '''Given a config dictionary, if the key is not set with a value,
    gets it from the environment or falls back to a given default value.
    '''
    if dict_.get(key):
        return
    env_key = key.upper().replace('-', '_')
    if env_key in os.environ:
        dict_[key] = os.environ[env_key]
        return
    if default_value:
        dict_[key] = default_value


def command_line_from_local_file(filename):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    return [os.path.join(this_dir, filename)]


def run_and_print_output_and_exit(func, *kargs, **kwargs):
    '''Calls function that runs something on the command-line.
    Prints the output and exits the program with appropriate exit code.
    '''
    try:
        output = func(*kargs, **kwargs)
    except subprocess.CalledProcessError as err:
        print(err.output.decode('utf-8'))
        print('ERROR:', err)
        sys.exit(1)
    print(output.stdout.decode('utf-8'))
    sys.exit(0)


def run_script(command_line, args):
    '''Runs one of our bash scripts.
    Converts the args to environment variables, as is the convention for our
    scripts.
    Returns a CompletedProcess instance containing the output.
    Raises subprocess.CalledProcessError on non-zero exit code.
    '''
    # ensure args is a dict
    if isinstance(args, argparse.Namespace):
        args = vars(args)

    # transfer args to environment variables
    command_env = os.environ.copy()
    for key, value in args.items():
        if value:
            command_env[key.upper().replace('-', '_')] = \
                value

    return run_(command_line, command_env)


def run_(command_line, env_vars=None):
    '''Runs a command.
    Returns a CompletedProcess instance containing the output.
    Raises subprocess.CalledProcessError on non-zero exit code.
    '''
    return subprocess.run(
        command_line,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # so errors are not swallowed
        check=True,
        env=env_vars or os.environ)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    def add_helm_arguments(parser_, include_charts=True):
        if include_charts:
            parser_.add_argument('--platform-env',
                                 default=os.environ.get('SANDBOX') or
                                 DEFAULT_PLATFORM_ENV)
            parser_.add_argument(
                '--chart-env-config',
                default=os.environ.get('CHART_ENV_CONFIG') or
                DEFAULT_CHART_ENV_CONFIG)
        parser_.add_argument('--helm', default=os.environ.get('HELM') or
                             DEFAULT_HELM)
    subparsers = parser.add_subparsers()

    parser_ = subparsers.add_parser('deploy',
                                    help='Create/update user & rstudio')
    add_helm_arguments(parser_)
    parser_.add_argument('--username', default=os.environ.get('USERNAME'))
    parser_.add_argument('--email', default=os.environ.get('EMAIL'))
    parser_.add_argument('--fullname', default=os.environ.get('FULLNAME'))
    parser_.set_defaults(func=deploy_cmd)

    parser_ = subparsers.add_parser('list',
                                    help='Get a list of all the sandboxes')
    parser_.set_defaults(func=list_)

    parser_ = subparsers.add_parser('pod_statuses',
                                    help='Get the statuses of all user pods')
    parser_.set_defaults(func=pod_statuses)

    parser_ = subparsers.add_parser('delete_user',
                                    help='Delete a user\'s sandbox '
                                    '(everything but the apps?)')
    add_helm_arguments(parser_, include_charts=False)
    parser_.add_argument('username', default=os.environ.get('USERNAME'))
    parser_.set_defaults(func=delete_user_cmd)

    parser_ = subparsers.add_parser('delete_chart',
                                    help='Delete one chart/app in someone\'s '
                                    'sandbox')
    add_helm_arguments(parser_, include_charts=False)
    parser_.add_argument('username', default=os.environ.get('USERNAME'))
    parser_.add_argument('chart',
                         default=os.environ.get('CHART') or 'rstudio',
                         help='NB "<username>-" is prepended automatically')
    parser_.set_defaults(func=delete_chart_cmd)

    args = parser.parse_args()
    if 'func' not in args:
        parser.error('You need to specify a command')
    args_dict = dict(args.__dict__)
    args_dict.pop('func')
    args.func(args_dict)
