'''Deploy Sandboxes to Kubernetes (and other operations)'''
import os
import argparse
import subprocess
import sys
import json

assert sys.version_info.major == 3, 'Use Python 3'


def deploy(args):
    run_script_and_print_output(
        command_line_from_local_file('deploy.sh'), args)

def list_(args):
    for sandbox in get_sandboxes(args):
        print(sandbox)

def pod_statuses(args):
    for pod_status in get_pod_statuses(args):
        print(pod_status)

def get_sandboxes(args):
    output = run_script(
        ['kubectl', 'get', 'namespaces', '--output=json'], args)
    namespace_info = json.loads(output.stdout)
    sandboxes = []
    for item in namespace_info['items']:
        assert item['kind'] == 'Namespace', item
        name = item['metadata']['name']
        if name.startswith('user-'):
            assert item['status'] == {'phase': 'Active'}, item
            sandboxes.append(name.replace('user-', ''))
    return sandboxes

def get_pod_statuses(args):
    output = run_script(
        ['kubectl', 'get', 'pods', '--all-namespaces', '--output=json'], args)
    pod_info = json.loads(output.stdout)
    pod_statuses = []
    for item in pod_info['items']:
        namespace = item['metadata']['namespace']
        if not namespace.startswith('user-'):
            continue
        pod = {}
        pod['user'] = namespace.replace('user-', '')
        pod['app'] = item['metadata']['labels']['app']
        pod['phase'] = item['status']['phase']  # Running or Pending
        conditions = sorted(item['status']['conditions'],
                            key=lambda x: x['lastTransitionTime'])
        latest_status = conditions[-1]
        pod['status'] = latest_status['type']
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


def command_line_from_local_file(filename):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    return [os.path.join(this_dir, filename)]

def run_script_and_print_output(command_line, args):
    try:
        output = run_script(command_line, args)
    except subprocess.CalledProcessError as err:
        print(err.output.decode('utf-8'))
        print('ERROR:', err)
        return False
    print(output.stdout.decode('utf-8'))

def run_script(command_line, args):
    # ensure args is a dict
    if isinstance(args, argparse.Namespace):
        args = vars(args)

    # transfer args to environment variables
    command_env = os.environ.copy()
    for key, value in args.items():
        command_env[key.upper().replace('-', '_')] = \
            value

    return subprocess.run(
        command_line,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # so errors are not swallowed
        check=True,
        env=command_env)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    def add_helm_arguments(parser_):
        parser_.add_argument('--platform-env',
                             default=os.environ.get('SANDBOX') or 'sandbox')
        parser_.add_argument(
            '--chart-env-config-dir',
            default=os.environ.get('CHART_ENV_CONFIG') or
            '../data-science-sandbox-infrastucture/chart-env-config')
        parser_.add_argument('--helm', default=os.environ.get('HELM') or
                             'helm')
    subparsers = parser.add_subparsers()

    parser_ = subparsers.add_parser('deploy',
                                    help='Create/update user & rstudio')
    add_helm_arguments(parser_)
    parser_.add_argument('--username', default=os.environ.get('USERNAME'))
    parser_.add_argument('--email', default=os.environ.get('EMAIL'))
    parser_.add_argument('--fullname', default=os.environ.get('FULLNAME'))
    parser_.set_defaults(func=deploy)

    parser_ = subparsers.add_parser('list',
                                    help='Get a list of all the sandboxes')
    parser_.set_defaults(func=list_)

    parser_ = subparsers.add_parser('pod_statuses',
                                    help='Get the statuses of all user pods')
    parser_.set_defaults(func=pod_statuses)

    args = parser.parse_args()
    if 'func' not in args:
        parser.error('You need to specify a command')
    args_dict = dict(args.__dict__)
    args_dict.pop('func')
    args.func(args_dict)
