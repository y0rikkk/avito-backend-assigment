docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate -i /local/swagger.yaml -g python -o /local/out/python
docker exec -it avito-test-backend-1 python generate_dto.py --input swagger.yaml
docker exec -it avito-test-backend-1 python -m app.grpc.grpc_client
docker exec -it avito-test-backend-1 pytest -v
docker exec -it avito-test-backend-1 pytest --cov=app --cov-report=html tests -v ; start htmlcov/index.html
