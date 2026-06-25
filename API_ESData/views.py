import datetime
import sys
import os
import traceback
from urllib import response
import logging

from elasticsearch import NotFoundError, TransportError
import logging
logger = logging.getLogger(__name__)
#from fastapi import logger

from rest_framework import views, status
from rest_framework.response import Response

from elasticsearch import Elasticsearch
from . import email_alert_EZ360
import string
from dateutil.relativedelta import relativedelta

ES_VEHICLE_INDEX = "vehicles2_v9"
ES_MAX_RESULT_SIZE = 500

DEFAULT_THUMBNAIL_HEIGHT = 500
DEFAULT_TEST_THUMBNAIL_HEIGHT = 200

from elasticsearch import Elasticsearch as ES9Client

from dotenv import load_dotenv
import os

load_dotenv()

ES_SECURE_ENDPOINT = os.getenv("ES_SECURE_ENDPOINT")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

ES9 = Elasticsearch(
    ES_SECURE_ENDPOINT,
    api_key=ELASTIC_API_KEY,
    verify_certs=False,
    request_timeout=300,
)

BASE_iVanaInteriorUrl = 'https://ivana.sister.tv/models/interior360/index.html?'
BASE_exterior360Url = 'https://ivana.sister.tv/models/exterior360_msk/index.html?'

def removeNonAscii(origin_string):
	if not origin_string:
		return origin_string

	printable = set(string.printable)
	result_string = ''.join(filter(lambda x: x in printable, str(origin_string)))
	return result_string

def checkIfRollingHillDealer(project_id):
	return project_id == "rollinghill_honda_01042020" or project_id == "rollinghill_nissan_01042020" or \
		   project_id == "rollinghill_toyota_01042020" or project_id == "rollinghill_used_01042020"

def pic2ThumbNail(pic_list, height=400):

	DISPLAY_BUCKET_IMGIX_HEAD = 'sistertech-display-pics.imgix.net'
	IVANA_BUCKET_IMGIX_HEAD = 'sistertech-ivana.imgix.net'

	result = []

	if not pic_list:
		return result

	for each_pic in pic_list:

		if not isinstance(each_pic, str):
			continue

		if 'display-pics' in each_pic:

			each_pic = each_pic.replace(
				"sistertech-display-pics.s3.amazonaws.com",
				DISPLAY_BUCKET_IMGIX_HEAD
			)

			each_pic = f"{each_pic}?h={height}"

			result.append(each_pic)

		elif '-ivana.s3' in each_pic:

			each_pic = each_pic.replace(
				"sistertech-ivana.s3.amazonaws.com",
				IVANA_BUCKET_IMGIX_HEAD
			)

			each_pic = f"{each_pic}?h={height}"

			result.append(each_pic)

		elif 'imgix.net' in each_pic:

			if '?' in each_pic:

				if 'mark=' in each_pic:

					if (
						'mark-h=' in each_pic and
						'mark-w=' in each_pic
					):

						mark_h = int(
							each_pic.split('mark-h=')[1]
							.split('&')[0]
						)

						mark_w = int(
							each_pic.split('mark-w=')[1]
							.split('&')[0]
						)

						if mark_w == 0 or mark_h == 0:

							each_pic = f"{each_pic}&q=10"

						else:

							ratio = float(height) / float(mark_h)

							width = int(ratio * mark_w)

							each_pic = (
								each_pic.split('mark-w=')[0]
								+
								f"mark-w={width}&"
								f"mark-h={height}&"
								f"mark-fit=scale&mark="
								+
								each_pic.split("mark=")[1]
								+
								f'&h={height}'
							)

					else:

						each_pic = f"{each_pic}&q=10"

				else:

					each_pic = f"{each_pic}&h={height}"

			else:

				each_pic = f"{each_pic}?h={height}"

			result.append(each_pic)

		else:

			result.append(each_pic)

	return result

