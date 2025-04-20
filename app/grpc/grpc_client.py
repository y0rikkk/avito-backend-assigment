import grpc
from app.grpc.pvz_v1 import pvz_pb2, pvz_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp


def run():
    channel = grpc.insecure_channel("localhost:3000")
    stub = pvz_pb2_grpc.PVZServiceStub(channel)

    request = pvz_pb2.GetPVZListRequest()

    response = stub.GetPVZList(request)

    for pvz in response.pvzs:
        print(f"ID: {pvz.id}")
        print(f"City: {pvz.city}")

        dt = pvz.registration_date.ToDatetime()
        print(f"Date: {dt.isoformat()}\n")


if __name__ == "__main__":
    run()
