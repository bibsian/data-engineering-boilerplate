import json
import uuid
from datetime import datetime


class EarthquakeActivity:

    CATASTROPHIC_THRESHOLD = 7.0

    def __init__(self, latitude, longitude, depth, magnitude):
        self.id = str(uuid.uuid4())
        self.latitude = latitude
        self.longitude = longitude
        self.depth = depth
        self.magnitude = magnitude
        self.timestamp = datetime.now().isoformat()
        self.activity_type = 'EARTHQUAKE'
        self.is_catastrophic = magnitude > self.CATASTROPHIC_THRESHOLD

    def __str__(self):
        return json.dumps({
            'activityType': self.activity_type,
            'depth': self.depth,
            'id': self.id,
            'isCatastrophic': self.is_catastrophic,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'magnitude': self.magnitude,
            'timestamp': self.timestamp
        })
