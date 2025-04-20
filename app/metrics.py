from prometheus_client import Counter


PVZ_CREATED = Counter("pvz_created_total", "Total PVZ Created")
RECEPTIONS_CREATED = Counter("receptions_created_total", "Total Receptions Created")
PRODUCTS_ADDED = Counter("products_added_total", "Total Products Added")

# docker run -d -p 9090:9090 -v .\app\prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
