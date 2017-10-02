import os
from functools import wraps
import subprocess

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify, Response

from deploy import commands

app = Flask('deploy.default_settings')
app.config.from_object(__name__)
app.config.from_envvar('DEPLOY_SETTINGS', silent=True)

# to avoid mishaps, you must set USERNAME. If set to blank then there is no
# auth required (for local testing only).
USERNAME = os.environ['SANDBOX_DEPLOY_USERNAME']
PASSWORD = os.environ.get('SANDBOX_DEPLOY_PASSWORD')


def check_auth(username, password):
    return username == USERNAME and password == PASSWORD


def challenge():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if USERNAME:
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return challenge()
        return f(*args, **kwargs)
    return decorated


@app.route('/')
@requires_auth
def show_entries():
    sandboxes = commands.get_sandboxes({})
    return render_template('sandboxes.html', sandboxes=sandboxes)


@app.route('/api/sandboxes', methods=['GET'])
@requires_auth
def get_sandboxes():
    sandboxes = commands.get_sandboxes(args={})
    return jsonify(sandboxes)


@app.route('/api/pod-statuses', methods=['GET'])
@requires_auth
def get_pod_statuses():
    data = commands.get_pod_statuses(args={})
    return jsonify(data)


@app.route('/api/deploy', methods=['POST'])
@requires_auth
def deploy():
    request_data = request.get_json()
    data = dict(
        fullname=request_data['name'],
        username=request_data['github'],
        email=request_data['email'],
        )
    try:
        response = commands.deploy(args=data)
    except subprocess.CalledProcessError as e:
        app.logger.error('Error calling deploy.sh: %s', str(e.output))
        return Response('Error calling deploy', 500)
    # currently just text
    return jsonify({'text': response.stdout.decode('utf-8')})


@app.route('/api/delete', methods=['POST'])
@requires_auth
def delete():
    request_data = request.get_json()
    data = dict(username=request_data['github'])

    # Delete the user
    try:
        response = commands.delete_user(args=data)
    except subprocess.CalledProcessError as e:
        app.logger.error('Error calling deploy.sh: %s', str(e.output))
        return Response('Error calling deploy', 500)

    # Delete the app
    try:
        data['chart'] = 'rstudio'
        response = commands.delete_chart(args=data)
    except subprocess.CalledProcessError as e:
        app.logger.error('Error calling deploy.sh: %s', str(e.output))
        return Response('Error calling deploy', 500)

    # currently just text
    return jsonify({'text': response.stdout.decode('utf-8')})
