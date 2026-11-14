"""
Entry point for Flask web application and xt32.local supervisor / proxy provisioner.
"""
from web_app import app, start_server

if __name__ == "__main__":
    start_server()
