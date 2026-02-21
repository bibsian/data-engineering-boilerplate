from minio import Minio
import io


def create_lake_client():
    """ Create and return a MinIO client """
    client = Minio(
        "minio:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=True
    )
    return client
