import logging
import os

import sqlalchemy

logger = logging.getLogger(__name__)

STAGE = os.getenv("STAGE", "dev")
if "dev" in STAGE:
    CONN_STR = "postgresql+psycopg2://postgres:thiswouldbehidden@warehouse_dev/earthquakes_dev"
else:
    CONN_STR = "postgresql+psycopg2://postgres:thiswouldbehidden@warehouse/earthquakes_prod"


def create_engine():
    """
    All creditials would be stored in AWS's System Manager (parameter store)
    and fetched through boto3 (credentials required to utilize/can
    be injected during container creation and later removed).
    """

    # container host are discoverable by their <container_name> i.e. host = 'warehouse'
    return sqlalchemy.create_engine(CONN_STR, echo=True)
