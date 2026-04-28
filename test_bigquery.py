from google.cloud import bigquery

client = bigquery.Client()
query = "SELECT COUNT(*) as n FROM `bigquery-public-data.crypto_bitcoin.transactions`"
result = client.query(query).result()
for row in result:
    print("Transazioni totali:", row.n)
