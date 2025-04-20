import grpc
import pytest
import psycopg2
from concurrent import futures
from app.grpc.pvz_v1 import pvz_pb2, pvz_pb2_grpc
from app.grpc.grpc_server import PVZService
from app.security import settings


@pytest.fixture(scope="module")
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pvz_pb2_grpc.add_PVZServiceServicer_to_server(PVZService(), server)
    server.add_insecure_port("[::]:3001")
    server.start()
    yield server
    server.stop(grace=None)


@pytest.fixture(scope="module")
def grpc_channel(grpc_server):
    channel = grpc.insecure_channel("localhost:3001")
    yield channel
    channel.close()


@pytest.fixture(scope="module")
def setup_test_data():
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME,
    )
    cur = conn.cursor()

    pvz = ("11111111-1111-1111-1111-111111111111", "2023-01-01 10:00:00", "Москва")

    cur.execute(
        "INSERT INTO pvz (id, registration_date, city) VALUES (%s, %s, %s)", pvz
    )

    conn.commit()
    yield
    cur.execute(
        "DELETE FROM pvz WHERE id = %s AND registration_date = %s AND city = %s", pvz
    )
    conn.commit()
    conn.close()


def test_get_pvz_list(grpc_channel, setup_test_data):
    stub = pvz_pb2_grpc.PVZServiceStub(grpc_channel)

    response = stub.GetPVZList(pvz_pb2.GetPVZListRequest())

    assert response is not None
    assert response.pvzs[-1].id == "11111111-1111-1111-1111-111111111111"
    assert response.pvzs[-1].city == "Москва"
