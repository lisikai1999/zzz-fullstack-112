from flask import Flask
from flask_cors import CORS
from database import init_db

app = Flask(__name__)
CORS(app)

init_db()

from routes.exams import exams_bp
from routes.analysis import analysis_bp
from routes.evidence import evidence_bp

app.register_blueprint(exams_bp, url_prefix='/api')
app.register_blueprint(analysis_bp, url_prefix='/api')
app.register_blueprint(evidence_bp, url_prefix='/api')


@app.route('/api/health')
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    app.run(debug=True, port=5000)
