# all the imports
import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from deploy import commands

app = Flask('deploy.default_settings')
app.config.from_object(__name__)
app.config.from_envvar('DEPLOY_SETTINGS', silent=True)

@app.route('/')
def show_entries():
    sandboxes = commands.get_sandboxes({})
    return render_template('sandboxes.html', sandboxes=sandboxes)
