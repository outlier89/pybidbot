#!flask/bin/python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/',methods=['GET'])
def index():
    %store -r curr_round
    %store -r last_round
    return jsonify ({"current_round": curr_round,"last_round":last_round})

if __name__ == "__main__":
    app.run(host='0.0.0.0',ssl_context=('cert.crt', 'pvt.key')) # Replace with cert.crt & pvt.key with your SSL certs & private key or remove this to disable https
