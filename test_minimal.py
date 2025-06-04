from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-key'

@app.route('/')
def hello():
    return '<h1>Minimal Test Working!</h1>'

@app.route('/test')
def test():
    return '<h1>Test Endpoint Working!</h1>'

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=True) 