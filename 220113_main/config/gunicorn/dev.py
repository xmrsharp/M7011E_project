"""Gunicorn *development* config file"""
import os, getpass



print("initializing gunicorn...")

print(f'env thinks that the user is [{os.getlogin()}]');
print(f'effective user is [{getpass.getuser()}]');

# Django WSGI application path in pattern MODULE_NAME:VARIABLE_NAME

wsgi_app = "phiwas.wsgi:application"
#wsgi_app = "phiwas.wsgi:application"
# The granularity of Error log outputs
loglevel = "debug"
# The number of worker processes for handling requests
workers = 2
# The socket to bind
bind = "127.0.0.1:8000"
# Restart workers when code changes (development only!)
reload = True
# Write access and error info to /var/log
accesslog = errorlog = "/var/log/gunicorn/dev.log"
# Redirect stdout/stderr to log file
capture_output = True
# PID file so you can easily fetch process ID
pidfile = "/var/run/gunicorn/dev.pid"
# Daemonize the Gunicorn process (detach & enter background)
#Current was no access to log files.
print("done...")
print("setting daemon true...")

###Comment out daemon if gunicorn wont start and output of failure will be printed to console
daemon = True
print("done...")
#OBS CURRENTLY HAVE TO CHOWN -cR UBUNTU:UBUNTU /var/run/gunicorn and /var/log/gunicorn each time.
#REMEMBER TO CHECK BOTH /var/run/gunicorn AND /var/log/gunicorn permissions
