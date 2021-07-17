"""
This script runs the application using a development server.
It contains the definition of routes and views for the application.
"""

import os
import pathlib
import cv2
import time

import requests
from flask import Flask, render_template, Response, session, abort, redirect, request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests

app = Flask(__name__)
app.secret_key = '49testing94'


t0 = time.time() 
camera=cv2.VideoCapture(0)

# Make the WSGI interface available at the top level so wfastcgi can get it.
wsgi_app = app.wsgi_app

def frames():
    #get frames from camera
    while True:
        success,frame=camera.read()
        if not success:
            break
        else:
           ret,buffer=cv2.imencode('.jpg', frame)
           frame=buffer.tobytes()

        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        t1 = time.time()
        num_seconds = t1 - t0
        if num_seconds > 3600:
            camera.release(num_seconds)
            
            
client_id = '1065200223248-dksn1k2nr97kgmhhqhrf2r9pekfo3mu5.apps.googleusercontent.com'
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, 'client_secret.json')

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=['https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/userinfo.email','openid'],
    redirect_uri='https://cnt-livestream.herokuapp.com/callback'
                                     )


def required_login(function):
    def wrapper(*args, **kwargs):
        if 'google_id' not in session:
            return abort(401) #Authorization required
        else:
            return function()
    return wrapper

@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session['state'] == request.args['state']:
        abort(500)

    credentials = flow.credentials 
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=client_id
    )

    session['google_id'] = id_info.get('sub')
    session['name'] = id_info.get('name')
    return redirect('/home')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/')
def welcome():
    #login welcome page
    return render_template('welcome.html')

#static video page
@app.route('/video')
@required_login
def video():
    return render_template('video.html')

#live stream
@app.route('/webcam')
def webcam():
    return Response(frames(),mimetype='multipart/x-mixed-replace; boundary=frame')
    
@app.route('/live') 
def live():
    return render_template('live.html')
    

#home page
@app.route('/home')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run()