class GetPlayer(views.APIView):

	def post(self, request):

		request_body = request.data

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if not project_id or not vin:

			return Response(
				'Please Enter Project ID and VIN',
				status=status.HTTP_400_BAD_REQUEST
			)

		elif project_id == "ignored":

			date_today = datetime.datetime.now().strftime("%Y-%m-%d")

			library_id = request_body.get('library_id')

			if library_id:
				library_id = removeNonAscii(library_id)
			else:
				return Response(
					'Please Enter Library ID',
					status=status.HTTP_400_BAD_REQUEST
				)

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
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

				hits = response.get(
					'hits',
					{}
				).get(
					'hits',
					[]
				)

				if not hits:

					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get('_source', {})

				ret_project_id = vehicle_doc.get("project_id")

				if ret_project_id:
					ret_project_id = removeNonAscii(ret_project_id)

				player_url = (
					f'https://player.sister.tv/'
					f'?project_id={ret_project_id}'
					f'&vin={vin.lower()}'
				)

				result = [player_url]

				return Response(
					result,
					status=status.HTTP_200_OK
				)

			except Exception as e:

				return Response(
					f'Getting Player Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		elif project_id == "rollinghill_01042020":

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				num_of_target = response['hits']['total']['value']

				if num_of_target == 1:

					project_id = (
						response["hits"]["hits"][0]
						.get('_source', {})
						.get('project_id')
					)

				elif num_of_target > 1:

					for i in range(num_of_target):

						project_id = (
							response["hits"]["hits"][i]
							.get('_source', {})
							.get('project_id')
						)

						if checkIfRollingHillDealer(project_id):
							break

				else:

					return Response(
						'Getting Player Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

				if checkIfRollingHillDealer(project_id):

					vehicle_id = (
						f"{project_id.lower()}-"
						f"{vin.lower()}"
					)

					try:


						#try:
						# response = ES9.get(
						# 	index=ES_VEHICLE_INDEX,
						# 	id=vehicle_id
						# )


						# vehicle_doc = response.get("_source", {})


						print("INDEX =", ES_VEHICLE_INDEX)
						print("VEHICLE_ID =", vehicle_id)

						response = ES9.search(
							index=ES_VEHICLE_INDEX,
							body={
								"query": {
									"ids": {
										"values": [vehicle_id]
									}
								}
							}
						)

						print(response)

						player_url = (
							f'https://player.sister.tv/'
							f'?project_id={project_id}'
							f'&vin={vin.lower()}'
						)

						result = [player_url]

						return Response(
							result,
							status=status.HTTP_200_OK
						)

					except Exception as e:

						return Response(
							f'Getting Player Failed: {e}.',
							status=status.HTTP_500_INTERNAL_SERVER_ERROR
						)

				else:

					return Response(
						'Getting Player Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

			except Exception as e:

				return Response(
					f'Getting Player Failed: {e}.',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		else:

			vehicle_id = (
				f"{project_id.lower()}-"
				f"{vin.lower()}"
			)

			try:
				# try:
				# response = ES9.get(
				# 	index=ES_VEHICLE_INDEX,
				# 	id=vehicle_id
				# )

				# vehicle_doc = response.get("_source", {})


				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"ids": {
								"values": [vehicle_id]
							}
						}
					}
				)

				hits = response.get("hits", {}).get("hits", [])

				if not hits:
					raise Exception(f"Vehicle not found: {vehicle_id}")

				vehicle_doc = hits[0].get("_source", {})

				player_url = (
					f'https://player.sister.tv/'
					f'?project_id={project_id}'
					f'&vin={vin.lower()}'
				)

				result = [player_url]

				return Response(
					result,
					status=status.HTTP_200_OK
				)

			except Exception as e:

				return Response(
					f'Getting Player Failed: {e}.',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

class GetAll(views.APIView):

	def post(self, request):

		request_body = request.data
		result_json = {}
		vehicle_doc = {}

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')
		input_library_id = request_body.get('library_id', "")

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if not project_id or not vin:

			return Response(
				'Please Enter Project ID and VIN',
				status=status.HTTP_400_BAD_REQUEST
			)

		elif project_id == "ignored":

			date_today = (
				datetime.datetime.now() +
				relativedelta(months=-1)
			).strftime("%Y-%m-%d")

			library_id = request_body.get('library_id')

			if library_id:
				library_id = removeNonAscii(library_id)
			else:
				return Response(
					'Please Enter Library ID',
					status=status.HTTP_400_BAD_REQUEST
				)

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
										}
									},
									{
										"range": {
											"expire_on": {
												"gte": date_today
											}
										}
									}
								],
								"must_not": [
									{
										"term": {
											"is_soft_del": True
										}
									}
								]
							}
						}
					}
				)

				res_data = response.get(
					'hits',
					{}
				).get(
					'hits',
					[]
				)

				for each in res_data:

					doc_source = each.get('_source', {})

					display_pics = doc_source.get(
						'display_pics',
						[]
					)

					if display_pics:
						vehicle_doc = doc_source
						break

				for each in res_data:

					if vehicle_doc:
						break

					doc_source = each.get('_source', {})

					third_party_pics = doc_source.get(
						'third_party_pics',
						[]
					)

					if third_party_pics:
						vehicle_doc = doc_source
						break

				if vehicle_doc:

					project_id = removeNonAscii(
						vehicle_doc.get("project_id")
					)

				else:

					return Response(
						'Cannot find any data of the VIN',
						status=status.HTTP_404_NOT_FOUND
					)

			except Exception as e:

				return Response(
					f'Getting All Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		elif project_id == "rollinghill_01042020":

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				num_of_target = response['hits']['total']['value']

				if num_of_target == 1:

					project_id = (
						response["hits"]["hits"][0]
						.get('_source', {})
						.get('project_id')
					)

				elif num_of_target > 1:

					for i in range(num_of_target):

						project_id = (
							response["hits"]["hits"][i]
							.get('_source', {})
							.get('project_id')
						)

						if checkIfRollingHillDealer(project_id):
							break

				else:

					return Response(
						'Getting All Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

				if checkIfRollingHillDealer(project_id):

					vehicle_id = f"{project_id.lower()}-{vin.lower()}"

					try:

						response = ES9.get(
							index=ES_VEHICLE_INDEX,
							id=vehicle_id
						)

						vehicle_doc = response.get('_source', {})

					except Exception as e:

						return Response(
							f'Getting All Failed: {e}.',
							status=status.HTTP_500_INTERNAL_SERVER_ERROR
						)

				else:

					return Response(
						'Getting All Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

			except Exception as e:

				return Response(
					f'Getting All Failed: {e}.',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		else:

			try:

				vehicle_id = f"{project_id.lower()}-{vin.lower()}"

				response = ES9.get(
					index=ES_VEHICLE_INDEX,
					id=vehicle_id
				)

				vehicle_doc = response.get('_source', {})

			except Exception as e:

				return Response(
					f'Getting All Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		try:

			if (
				vehicle_doc.get('display_pics', [])
				and vehicle_doc.get('is_publishable', False) is False
				and input_library_id not in (
					'202106221934',
					'icontent',
					'ez360bgrdemo'
				)
			):

				return Response(
					f'Vehicle is not publishable {input_library_id}',
					status=status.HTTP_404_NOT_FOUND
				)

			result_json['full_player'] = (
				f'https://player.sister.tv/'
				f'?project_id={project_id}&vin={vin}'
			)

			videos = []

			pic2vid_en_US = vehicle_doc.get('pic2vid_en_US')

			if pic2vid_en_US:
				videos.append(pic2vid_en_US)

			fullmo_sis = vehicle_doc.get('fullmo_sis')

			if fullmo_sis:
				videos.append(fullmo_sis)

			auto_up_link_video = vehicle_doc.get('auto_up_link_video')

			if auto_up_link_video:
				videos.append(auto_up_link_video)

			if videos:
				result_json['videos'] = videos

			year = vehicle_doc.get('year')

			if year:
				result_json['year'] = year

			make = vehicle_doc.get('make')

			if make:
				result_json['make'] = make

			model = vehicle_doc.get('model')

			if model:
				result_json['model'] = model

			trim = vehicle_doc.get('trim')

			if trim:
				result_json['trim'] = trim

			price_web = vehicle_doc.get('price_web')

			if price_web:
				result_json['price_web'] = price_web

			interior_360 = vehicle_doc.get('interior_panorama')

			if interior_360:

				result_json['interior_360'] = interior_360

				result_json['interior_player'] = (
					f'https://ivana.sister.tv/models/interior360/'
					f'index.html?header=false&project_id='
					f'{project_id}&vin={vin}&idx_spin=0'
				)

			display_pics = vehicle_doc.get('display_pics')

			if display_pics:
				result_json['display_pics'] = display_pics

			detail_pics = vehicle_doc.get('detail_pics')

			if detail_pics:
				result_json['detail_pics'] = detail_pics

			spin_pics = vehicle_doc.get('spin_pics')

			if spin_pics and spin_pics[0]:

				result_json['spin_pics'] = spin_pics[0]

				result_json['exterior_player'] = (
					f'https://ivana.sister.tv/models/'
					f'exterior360_msk/index.html'
					f'?vin={vin}&project_id={project_id}'
				)

			spin_detail_pics = vehicle_doc.get('spin_detail_pics')

			if spin_detail_pics and spin_detail_pics[0]:
				result_json['spin_detail_pics'] = spin_detail_pics[0]

			spn_spin_pics = vehicle_doc.get('spn_spin_pics')

			if spn_spin_pics and spn_spin_pics[0]:
				result_json['spn_spin_pics'] = spn_spin_pics[0]

			spn_spin_detail_pics = vehicle_doc.get(
				'spn_spin_detail_pics'
			)

			if (
				spn_spin_detail_pics and
				spn_spin_detail_pics[0]
			):
				result_json[
					'spn_spin_detail_pics'
				] = spn_spin_detail_pics[0]

			spinraw_video = vehicle_doc.get('spinraw_video')

			if spinraw_video:
				result_json['spinraw_video'] = spinraw_video

			sp_exterior_data = vehicle_doc.get('sp_exterior_data')

			if sp_exterior_data:
				result_json['sp_exterior_data'] = sp_exterior_data
			else:
				result_json['sp_exterior_data'] = None

			last_spinsmart_execution_date = vehicle_doc.get(
				'last_spinsmart_execution_dt'
			)

			if last_spinsmart_execution_date:

				result_json[
					'last_spinsmart_execution_date'
				] = last_spinsmart_execution_date

			third_party_pics = vehicle_doc.get(
				'third_party_pics'
			)

			if third_party_pics:
				result_json['third_party_pics'] = third_party_pics

			thumbnail_pics = pic2ThumbNail(display_pics)

			phone_pics = pic2ThumbNail(
				display_pics,
				1080
			)

			if thumbnail_pics:

				result_json['thumbnail_pics'] = thumbnail_pics
				result_json['phone_pics'] = phone_pics

			bgr_pics = vehicle_doc.get('bgr_pics')

			if bgr_pics:
				result_json['bgr_pics'] = bgr_pics

			original_before_bgr_pics = vehicle_doc.get(
				'original_before_bgr_pics'
			)

			if original_before_bgr_pics:

				result_json[
					'original_before_bgr_pics'
				] = original_before_bgr_pics

			appVersion = vehicle_doc.get('appVersion')

			result_json['project_id'] = vehicle_doc.get(
				'project_id'
			)

			result_json['appVersion'] = appVersion

			result_json['sp_data'] = vehicle_doc.get(
				'sp_data'
			)

		except Exception as e:

			return Response(
				f'Getting Display Pictures Failed: {e}',
				status=status.HTTP_500_INTERNAL_SERVER_ERROR
			)

		return Response(
			result_json,
			status=status.HTTP_200_OK
		)

def build_interior_urls(interiors, project_id, vin):

	result = []

	for idx, link in enumerate(interiors):

		if '.html' in link:
			result.append(link)

		elif '.jpg' in link:

			ivana_interior_url = (
				BASE_iVanaInteriorUrl
				+ 'header=false'
				+ '&project_id=' + project_id.lower()
				+ '&vin=' + vin.upper()
				+ '&idx_spin=' + str(idx)
			)

			result.append(ivana_interior_url)

	return result

class GetInterior(views.APIView):


	def post(self, request):
		logger.info("POST get_interior")
		date_today = (datetime.datetime.now()+relativedelta(months=-1)).strftime("%Y-%m-%d")
		request_body = request.data
		result = []

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if not vin:
			return Response('Please Enter VIN', status=status.HTTP_400_BAD_REQUEST)
		elif not project_id:
			try:
				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query" : {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
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

				hits = response.get("hits", {}).get("hits", [])

				if not hits:
					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get('_source', {})

				interiors = vehicle_doc.get('interior_panorama')
				if not interiors:
					return Response(
						'No Interior Found',
						status=status.HTTP_404_NOT_FOUND
					)

				project_id = vehicle_doc.get('project_id')
				result.extend(
					build_interior_urls(
						interiors,
						project_id,
						vin
					)
				)
			except Exception as e:
				return Response(f'KBB Getting Interior Failed: {e}',
								status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "ignored":
			# date_today = datetime.datetime.now().strftime("%Y-%m-%d")
			library_id = request_body.get('library_id')
			# library_id = "10011020061817"
			if library_id:
				library_id = removeNonAscii(library_id)
			else:
				return Response(
					'Please Enter Library ID',
					status=status.HTTP_400_BAD_REQUEST
				)
			try:
				# vehicle_doc = ES9.search(index=ES_VEHICLE_INDEX, 
				# 						q="vin:{} AND library_id:{} AND expire_on:[{} TO *]".format(
				# 							vin.lower(), library_id, date_today)
				# 						)['hits']['hits'][0]['_source']
				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query" :{
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
										}
									}
								]
							}
						}
					}
				)

				vehicle_docs = response.get("hits", {}).get("hits", [])

				if not vehicle_docs:
					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)
				vehicle_doc = vehicle_docs[0]['_source']
				# year = vehicle_doc.get('expire_on')
				for doc in vehicle_docs:
					# if doc['_source'].get('expire_on') > year:
					# 	vehicle_doc = doc['_source']
					# 	year = doc['_source'].get('expire_on')
					doc_source = doc.get('_source', {})

					if doc_source.get('interior_panorama') and len(doc_source.get('interior_panorama')) > 0:
						vehicle_doc = doc_source
						break
				interiors = vehicle_doc.get('interior_panorama')


				# interiors = vehicle_doc.get('interior_panorama')
				if not interiors:
					return Response(
						'No Interior Found',
						status=status.HTTP_404_NOT_FOUND
					)

				project_id = vehicle_doc.get('project_id')
				result.extend(
					build_interior_urls(
						interiors,
						project_id,
						vin
					)
				)
			except Exception as e:
				return Response(f'KBB Getting Interior Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				num_of_target = response['hits']['total']['value']
				if num_of_target == 1:
					project_id = response["hits"]["hits"][0]['_source']['project_id']
				elif num_of_target > 1:
					for i in range(num_of_target):
						project_id = response["hits"]["hits"][i]['_source']['project_id']
						if checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Interior Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES9.get(
							index=ES_VEHICLE_INDEX,
							id=vehicle_id
						)

						vehicle_doc = response.get('_source', {})
						interiors = vehicle_doc.get('interior_panorama')
						if not interiors:
							return Response(
								'No Interior Found',
								status=status.HTTP_404_NOT_FOUND
							)
						result.extend(
							build_interior_urls(
								interiors,
								project_id,
								vin
							)
						)

					except Exception as e:
						return Response(f'Getting Interior Failed: {e}.',
										status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				else:
					return Response('Getting Interior Failed: Cannot find the vehicle',
									status=status.HTTP_500_INTERNAL_SERVER_ERROR)
			except Exception as e:
				return Response(f'Getting Interior Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		else:
			vehicle_id = f"{project_id.lower()}-{vin.lower()}"

			'''
				Getting Interior html for pixzero & iVana
			'''
			try:
				response = ES9.get(
					index=ES_VEHICLE_INDEX,
					id=vehicle_id
				)

				vehicle_doc = response.get('_source', {})
				if 'interior_panorama' not in vehicle_doc:
					return Response('No Interior Found', status=status.HTTP_404_NOT_FOUND)
				interiors = vehicle_doc.get('interior_panorama')
				
				if not interiors:
					return Response(
						'No Interior Found',
						status=status.HTTP_404_NOT_FOUND
					)

				result.extend(
					build_interior_urls(
						interiors,
						project_id,
						vin
					)
				)

			except Exception as e:

					if hasattr(e, 'status_code') and e.status_code == 404:
						return Response(
							'No Vehicle Found',
							status=status.HTTP_404_NOT_FOUND
						)

					return Response(
						f'Getting Interior Failed: {e}',
						status=status.HTTP_500_INTERNAL_SERVER_ERROR
					)
		if result:
			return Response(result, status=status.HTTP_200_OK)
		else:
			return Response('No Interior Found', status=status.HTTP_404_NOT_FOUND)

class GetExterior(views.APIView):
	def post(self, request):

		exterior360url = ""
		date_today = (datetime.datetime.now()+relativedelta(months=-1)).strftime("%Y-%m-%d")
		request_body = request.data
		result = []

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')
		player_type = request_body.get('playerType',"")

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)


		if not vin:
			return Response('Please Enter VIN', status=status.HTTP_400_BAD_REQUEST)
		elif not project_id:
			try:
				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
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


				#response = response.body

				hits = response.get("hits", {}).get("hits", [])

				if not hits:
					return Response(
						'No Exterior360 Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get('_source', {})
				exterior = vehicle_doc.get('spin_pics')
				project_id = vehicle_doc.get('project_id')

				if exterior and len(exterior) > 0 and exterior[0] and len(exterior[0]) > 10:
					exterior360url = BASE_exterior360Url + 'vin=' + vin.upper() + '&project_id=' + project_id.lower()
					result.append(exterior360url)
			except Exception as e:
				return Response(f'KBB Getting Exterior360 Failed: {e}',
								status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "ignored":
			try:
				# date_today = datetime.datetime.now().strftime("%Y-%m-%d")
				library_id = request_body.get('library_id')
				# library_id = "10011020061817"
				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)
				# vehicle_doc = ES9.search(
				# 	index=ES_VEHICLE_INDEX,
				# 	
				# 	q="vin:{} AND library_id:{} AND expire_on:[{} TO *]".format(
				# 							vin.lower(), library_id, date_today))['hits']['hits'][0]['_source']
				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
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

				#response = response.body

				vehicle_docs = response.get("hits", {}).get("hits", [])

				if not vehicle_docs:
					return Response(
						'No Exterior360 Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = vehicle_docs[0].get('_source', {})
				# year = vehicle_doc.get('expire_on')
				for doc in vehicle_docs:
					# if doc['_source'].get('expire_on') > year:
					# 	vehicle_doc = doc['_source']
					# 	year = doc['_source'].get('expire_on')
					if doc['_source'].get('spin_pics') and len(doc['_source'].get('spin_pics')) > 0:
						vehicle_doc = doc['_source']
						break
				exterior = vehicle_doc.get('spin_pics')
				project_id = vehicle_doc.get('project_id')

				if exterior and len(exterior) > 0 and exterior[0] and len(exterior[0]) > 10:
					exterior360url = BASE_exterior360Url + 'vin=' + vin.upper() + '&project_id=' + project_id.lower()
					result.append(exterior360url)
			except Exception as e:
				return Response(f'KBB Getting Exterior360 Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				#response = response.body

				num_of_target = response['hits']['total']['value']
				if num_of_target == 1:
					project_id = response["hits"]["hits"][0]['_source']['project_id']
				elif num_of_target > 1:
					for i in range(num_of_target):
						project_id = response["hits"]["hits"][i]['_source']['project_id']
						if checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Exterior360 Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES9.get(index=ES_VEHICLE_INDEX, id=vehicle_id)

						#response = response.body

						vehicle_doc = response.get('_source', {})
						exterior = vehicle_doc.get('spin_pics')
						if exterior and len(exterior) > 0 and exterior[0] and len(exterior[0]) > 10:
							exterior360url = BASE_exterior360Url + 'vin=' + vin.upper() + '&project_id=' + project_id.lower()
							result.append(exterior360url)
					except Exception as e:
						return Response(f'Getting Exterior360 Failed: {e}.',
										status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				else:
					return Response('Getting Exterior360 Failed: Cannot find the vehicle',
									status=status.HTTP_500_INTERNAL_SERVER_ERROR)
			except Exception as e:
				return Response(f'Getting Exterior360 Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		else:
			vehicle_id = f"{project_id.lower()}-{vin.lower()}"

			'''
				Getting Exterior html for pixzero & iVana
			'''
			try:
				response = ES9.get(index=ES_VEHICLE_INDEX, id=vehicle_id)

				#response = response.body

				vehicle_doc = response.get('_source', {})

				if 'spin_pics' not in vehicle_doc:
					return Response('No Exterior360 Found', status=status.HTTP_404_NOT_FOUND)

				exterior = vehicle_doc.get('spin_pics')

				# if isinstance(exterior, list):
				# 	exterior = exterior[0]
				sku_id = ""
				if "sp_data" in vehicle_doc and vehicle_doc['sp_data'] != None:
					sku_id = vehicle_doc.get('sp_data', {}).get('sku_id', "")
				if player_type == "" or sku_id == "":
					if exterior and len(exterior) > 0 and exterior[0] and len(exterior[0]) > 2:
						if vehicle_doc['project_id'] == "jones_ford_062724":
							exterior360url = "https://icontent.sister.tv/embedplayer.html?project_id=" + project_id.lower() + "&vin=" + vin.upper() + "&onlyplayer=1&player_type=9"
						else:
							exterior360url = BASE_exterior360Url + 'vin=' + vin.upper() + '&project_id=' + project_id.lower()
				else:
					if sku_id != "":
						exterior360url = "https://spnplayer.sister.tv/360?project_id="+project_id+"&vin="+vin+"&sku_id="+sku_id+"&data_provider=ez360&player_type=full"
				
				result.append(exterior360url)

			except Exception as e:
				import traceback
				traceback.print_exc()

				error_message = str(e)

				if "404" in error_message:
					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				return Response(
					f'Getting Exterior360 Failed: {error_message}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)
		if result:
			return Response(result, status=status.HTTP_200_OK)
		else:
			return Response('No Exterior360 Found', status=status.HTTP_404_NOT_FOUND)

# Unused
class GetDetailPics(views.APIView):
	def post(self, request):
		request_body = request.data
		result = []

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')
		request_date = request_body.get('date')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if not project_id or not vin:
			return Response('Please Enter Project ID and VIN', status=status.HTTP_400_BAD_REQUEST)
		elif project_id == "ignored":
			try:
				date_today = (datetime.datetime.now()+relativedelta(months=-1)).strftime("%Y-%m-%d")
				library_id = request_body.get('library_id')
				# library_id = "10011020061817"
				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)
				query_must = [
					{
						"term": {
							"vin.keyword": vin.lower()
						}
					},
					{
						"term": {
							"library_id.keyword": library_id
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

				if request_date and request_date != 'any':
					query_must.append({
						"range": {
							"last_modified": {
								"gte": request_date
							}
						}
					})

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": query_must
							}
						}
					}
				)

				hits = response.get("hits", {}).get("hits", [])

				if not hits:
					return Response(
						'No Details or Recently Changed Details Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get('_source', {})
				result = vehicle_doc.get('detail_pics', [])
				if vehicle_doc.get('total') == 0:
					result = []
				else:
					vehicle_doc = vehicle_doc['hits'][0]['_source']
					result = vehicle_doc.get('detail_pics')
			except Exception as e:
				return Response(f'Getting Details Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				query_must = [
					{
						"term": {
							"vin.keyword": vin.lower()
						}
					}
				]

				if request_date and request_date != 'any':
					query_must.append({
						"range": {
							"last_modified": {
								"gte": request_date
							}
						}
					})

				vehicle_doc = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": query_must
							}
						}
					}
				)
				num_of_target = vehicle_doc['hits']['total']['value']
				if num_of_target == 0:
					return Response('No Details or Recently Changed Details Found', status=status.HTTP_404_NOT_FOUND)
				elif num_of_target == 1:
					project_id = response["hits"]["hits"][0]['_source']['project_id']
				else:
					for i in range(num_of_target):
						project_id = response["hits"]["hits"][i]['_source']['project_id']
						if checkIfRollingHillDealer(project_id):
							break
				# else:
				# 	return Response('Getting Details Failed: Cannot find the vehicle',
				# 					status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES9.get(
							index=ES_VEHICLE_INDEX,
							id=vehicle_id
						)

						vehicle_doc = response.get('_source', {})
						result = vehicle_doc.get('detail_pics')
					except Exception as e:
						return Response(f'Getting Details Failed: {e}.',
										status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				else:
					return Response('Getting Details Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
			except Exception as e:
				return Response(f'Getting Details Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		else:
			vehicle_id = f"{project_id.lower()}-{vin.lower()}"
			try:
				response = ES9.get(
					index=ES_VEHICLE_INDEX,
					id=vehicle_id
				)

				vehicle_doc = response.get('_source', {})
				date_comp = False
				if request_date and request_date != 'any' and vehicle_doc.get('last_modified'):
					last_modified_date_str = vehicle_doc['last_modified'].split('T')[0]
					last_modified_date = datetime.datetime.strptime(last_modified_date_str, '%Y-%m-%d').date()
					asked_date = datetime.datetime.strptime(request_date, '%Y-%m-%d').date() - datetime.timedelta(days=1)
					if last_modified_date < asked_date:
						date_comp = True
				if 'detail_pics' not in vehicle_doc or date_comp:
					return Response('No Details or Recently Changed Details Found', status=status.HTTP_404_NOT_FOUND)
				result = vehicle_doc.get('detail_pics')
			except Exception as e:

				if hasattr(e, 'status_code') and e.status_code == 404:
					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				return Response(
					f'Getting Details Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		if result:
			return Response(result, status=status.HTTP_200_OK)
		else:
			return Response('No Details or Recently Changed Details Found', status=status.HTTP_404_NOT_FOUND)

class GetDisplayPics(views.APIView):

	def post(self, request):

		request_body = request.data

		result = []
		vehicle_doc = {}

		project_id = request_body.get('project_id')
		library_id = ""
		vin = request_body.get('vin')
		request_date = request_body.get('date')

		allow_thirdparty = request_body.get(
			'allow_third_party',
			False
		)

		allow_thirdparty_projects = [
			"clyclcjdr_newpreown",
			"clyclkia_newpreown",
			"centralkia_070821",
			"irvingnissan_070621",
			"clyclagp_newpreown",
			"clyclchv_newpreown",
			"arlingtonchryslerjeepdodgeram_100424",
			"courtesynissan_090923",
			"claycooleyford_100424",
			"genesisofmesquite_070423",
			"mydallashyundai_070822",
			"hyundaimesquite_070821",
			"rockwallhyundai_070821",
			"shermanhyundai_082625",
			"terrellhyundai_101322",
			"dallascadillac_120221",
			"claycooleymitsubishiofarlington_070821",
			"claycooleynissan_070821",
			"nissanoflewisville_070821",
			"lewisvillevw_100325",
			"claycooleyvwparkcities_070821",
			"claycooleyvwrichardson_070821",
			"youngchevrolet_070821",
			"carwisegurnee_090825",
			"carwisepeoria_090825"
		]

		allow_thirdparty_libraries = [
			"202509080417"
		]

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if request_date:
			request_date = removeNonAscii(request_date)

		if project_id in allow_thirdparty_projects:
			allow_thirdparty = True

		if library_id in allow_thirdparty_libraries:
			allow_thirdparty = True

		if project_id == "clyclagp_newpreown":

			project_id = "ignored"
			library_id = "20210119_1630"

		if not project_id or not vin:

			return Response(
				'Please Enter Project ID and VIN',
				status=status.HTTP_400_BAD_REQUEST
			)

		elif project_id == "ignored":

			try:

				if library_id != "20210119_1630":
					library_id = request_body.get('library_id')

				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
										}
									}
								]
							}
						}
					}
				)

				vehicle_docs = response.get(
					"hits",
					{}
				).get(
					"hits",
					[]
				)

				if not vehicle_docs:

					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = vehicle_docs[0].get('_source', {})

				year = vehicle_doc.get('expire_on')

				for doc in vehicle_docs:

					doc_source = doc.get('_source', {})

					expire_on = doc_source.get('expire_on')

					if expire_on and expire_on > year:

						vehicle_doc = doc_source
						year = expire_on

			except Exception as e:

				return Response(
					f'KBB Getting Display Pictures Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		elif project_id == "rollinghill_01042020":

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				num_of_target = response['hits']['total']['value']

				if num_of_target == 1:

					project_id = (
						response["hits"]["hits"][0]
						.get('_source', {})
						.get('project_id')
					)

				elif num_of_target > 1:

					for i in range(num_of_target):

						project_id = (
							response["hits"]["hits"][i]
							.get('_source', {})
							.get('project_id')
						)

						if checkIfRollingHillDealer(project_id):
							break

				else:

					return Response(
						'Getting Display Pictures Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

				if checkIfRollingHillDealer(project_id):

					vehicle_id = f"{project_id.lower()}-{vin.lower()}"

					try:

						# response = ES9.get(
						# 	index=ES_VEHICLE_INDEX,
						# 	id=vehicle_id
						# )

						# vehicle_doc = response.get('_source', {})

						response = ES9.search(
							index=ES_VEHICLE_INDEX,
							body={
								"query": {
									"ids": {
										"values": [vehicle_id]
									}
								}
							}
						)

						hits = response.get("hits", {}).get("hits", [])

						if not hits:
							return Response(
								'No Vehicle Found',
								status=status.HTTP_404_NOT_FOUND
							)

						vehicle_doc = hits[0].get("_source", {})

					except Exception as e:

						return Response(
							f'Getting Display Pictures Failed: {e}.',
							status=status.HTTP_500_INTERNAL_SERVER_ERROR
						)

				else:

					return Response(
						'Getting Display Pictures Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

			except Exception as e:

				return Response(
					f'Getting Display Pictures Failed: {e}.',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		else:

			vehicle_id = f"{project_id.lower()}-{vin.lower()}"

			try:

				# response = ES9.get(
				# 	index=ES_VEHICLE_INDEX,
				# 	id=vehicle_id
				# )

				# vehicle_doc = response.get('_source', {})

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"ids": {
								"values": [vehicle_id]
							}
						}
					}
				)

				hits = response.get("hits", {}).get("hits", [])

				if not hits:
					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})

			except Exception as e:

				try:

					if e.status_code == 404:

						return Response(
							'No Vehicle Found',
							status=status.HTTP_404_NOT_FOUND
						)

					return Response(
						f'By project id Getting Display Pictures Failed ES error {e}',
						status=status.HTTP_500_INTERNAL_SERVER_ERROR
					)

				except Exception:

					return Response(
						'By project id Getting Display Pictures Failed',
						status=status.HTTP_500_INTERNAL_SERVER_ERROR
					)

		if not vehicle_doc:

			return Response(
				'No Display Pictures Found',
				status=status.HTTP_404_NOT_FOUND
			)

		date_comp = False

		if (
			request_date and
			request_date != 'any' and
			vehicle_doc.get('last_modified')
		):

			last_modified_date_str = (
				vehicle_doc['last_modified']
				.split('T')[0]
			)

			last_modified_date = datetime.datetime.strptime(
				last_modified_date_str,
				'%Y-%m-%d'
			).date()

			asked_date = (
				datetime.datetime.strptime(
					request_date,
					'%Y-%m-%d'
				).date()
				-
				datetime.timedelta(days=1)
			)

			if last_modified_date < asked_date:
				date_comp = True

		if (
			'display_pics' not in vehicle_doc
			or date_comp
		):

			if allow_thirdparty in [True, "True"]:

				result = vehicle_doc.get('third_party_pics')

				if result:

					return Response(
						result,
						status=status.HTTP_200_OK
					)

				return Response(
					'No Display Pictures Found',
					status=status.HTTP_404_NOT_FOUND
				)

			return Response(
				'No Display Pictures or Recently Changed Display Pictures Found',
				status=status.HTTP_404_NOT_FOUND
			)

		result = vehicle_doc.get('display_pics')

		if (
			result and
			vehicle_doc.get('is_publishable', "") is False
		):

			return Response(
				'Vehicle is not publishable',
				status=status.HTTP_404_NOT_FOUND
			)

		if result:

			return Response(
				result,
				status=status.HTTP_200_OK
			)

		if allow_thirdparty in [True, "True"]:

			result = vehicle_doc.get('third_party_pics')

			if result:

				return Response(
					result,
					status=status.HTTP_200_OK
				)

		return Response(
			'No Display Pictures Found',
			status=status.HTTP_404_NOT_FOUND
		)

