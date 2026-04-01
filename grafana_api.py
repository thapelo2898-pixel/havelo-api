from flask import Flask, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# Force the app to use the Railway Environment Variable
if 'FIREBASE_CREDENTIALS' in os.environ:
    cred_json = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred)
else:
    raise ValueError("FIREBASE_CREDENTIALS variable not found in Railway!")

db = firestore.client()

@app.route("/detections")
def get_detections():
    """Return last 24 hours of detections as a JSON array."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    docs = db.collection("detections")\
             .where("timestamp", ">=", cutoff.isoformat())\
             .order_by("timestamp", direction=firestore.Query.DESCENDING)\
             .limit(1000)\
             .stream()
    
    return jsonify([d.to_dict() for d in docs])

@app.route("/heatmap")
def get_heatmap():
    """Return latest 100 detections for heatmap coordinates."""
    docs = db.collection("detections")\
             .order_by("timestamp", direction=firestore.Query.DESCENDING)\
             .limit(100)\
             .stream()
    
    return jsonify([{"lat": d.get("latitude"), "lng": d.get("longitude")} for d in docs])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
