import json
import uuid
from datetime import datetime


class TectonicStressActivity:

    def __init__(self, stress_magnitude):
        self.id = str(uuid.uuid4())
        self.stress_magnitude = stress_magnitude
        self.timestamp = datetime.now().isoformat()
        self.activity_type = 'TECTONIC_STRESS'

    def __str__(self):
        return json.dumps({
            'activityType': self.activity_type,
            'id': self.id,
            'stressMagnitude': self.stress_magnitude,
            'timestamp': self.timestamp
        })
