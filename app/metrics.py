from prometheus_client import Counter


PVZ_CREATED = Counter("pvz_created_total", "Total PVZ Created")
RECEPTIONS_CREATED = Counter("receptions_created_total", "Total Receptions Created")
PRODUCTS_ADDED = Counter("products_added_total", "Total Products Added")
