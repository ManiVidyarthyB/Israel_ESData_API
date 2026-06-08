from elasticsearch import Elasticsearch
import elasticsearch
import datetime

from dotenv import load_dotenv
import os

load_dotenv()

ES_SECURE_ENDPOINT = os.getenv("ES_SECURE_ENDPOINT")

ES = Elasticsearch(
    ES_SECURE_ENDPOINT
)

if __name__ == '__main__':
    vin = 'ZN661XUS8JX284187'.lower()
    vehicle_id = 'mp15740_053017-'+vin
    # vehicle_doc = ES.get(index='vehicles1', doc_type='inventory', id=vehicle_id)['_source']
    try:
        vehicle_doc = ES.get(index='vehicles1', id=vehicle_id)['_source']
        print (vehicle_doc)
        # a = 1/0
    # except elasticsearch.ElasticsearchException as es1:
    except Exception as e:
        # if es1.status_code == 404:
        #     print "get"
        # print es1.status_code
        print (e.status_code)
    print ('display_pics' in vehicle_doc)
    print ('display_pics2' in vehicle_doc)
    # print(vehicle_doc)
    # date_today = datetime.datetime.now().strftime("%Y-%m-%d")
    # vehicle_doc = ES.search(index='vehicles1', doc_type='inventory', q="vin:{} AND library_id:{} AND expire_on:[{} TO *]".format("1FTBF2B61GEC92596", "10011020061817", date_today))
    # print(vehicle_doc['hits']['hits'][0]['_source']["project_id"])
    # vehicle_doc = ES.search(index='vehicles1', doc_type='inventory',
    #                         q="vin:{}".format("5FNRL6H73LB060234"))
    # print vehicle_doc["hits"]["total"]
    # print vehicle_doc["hits"]["hits"][0]['_source']['project_id']
