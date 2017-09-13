import os
from functools import wraps

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
