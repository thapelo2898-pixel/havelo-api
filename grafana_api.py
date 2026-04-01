from flask import Flask, jsonify
from firebase_admin import credentials, firestore
import firebase_admin, os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

import json

# Load credentials from the Railway environment variable
if 'FIREBASE_CREDENTIALS' in os.environ:
    cred_json = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
    cred = credentials.Certificate(cred_json)
else:
    # Fallback for local testing if the file exists
    cred = credentials.Certificate('serviceAccountKey.json')

firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route("/detections")
def get_detections():
    """Return last 24 hours of detections as JSON array."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    docs = db.collection("detections")\
             .where("timestamp", ">=", cutoff.isoformat())\
             .order_by("timestamp", direction=firestore.Query.DESCENDING)\
             .limit(1000)\
             .stream()
    return jsonify([d.to_dict() for d in docs])

@app.route("/heatmap")
def get_heatmap():
    """Return latest congestion score per location for map view."""
    locs = {}
    docs = db.collection("detections")\
             .order_by("timestamp", direction=firestore.Query.DESCENDING)\
             .limit(200).stream()
    for d in docs:
        data = d.to_dict()
        loc = data.get("location")
        if loc and loc not in locs:
            locs[loc] = data    # keep only latest per location
    return jsonify(list(locs.values()))

@app.route("/summary")
def get_summary():
    """Stats for the 4 top cards in Grafana dashboard."""
    docs = list(db.collection("detections")
                  .order_by("timestamp", direction=firestore.Query.DESCENDING)
                  .limit(500).stream())
    data = [d.to_dict() for d in docs]
    totals = [d.get("total_vehicles",0) for d in data]
    taxis  = [d.get("taxi_count",0) for d in data]
    return jsonify({
        "total_vehicles_today": sum(totals),
        "avg_taxi_pct": round(sum(taxis)/sum(totals)*100 if sum(totals)>0 else 0, 1),
        "active_locations": len(set(d.get("location") for d in data)),
        "high_congestion_count": sum(1 for d in data if d.get("congestion_level")=="High")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
