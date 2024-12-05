from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from the home page"

@app.route('/landing')
def landing():
    return "Hello from the landing page"

if __name__ == '__main__':
    app.run(debug=True, port=5001)
