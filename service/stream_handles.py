import os
import json
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

STAGE = os.getenv("STAGE", "dev")


class StreamDirectToDbBase:
    def __init__(self, engine):
        self.engine = engine

    def insert(self, *args, **kwargs):
        raise NotImplementedError

    def pre_process(self, data):
        return data

    def trigger(self, data):
        return data
    
    def transform(self, data):
        return data


class EarthquakeStream(StreamDirectToDbBase):
    TABLE_NAME = "earthquake_activity"
    ALLOWED_EXCEPTIONS = 10 if "prod" in STAGE else 0

    @staticmethod
    def json_insert(tbl:str, data:dict):
        return f"""
        INSERT INTO {tbl} (raw) VALUES ('{data}')
        """

    def __init__(self, engine):
        super().__init__(engine)
        self.exception_cnt = 0

    def insert(self, raw:str):
        stmt = self.json_insert(self.TABLE_NAME, data=raw)
        with self.engine.connect() as connection:
            connection.execute(text(stmt))

    def pre_process(self, data):
        return json.loads(data)

    def process(self, data):
        try:
            self.transform(self.trigger(self.pre_process(data)))
        except Exception as ex:
            self.exception_cnt += 1
            if self.exception_cnt == self.ALLOWED_EXCEPTIONS:
                raise ex
            else:
                logger.warning(f"Failed processing: {data}")
        self.insert(data)

        return True

    def trigger(self, data, handler_func=None):
        if data.get("isCatastrophic") and handler_func:
            _ = handler_func(data)
        return data


class TectonicStressStream(EarthquakeStream):
    TABLE_NAME = "sensor_tectonic_stress"

    def __init__(self, engine):
        super().__init__(engine)

    def trigger(self, data):
        return data

