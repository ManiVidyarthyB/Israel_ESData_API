from elasticsearch import Elasticsearch
import datetime
from dateutil.relativedelta import relativedelta

from dotenv import load_dotenv
import os

load_dotenv()

ES_SECURE_ENDPOINT = os.getenv("ES_SECURE_ENDPOINT")

ES = Elasticsearch(
    ES_SECURE_ENDPOINT
)


project_id = 'legacy_ford_081519'

date_today = datetime.datetime.now().strftime("%Y-%m-%d")

response = ES.search(
	index='vehicles1',
	body={
		"size": 500,
		"query": {
			"bool": {
				"must": [
					{
						"term": {
							"project_id.keyword": project_id
						}
					},
					{
						"range": {
							"expire_on": {
								"gte": date_today
							}
						}
					}
				]
			}
		}
	}
)

res = {
	'project_id': project_id,
	'vehicles': []
}

hits = response.get('hits', {}).get('hits', [])

print(response.get('hits', {}).get('total', {}).get('value', 0))

if hits:

	res['vehicles'] = [
		{
			'vin': vehicle_doc.get('_source', {}).get('vin'),
			'display_pics': vehicle_doc.get('_source', {}).get('display_pics'),
			'modified_date': vehicle_doc.get('_source', {}).get('last_modified')
		}
		for vehicle_doc in hits
		if (
			vehicle_doc.get('_source', {}).get('display_pics')
			and len(vehicle_doc.get('_source', {}).get('display_pics')) > 0
		)
	]

print(res)

print(len(res.get('vehicles', [])))