class GetDisplayPics2(views.APIView):

	def get(self, request):

		request_body = request.data

		result = []
		vehicle_doc = {}

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')
		request_date = request_body.get('date')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if request_date:
			request_date = removeNonAscii(request_date)

		if not project_id or not vin:

			return Response(
				'Please Enter Project ID and VIN',
				status=status.HTTP_400_BAD_REQUEST
			)

		elif project_id == "ignored":

			try:

				library_id = request_body.get('library_id')

				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
										}
									}
								]
							}
						}
					}
				)

				vehicle_docs = response.get(
					'hits',
					{}
				).get(
					'hits',
					[]
				)

				if not vehicle_docs:

					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = vehicle_docs[0].get('_source', {})

				year = vehicle_doc.get('expire_on')

				for doc in vehicle_docs:

					doc_source = doc.get('_source', {})

					expire_on = doc_source.get('expire_on')

					if expire_on and expire_on > year:

						vehicle_doc = doc_source
						year = expire_on

			except Exception as e:

				return Response(
					f'KBB Getting Display Pictures Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		elif project_id == "rollinghill_01042020":

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				num_of_target = response['hits']['total']['value']

				if num_of_target == 1:

					project_id = (
						response["hits"]["hits"][0]
						.get('_source', {})
						.get('project_id')
					)

				elif num_of_target > 1:

					for i in range(num_of_target):

						project_id = (
							response["hits"]["hits"][i]
							.get('_source', {})
							.get('project_id')
						)

						if checkIfRollingHillDealer(project_id):
							break

				else:

					return Response(
						'Getting Display Pictures Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

				if checkIfRollingHillDealer(project_id):

					vehicle_id = f"{project_id.lower()}-{vin.lower()}"

					try:

						# response = ES9.get(
						# 	index=ES_VEHICLE_INDEX,
						# 	id=vehicle_id
						# )

						# vehicle_doc = response.get('_source', {})

						response = ES9.search(
							index=ES_VEHICLE_INDEX,
							body={
								"query": {
									"ids": {
										"values": [vehicle_id]
									}
								}
							}
						)

						hits = response.get("hits", {}).get("hits", [])

						if not hits:
							return Response(
								'No Vehicle Found',
								status=status.HTTP_404_NOT_FOUND
							)

						vehicle_doc = hits[0].get("_source", {})


					except Exception as e:

						return Response(
							f'Getting Display Pictures Failed: {e}.',
							status=status.HTTP_500_INTERNAL_SERVER_ERROR
						)

				else:

					return Response(
						'Getting Display Pictures Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

			except Exception as e:

				return Response(
					f'Getting Display Pictures Failed: {e}.',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		else:

			vehicle_id = f"{project_id.lower()}-{vin.lower()}"

			try:

				response = ES9.get(
					index=ES_VEHICLE_INDEX,
					id=vehicle_id
				)

				vehicle_doc = response.get('_source', {})

			except Exception as e:

				try:

					if e.status_code == 404:

						return Response(
							'No Vehicle Found',
							status=status.HTTP_404_NOT_FOUND
						)

					else:

						return Response(
							'Getting Display Pictures Failed',
							status=status.HTTP_500_INTERNAL_SERVER_ERROR
						)

				except Exception:

					return Response(
						'Getting Display Pictures Failed',
						status=status.HTTP_500_INTERNAL_SERVER_ERROR
					)

		if not vehicle_doc:

			return Response(
				'No Display Pictures Found',
				status=status.HTTP_404_NOT_FOUND
			)

		date_comp = False

		if (
			request_date and
			request_date != 'any' and
			vehicle_doc.get('last_modified')
		):

			last_modified_date_str = (
				vehicle_doc['last_modified']
				.split('T')[0]
			)

			last_modified_date = datetime.datetime.strptime(
				last_modified_date_str,
				'%Y-%m-%d'
			).date()

			asked_date = (
				datetime.datetime.strptime(
					request_date,
					'%Y-%m-%d'
				).date()
				-
				datetime.timedelta(days=1)
			)

			if last_modified_date < asked_date:
				date_comp = True

		if (
			'display_pics' not in vehicle_doc
			or date_comp
		):

			return Response(
				'No Display Pictures or Recently Changed Display Pictures Found',
				status=status.HTTP_404_NOT_FOUND
			)

		result = vehicle_doc.get('display_pics')

		if result:

			return Response(
				result,
				status=status.HTTP_200_OK
			)

		return Response(
			'No Display Pictures Found',
			status=status.HTTP_404_NOT_FOUND
		)

class GetProjectDisplayPics(views.APIView):

	def post(self, request):

		request_body = request.data

		project_id = request_body.get('project_id')
		vins = request_body.get('vins', [])
		library_id = request_body.get('library_id', 'ignored')

		if project_id:
			project_id = removeNonAscii(project_id)

		if not project_id:

			return Response(
				'Please Enter Project ID',
				status=status.HTTP_400_BAD_REQUEST
			)

		try:

			get_display_pics = ProjectData(
				project_id=project_id,
				pic_type='display_pics',
				vins=vins,
				library_id=library_id
			)

			resp = get_display_pics.get_display_pics()
		

			return Response(
				resp,
				status=status.HTTP_200_OK
			)

		except Exception as e:

			return Response(
				f'Getting Project Display Pics Failed: {e}',
				status=status.HTTP_500_INTERNAL_SERVER_ERROR
			)

	def get(self, request):

		try:

			project_id = request.GET.get('projectId')

			if project_id:
				project_id = removeNonAscii(project_id)

			if not project_id:

				return Response(
					'Please Enter Project ID',
					status=status.HTTP_400_BAD_REQUEST
				)

			get_display_pics = ProjectData(
				project_id=project_id,
				pic_type='display_pics'
			)

			resp = get_display_pics.get_display_pics()

			return Response(
				resp,
				status=status.HTTP_200_OK
			)

		except Exception as e:

			return Response(
				f'Getting Project Display Pics Failed: {e}',
				status=status.HTTP_500_INTERNAL_SERVER_ERROR
			)

class GetDisplayPicsWithCustomHeight(views.APIView):

	def post(self, request):

		request_body = request.data

		project_id = request_body.get('project_id')
		height = request_body.get('h')

		if project_id:
			project_id = removeNonAscii(project_id)

		if not project_id:

			return Response(
				'Please Enter Project ID',
				status=status.HTTP_400_BAD_REQUEST
			)

		try:

			get_display_pics = ProjectDataCustom(
				project_id=project_id,
				height=height,
				pic_type='display_pics'
			)

			resp = get_display_pics.get_pics_w_custom_height()

			return Response(
				resp,
				status=status.HTTP_200_OK
			)

		except Exception as e:

			return Response(
				f'Getting Project Display Pics Failed: {e}',
				status=status.HTTP_500_INTERNAL_SERVER_ERROR
			)

	def get(self, request):

		try:

			project_id = request.GET.get('projectId')
			height = request.GET.get('h')

			if project_id:
				project_id = removeNonAscii(project_id)

			if not project_id:

				return Response(
					'Please Enter Project ID',
					status=status.HTTP_400_BAD_REQUEST
				)

			get_display_pics = ProjectDataCustom(
				project_id=project_id,
				height=height,
				pic_type='display_pics'
			)

			resp = get_display_pics.get_pics_w_custom_height()

			return Response(
				resp,
				status=status.HTTP_200_OK
			)

		except Exception as e:

			return Response(
				f'Getting Project Display Pics Failed: {e}',
				status=status.HTTP_500_INTERNAL_SERVER_ERROR
			)

class GetProjectVehicleInfo(views.APIView):

	def post(self, request):

		request_body = request.data

		project_id = request_body.get('project_id')

		if project_id:
			project_id = removeNonAscii(project_id)

		if not project_id:

			return Response(
				'Please Enter Project ID',
				status=status.HTTP_400_BAD_REQUEST
			)

		try:

			get_display_pics = ProjectData(
				project_id=project_id,
				pic_type='display_pics'
			)

			resp = get_display_pics.get_vehicles_attributes()
			
			return Response(
				resp,
				status=status.HTTP_200_OK
			)

		except Exception as e:

			return Response(
				f'Getting Project Vehicle Info Failed: {e}',
				status=status.HTTP_500_INTERNAL_SERVER_ERROR
			)

class GetPicsPlayer(views.APIView):

	def post(self, request):

		request_body = request.data
		result = []

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		galleryMode = request_body.get('galleryMode')

		if not project_id or not vin:

			return Response(
				'Please Enter Project ID and VIN',
				status=status.HTTP_400_BAD_REQUEST
			)

		elif project_id == "ignored":

			try:

				date_today = (
					datetime.datetime.now() +
					relativedelta(months=-1)
				).strftime("%Y-%m-%d")

				library_id = request_body.get('library_id')

				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
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

				hits = response.get("hits", {}).get("hits", [])

				if not hits:

					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get('_source', {})

				project_id = vehicle_doc.get('project_id')

			except Exception as e:

				return Response(
					f'KBB Getting Player Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		elif project_id == "rollinghill_01042020":

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				num_of_target = response['hits']['total']['value']

				if num_of_target == 1:

					project_id = (
						response["hits"]["hits"][0]
						.get('_source', {})
						.get('project_id')
					)

				elif num_of_target > 1:

					for i in range(num_of_target):

						project_id = (
							response["hits"]["hits"][i]
							.get('_source', {})
							.get('project_id')
						)

						if checkIfRollingHillDealer(project_id):
							break

				else:

					return Response(
						'Getting Player Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

				if not checkIfRollingHillDealer(project_id):

					return Response(
						'Getting Player Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

			except Exception as e:

				return Response(
					f'Getting Player Failed: {e}.',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		if galleryMode == 'bar':

			playerUrl = (
				f'https://ivana.sister.tv/models/picture_player/'
				f'index.html?projectid={project_id}'
				f'&vin={vin}&galleryMode=bar'
			)

		else:

			playerUrl = (
				f'https://ivana.sister.tv/models/picture_player/'
				f'index.html?projectid={project_id}'
				f'&vin={vin}'
			)

		result.append(playerUrl)

		return Response(result, status=status.HTTP_200_OK)

class GetVideos(views.APIView):
	def post(self, request):
		vehicle_doc = {}
		request_body = request.data
		result = []

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if not project_id or not vin:
			return Response('Please Enter Project ID and VIN', status=status.HTTP_400_BAD_REQUEST)
		elif project_id == "ignored":
			try:
				date_today = (datetime.datetime.now()+relativedelta(months=-1)).strftime("%Y-%m-%d")
				library_id = request_body.get('library_id')
				# library_id = "10011020061817"
				library_id = removeNonAscii(library_id)
				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
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


				hits = response.get("hits", {}).get("hits", [])

				if not hits:
					return Response(
						'No Video Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get('_source', {})

				fullmo_sis = vehicle_doc.get('fullmo_sis')

			except Exception as e:
				return Response(f'KBB Getting Video Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				# vehicle_doc = ES9.search(index=ES_VEHICLE_INDEX,  q=f"vin:{vin}")
				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)


				vehicle_doc = response
				num_of_target = response['hits']['total']['value']
				if num_of_target == 1:
					project_id = response["hits"]["hits"][0]['_source']['project_id']
				elif num_of_target > 1:
					for i in range(num_of_target):
						project_id = response["hits"]["hits"][i]['_source']['project_id']
						if checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Video Failed: Cannot find the vehicle',
									status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						# vehicle_doc = ES.get(index=ES_VEHICLE_INDEX,  id=vehicle_id)['_source']
						response = ES9.get(index=ES_VEHICLE_INDEX, id=vehicle_id)


						vehicle_doc = response.get('_source', {})
						fullmo_sis = vehicle_doc.get('fullmo_sis', [])
					except Exception as e:
						return Response(f'Getting Video Failed: {e}.',
										status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				else:
					return Response('Getting Video Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
			except Exception as e:
				return Response(f'Getting Player Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		else:
			vehicle_id = f"{project_id.lower()}-{vin.lower()}"
			try:
				response = ES9.get(
					index=ES_VEHICLE_INDEX,
					id=vehicle_id
				)

				vehicle_doc = response.get('_source', {})
				fullmo_sis = vehicle_doc.get('fullmo_sis')
			except Exception as e:
				return Response(f'Getting Video Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		if fullmo_sis:
			result.append(fullmo_sis)

		try:
			pic2vid = vehicle_doc.get('pic2vid_en_US', [])
		except Exception as e:
			return Response(f'Getting Video Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

		if pic2vid:

			if isinstance(pic2vid, str):

				if pic2vid.lower().startswith("http:"):
					pic2vid = f"https:{pic2vid[5:]}"

			elif isinstance(pic2vid, list):

				pic2vid = [
					f"https:{url[5:]}" if isinstance(url, str) and url.lower().startswith("http:")
					else url
					for url in pic2vid
				]

			result.append(pic2vid)

		if result:
			return Response(result, status=status.HTTP_200_OK)
		else:
			return Response('No Video Found', status=status.HTTP_404_NOT_FOUND)

class GetThumbnailPicsTest(views.APIView):

	def post(self, request):

		request_body = request.data

		result = []
		vehicle_doc = {}

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')
		target_height = request_body.get('h')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if not target_height:
			target_height = DEFAULT_TEST_THUMBNAIL_HEIGHT

		if not project_id or not vin:

			return Response(
				'Please Enter Project ID and VIN',
				status=status.HTTP_400_BAD_REQUEST
			)

		elif project_id == "ignored":

			try:

				library_id = request_body.get('library_id')

				if not library_id:

					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)

				library_id = removeNonAscii(library_id)

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"size": ES_MAX_RESULT_SIZE,
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
										}
									}
								]
							}
						}
					}
				)

				hits = response.get("hits", {}).get("hits", [])

				if not hits:

					return Response(
						'No Vehicle Found',
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get('_source', {})

				year = vehicle_doc.get('expire_on')

				for doc in hits:

					doc_source = doc.get('_source', {})

					expire_on = doc_source.get('expire_on')

					if expire_on and expire_on > year:

						vehicle_doc = doc_source
						year = expire_on

			except Exception as e:

				traceback.print_exc()

				return Response(
					f'Getting Display Pictures Failed: {e}',
					status=status.HTTP_404_NOT_FOUND
				)

		elif project_id == "rollinghill_01042020":

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				num_of_target = response.get(
					'hits',
					{}
				).get(
					'total',
					{}
				).get(
					'value',
					0
				)

				if num_of_target == 1:

					project_id = response["hits"]["hits"][0].get(
						'_source',
						{}
					).get(
						'project_id'
					)

				elif num_of_target > 1:

					for each in response["hits"]["hits"]:

						source = each.get('_source', {})

						project_id = source.get('project_id')

						if checkIfRollingHillDealer(project_id):
							break

				else:

					return Response(
						'Getting Display Pictures Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

				if checkIfRollingHillDealer(project_id):

					vehicle_id = (
						project_id.lower() +
						'-' +
						vin.lower()
					)

					response = ES9.get(
						index=ES_VEHICLE_INDEX,
						id=vehicle_id
					)

					vehicle_doc = response.get('_source', {})

				else:

					return Response(
						'Getting Display Pictures Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

			except Exception as e:

				traceback.print_exc()

				return Response(
					f'Getting Display Pictures Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		else:

			try:

				vehicle_id = (
					project_id.lower() +
					'-' +
					vin.lower()
				)

				response = ES9.get(
					index=ES_VEHICLE_INDEX,
					id=vehicle_id
				)

				vehicle_doc = response.get('_source', {})

			except Exception as e:

				traceback.print_exc()

				try:

					if e.status_code == 404:

						return Response(
							'No Vehicle Found',
							status=status.HTTP_404_NOT_FOUND
						)

				except Exception:
					pass

				return Response(
					'Getting Display Pictures Failed',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		if not vehicle_doc:

			return Response(
				'No Display Pictures Found',
				status=status.HTTP_404_NOT_FOUND
			)

		if 'display_pics' not in vehicle_doc:

			return Response(
				'No Display Pictures Found',
				status=status.HTTP_404_NOT_FOUND
			)

		cur_display_pics = vehicle_doc.get(
			'display_pics',
			[]
		)

		result = pic2ThumbNail(
			cur_display_pics,
			target_height
		)

		if result:

			return Response(
				result,
				status=status.HTTP_200_OK
			)

		return Response(
			'No Display Pictures Found',
			status=status.HTTP_404_NOT_FOUND
		)

class GetThumbnailPics(views.APIView):

	def post(self, request):

		request_body = request.data

		result = []
		vehicle_doc = {}

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')
		target_height = request_body.get('h')
		request_date = request_body.get('date')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if request_date:
			request_date = removeNonAscii(request_date)

		if not target_height:
			target_height = DEFAULT_THUMBNAIL_HEIGHT

		if not project_id or not vin:

			return Response(
				'Please Enter Project ID and VIN',
				status=status.HTTP_400_BAD_REQUEST
			)

		elif project_id == "ignored":

			try:

				library_id = request_body.get('library_id')

				if not library_id:

					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)

				library_id = removeNonAscii(library_id)

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"size": ES_MAX_RESULT_SIZE,
						"query": {
							"bool": {
								"must": [
									{
										"term": {
											"vin.keyword": vin.lower()
										}
									},
									{
										"term": {
											"library_id.keyword": library_id
										}
									}
								]
							}
						}
					}
				)

				hits = response.get("hits", {}).get("hits", [])

				for each in hits:

					source = each.get('_source', {})

					display_pics = source.get('display_pics', [])

					if display_pics:

						vehicle_doc = source
						break

			except Exception as e:

				traceback.print_exc()

				return Response(
					f'Getting Display Pictures Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		elif project_id == "rollinghill_01042020":

			try:

				response = ES9.search(
					index=ES_VEHICLE_INDEX,
					body={
						"query": {
							"term": {
								"vin.keyword": vin.lower()
							}
						}
					}
				)

				num_of_target = response.get(
					'hits',
					{}
				).get(
					'total',
					{}
				).get(
					'value',
					0
				)

				if num_of_target == 1:

					project_id = response["hits"]["hits"][0].get(
						'_source',
						{}
					).get(
						'project_id'
					)

				elif num_of_target > 1:

					for each in response["hits"]["hits"]:

						source = each.get('_source', {})

						project_id = source.get('project_id')

						if checkIfRollingHillDealer(project_id):
							break

				else:

					return Response(
						'Getting Display Pictures Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

				if checkIfRollingHillDealer(project_id):

					vehicle_id = (
						project_id.lower() +
						'-' +
						vin.lower()
					)

					response = ES9.get(
						index=ES_VEHICLE_INDEX,
						id=vehicle_id
					)

					vehicle_doc = response.get('_source', {})

				else:

					return Response(
						'Getting Display Pictures Failed: Cannot find the vehicle',
						status=status.HTTP_404_NOT_FOUND
					)

			except Exception as e:

				traceback.print_exc()

				return Response(
					f'Getting Display Pictures Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		else:

			try:

				vehicle_id = (
					project_id.lower() +
					'-' +
					vin.lower()
				)

				response = ES9.get(
					index=ES_VEHICLE_INDEX,
					id=vehicle_id
				)

				vehicle_doc = response.get('_source', {})

			except Exception as e:

				traceback.print_exc()

				try:

					if e.status_code == 404:

						return Response(
							'No Vehicle Found',
							status=status.HTTP_404_NOT_FOUND
						)

				except Exception:
					pass

				return Response(
					'Getting Display Pictures Failed',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)

		if not vehicle_doc:

			return Response(
				'No Display Pictures Found',
				status=status.HTTP_404_NOT_FOUND
			)

		date_comp = False

		if (
			request_date and
			request_date != 'any' and
			vehicle_doc.get('last_modified')
		):

			last_modified_date_str = (
				vehicle_doc['last_modified']
				.split('T')[0]
			)

			last_modified_date = datetime.datetime.strptime(
				last_modified_date_str,
				'%Y-%m-%d'
			).date()

			asked_date = (
				datetime.datetime.strptime(
					request_date,
					'%Y-%m-%d'
				).date()
				-
				datetime.timedelta(days=1)
			)

			if last_modified_date < asked_date:
				date_comp = True

		if (
			'display_pics' not in vehicle_doc
			or date_comp
		):

			return Response(
				'No Display Pictures or Recently Changed Display Pictures Found',
				status=status.HTTP_404_NOT_FOUND
			)

		cur_display_pics = vehicle_doc.get(
			'display_pics',
			[]
		)

		result = pic2ThumbNail(
			cur_display_pics,
			target_height
		)

		if result:

			return Response(
				result,
				status=status.HTTP_200_OK
			)

		return Response(
			'No Display Pictures or Recently Changed Display Pictures Found',
			status=status.HTTP_404_NOT_FOUND
		)

class ProjectData:

	def __init__(
		self,
		project_id,
		pic_type='display_pics',
		vins=None,
		library_id="ignored"
	):

		self.project_id = project_id
		self.library_id = library_id
		self.vins = vins or []
		self.pic_type = pic_type
		self.date_today = datetime.datetime.now().strftime("%Y-%m-%d")

	def get_display_pics(self):

		res = {
			'project_id': self.project_id,
			'vehicles': []
		}

		try:

			must_conditions = [
				{
					"range": {
						"expire_on": {
							"gte": self.date_today
						}
					}
				}
			]

			if self.vins:

				must_conditions.append({
					"term": {
						"library_id.keyword": self.library_id
					}
				})

				must_conditions.append({
					"terms": {
						"vin.keyword": [
							vin.lower() for vin in self.vins
						]
					}
				})

			else:

				must_conditions.append({
					"term": {
						"project_id.keyword": self.project_id
					}
				})
				
			vehicle_docs = ES9.search(
				index=ES_VEHICLE_INDEX,
				body={
					"size": ES_MAX_RESULT_SIZE,
					"query": {
						"bool": {
							"must": must_conditions
						}
					}
				}
			)

			hits = vehicle_docs.get("hits", {}).get("hits", [])

			for vehicle_doc in hits:

				source = vehicle_doc.get('_source', {})

				pics = source.get(self.pic_type, [])

				if pics:

					res['vehicles'].append({
						'vin': source.get('vin'),
						'display_pics': pics,
						'modified_date': source.get('last_modified')
					})

		except Exception as e:

			traceback.print_exc()

			email_alert = email_alert_EZ360()

			email_alert.send(
				os.path.basename(__file__),
				f'ID: {self.project_id}, type: {self.pic_type}, Error: {e}'
			)

		return res

	def get_vehicles_attributes(self):

		res = {
			'project_id': self.project_id,
			'vehicles': []
		}

		try:

			vehicle_docs = ES9.search(
				index=ES_VEHICLE_INDEX,
				body={
					"size": 10,
					"query": {
						"bool": {
							"must": [
								{
									"term": {
										"project_id.keyword": self.project_id
									}
								},
								{
									"range": {
										"expire_on": {
											"gte": self.date_today
										}
									}
								}
							]
						}
					}
				}
			)

			hits = vehicle_docs.get("hits", {}).get("hits", [])

			for vehicle_doc in hits:

				source = vehicle_doc.get('_source', {})

				pics = source.get(self.pic_type, [])

				if pics:

					res['vehicles'].append({

						'VIN': source.get('vin'),

						'Mileage': source.get('miles'),

						'Fuel Type': source.get('fuel_type'),

						'Transmission': source.get('transmission'),

						'Condition': source.get('new_used'),

						'Engine': source.get('engine'),

						'Price': source.get('price_web'),

						'City MPG': source.get('city_mpg'),

						'Highway MPG': source.get('hwy_mpg'),

						'Features and Options': source.get('options'),

						'Vehicle Overview': source.get('description'),

						'Location': {
							'dealer_address':
								f"{source.get('dealer_address1', '')} "
								f"{source.get('dealer_address2', '')}".strip(),

							'dealer_zip': source.get('dealer_zip'),

							'dealer_city': source.get('dealer_city'),

							'dealer_state': source.get('dealer_state'),
						},

						'drivetrain': source.get('drivetrain'),

						'Modified_date': source.get('last_modified'),

						'interior_color': source.get('int_color'),

						'exterior_color': source.get('ext_color'),

						'trim': source.get('trim'),

						'make': source.get('make'),

						'model': source.get('model'),

						'year': source.get('year'),

						'door': source.get('door'),

						'is_certified': ''
					})

		except Exception as e:

			traceback.print_exc()

			email_alert = email_alert_EZ360()

			email_alert.send(
				os.path.basename(__file__),
				f'ID: {self.project_id}, type: {self.pic_type}, Error: {e}'
			)

		return res

class ProjectDataCustom:

	def __init__(self, project_id, height, pic_type='display_pics'):

		self.project_id = project_id
		self.pic_type = pic_type
		self.height = height
		self.date_today = datetime.datetime.now().strftime("%Y-%m-%d")

	def get_pics_w_custom_height(self):

		res = {
			'project_id': self.project_id,
			'vehicles': []
		}

		try:

			vehicle_docs = ES9.search(
				index=ES_VEHICLE_INDEX,
				body={
					"size": ES_MAX_RESULT_SIZE,
					"query": {
						"bool": {
							"must": [
								{
									"term": {
										"project_id.keyword": self.project_id
									}
								},
								{
									"range": {
										"expire_on": {
											"gte": self.date_today
										}
									}
								}
							]
						}
					}
				}
			)

			hits = vehicle_docs.get("hits", {}).get("hits", [])

			for vehicle_doc in hits:

				source = vehicle_doc.get('_source', {})

				pics = source.get(self.pic_type, [])

				if pics:

					res['vehicles'].append({
						'vin': source.get('vin'),
						'display_pics': pic2ThumbNail(
							pics,
							self.height
						),
						'modified_date': source.get('last_modified')
					})

		except Exception as e:

			traceback.print_exc()

			email_alert = email_alert_EZ360()

			email_alert.send(
				os.path.basename(__file__),
				'ID: {}, type: {}, Error: {}'.format(
					self.project_id,
					self.pic_type,
					e
				)
			)

		return res

class GetBGREDPics(views.APIView):
	def get(self, request):
		vehicle_doc = {}
		project_id = request.GET.get('projectId')
		vin = request.GET.get('vin')
		if project_id and vin:
			project_id = removeNonAscii(project_id)
			vin = removeNonAscii(vin)
			if project_id == "ignored":
				try:
					# date_today = datetime.datetime.now().strftime("%Y-%m-%d")
					library_id = request.GET.get('libraryId')
					if library_id:
						library_id = removeNonAscii(library_id)

						response = ES9.search(
							index=ES_VEHICLE_INDEX,
							body={
								"query": {
									"bool": {
										"must": [
											{
												"term": {
													"vin.keyword": vin.lower()
												}
											},
											{
												"term": {
													"library_id.keyword": library_id
												}
											}
										]
									}
								}
							}
						)

						

						vehicle_docs = response.get("hits", {}).get("hits", [])

						if not vehicle_docs:
							return Response(
								'No Vehicle Found',
								status=status.HTTP_404_NOT_FOUND
							)

						vehicle_doc = vehicle_docs[0].get('_source', {})
						year = vehicle_doc.get('expire_on')
						for doc in vehicle_docs:

							doc_source = doc.get('_source', {})

							expire_on = doc_source.get('expire_on')

							if expire_on and expire_on > year:

								vehicle_doc = doc_source
								year = expire_on
					else:
						return Response('Need library id', status=status.HTTP_400_BAD_REQUEST)

				# result = vehicle_doc.get('display_pics')
				except Exception as e:
					return Response(f'KBB Getting Pictures Failed: {e}',
									status=status.HTTP_500_INTERNAL_SERVER_ERROR)

			else:
				vehicle_id = f"{project_id.lower()}-{vin.lower()}"
				try:
					response = ES9.get(index=ES_VEHICLE_INDEX, id=vehicle_id)


					vehicle_doc = response.get('_source', {})
				# result = vehicle_doc.get('display_pics')
				except Exception as e:
					import traceback
					traceback.print_exc()

					return Response(
						f'Getting Display Pictures Failed: {str(e)}',
						status=status.HTTP_500_INTERNAL_SERVER_ERROR
					)

			if not vehicle_doc:
				return Response('No  Pictures Found', status=status.HTTP_404_NOT_FOUND)
			else:
				if 'spn_bgred_pics' not in vehicle_doc:
					return Response('No Pictures or Recently Changed Pictures Found',
									status=status.HTTP_404_NOT_FOUND)
				else:
					result = vehicle_doc.get('spn_bgred_pics')
					if result:
						return Response(result, status=status.HTTP_200_OK)
					else:
						return Response('No  Pictures Found', status=status.HTTP_404_NOT_FOUND)
		else:
			return Response("Need more parameter to extract data", status=status.HTTP_400_BAD_REQUEST)

if __name__ == '__main__':
	get_display_pics = ProjectDataCustom(project_id='jimgauthier_kia_0321', height=300, type='display_pics')
	resp = get_display_pics.get_pics_w_custom_height()
	print(resp)
