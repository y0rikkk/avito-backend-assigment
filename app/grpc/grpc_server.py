from concurrent import futures
import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from app.grpc.pvz_v1 import pvz_pb2, pvz_pb2_grpc
from app.security import settings
import psycopg2

# python -m grpc_tools.protoc -I app/grpc/pvz_v1 --python_out=app/grpc/pvz_v1 --grpc_python_out=app/grpc/pvz_v1 app/grpc/pvz_v1/pvz.proto


class PVZService(pvz_pb2_grpc.PVZServiceServicer):
    def GetPVZList(self, request, context):
        conn = None
        try:
            conn = psycopg2.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                dbname=settings.DB_NAME,
            )
            cur = conn.cursor()
            cur.execute("SELECT id, registration_date, city FROM pvz")
            rows = cur.fetchall()

            response = pvz_pb2.GetPVZListResponse()
            for row in rows:
                pvz = response.pvzs.add()
                pvz.id = row[0]

                timestamp = Timestamp()
                timestamp.FromDatetime(row[1])
                pvz.registration_date.CopyFrom(timestamp)

                pvz.city = row[2]

            return response

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return pvz_pb2.GetPVZListResponse()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pvz_pb2_grpc.add_PVZServiceServicer_to_server(PVZService(), server)
    server.add_insecure_port("[::]:3000")
    server.start()
    print("gRPC Server running on port 3000")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
