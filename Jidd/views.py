import datetime
import sys
import os
from dotenv import load_dotenv
load_dotenv()
from rest_framework import views, status
from rest_framework.response import Response

from elasticsearch import Elasticsearch
#from . import email_alert_EZ360
import string


from dotenv import load_dotenv
import os

load_dotenv()
ES_VEHICLE_INDEX = "vehicles2_v9"
ES_SECURE_ENDPOINT = os.getenv("ES_SECURE_ENDPOINT")

ES = Elasticsearch(
    ES_SECURE_ENDPOINT,
    verify_certs=False,
    request_timeout=30
)

BASE_iVanaInteriorUrl = 'https://ivana.sister.tv/models/interior360/index.html?'
BASE_exterior360Url = 'https://ivana.sister.tv/models/exterior360/index.html?'


def removeNonAscii(origin_string):

	if not origin_string:
		return ""

	printable = set(string.printable)

	return ''.join(
		filter(lambda x: x in printable, str(origin_string))
	)

def checkIfRollingHillDealer(project_id):
	return project_id == "rollinghill_honda_01042020" or project_id == "rollinghill_nissan_01042020" or \
		   project_id == "rollinghill_toyota_01042020" or project_id == "rollinghill_used_01042020"

class GetPlayer(views.APIView):
	def post(self, request):
		request_body = request.data
		result_json = {}

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if not project_id or not vin:
			return Response('Please Enter Project ID and VIN', status=status.HTTP_400_BAD_REQUEST)
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
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})
				ret_project_id = vehicle_doc.get("project_id")
				if not ret_project_id:
					return Response(
						"Project ID missing",
						status=status.HTTP_404_NOT_FOUND
					)
				ret_project_id = removeNonAscii(ret_project_id)
				player_url = f'https://player.sister.tv/?project_id={ret_project_id}&vin={vin.lower()}'
				result = []
				result.append(player_url)
				return Response(result, status=status.HTTP_200_OK)
			except Exception as e:
				# import traceback

				# traceback.print_exc()

				# exc_type, exc_obj, exc_tb = sys.exc_info()

				# print("========== FULL DEBUG ==========")
				# print("LINE:", exc_tb.tb_lineno)
				# print("ERROR:", repr(e))
				# print("VIN:", vin)
				# print("LIBRARY:", library_id)
				# print("================================")

				return Response(
					f'Getting Player Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)
		else:
			if project_id == "rollinghill_01042020":
				try:
					vehicle_doc = ES.search(index=ES_VEHICLE_INDEX, body={
																"query": {
																	"term": {
																		"vin.keyword": vin.lower()
																	}
																}
															})
					num_of_target = vehicle_doc.get('hits', {}).get('total', {}).get('value', 0)
					if num_of_target == 1:
						hits = vehicle_doc.get("hits", {}).get("hits", [])

						if not hits:
							return Response(
								"No vehicle found",
								status=status.HTTP_404_NOT_FOUND
							)

						project_id = hits[0].get("_source", {}).get("project_id")
					elif num_of_target > 1:

						hits = vehicle_doc.get("hits", {}).get("hits", [])

						if not hits:
							return Response(
								"No vehicle found",
								status=status.HTTP_404_NOT_FOUND
							)

						for hit in hits:

							project_id = hit.get("_source", {}).get("project_id")

							if project_id and checkIfRollingHillDealer(project_id):
								break
					else:
						return Response('Getting Player Failed: Cannot find the vehicle', status=status.HTTP_404_NOT_FOUND)
					if checkIfRollingHillDealer(project_id):
						vehicle_id = f"{project_id.lower()}-{vin.lower()}"
						try:
							result = []
							response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
							vehicle_doc = response.get('_source', {})

							if not vehicle_doc:
								return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)

							player_url = 'https://player.sister.tv/?project_id={}&vin={}'.format(project_id,
																								 vin.lower())

							result.append(player_url)

							return Response(result, status=status.HTTP_200_OK)

						except Exception as e:
							return Response(f'Getting Player Failed: {e}.',
											status=status.HTTP_500_INTERNAL_SERVER_ERROR)
					else:
						return Response('Getting Player Failed: Cannot find the vehicle',
										status=status.HTTP_404_NOT_FOUND)
				except Exception as e:
					return Response(f'Getting Player Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

			else:
				vehicle_id = f"{project_id.lower()}-{vin.lower()}"

				'''
					Varify Player
				'''
				try:

					result = []
					response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
					vehicle_doc = response.get('_source', {})

					if not vehicle_doc:
						return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)

					player_url = f'https://player.sister.tv/?project_id={project_id}&vin={vin.lower()}'

					result.append(player_url)

					return Response(result, status=status.HTTP_200_OK)

				except Exception as e:
					return Response(f'Getting Player Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetAll(views.APIView):
	def post(self, request):
		request_body = request.data
		result_json = {}

		project_id = request_body.get('project_id')
		vin = request_body.get('vin')

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)


		if not project_id or not vin:
			return Response('Please Enter Project ID and VIN', status=status.HTTP_400_BAD_REQUEST)
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
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})
				project_id = removeNonAscii(vehicle_doc.get("project_id"))
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				#email_alert = email_alert_EZ360()
				#email_alert.send(os.path.basename(__file__),
				#				 f'ID: {vin}. Line: {exc_tb.tb_lineno}. Error:{e}')
				return Response(f'Getting All Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				vehicle_doc = ES.search(index=ES_VEHICLE_INDEX, body={
																	"query":{
																		"term": {
																			"vin.keyword": vin.lower()
																		}
																	}
															})
				num_of_target = vehicle_doc.get('hits', {}).get('total', {}).get('value', 0)
				if num_of_target == 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					if not hits:
						return Response(
							"No vehicle found",
							status=status.HTTP_404_NOT_FOUND
						)

					project_id = hits[0].get("_source", {}).get("project_id")
				elif num_of_target > 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					if not hits:
						return Response(
							"No vehicle found",
							status=status.HTTP_404_NOT_FOUND
						)

					for hit in hits:

						project_id = hit.get("_source", {}).get("project_id")

						if project_id and checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting All Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES.get(
							index=ES_VEHICLE_INDEX,
							id=vehicle_id
						)

						vehicle_doc = response.get('_source', {})
						if not vehicle_doc:
							return Response(
								'No Vehicle Found',
								status=status.HTTP_404_NOT_FOUND
							)
					except Exception as e:
						return Response(f'Getting All Failed: {e}.',
										status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				else:
					return Response('Getting All Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
			except Exception as e:
				return Response(f'Getting All Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		else:
			try:
				vehicle_id = f"{project_id.lower()}-{vin.lower()}"
				response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
				vehicle_doc = response.get('_source', {})

				if not vehicle_doc:
					return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				#email_alert = email_alert_EZ360()
				#email_alert.send(os.path.basename(__file__),
				#				 f'ID: {vehicle_id}. Line: {exc_tb.tb_lineno}. Error:{e}')
				return Response(f'Getting All Failed: {e}',
								status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		# vehicle_id = f"{project_id.lower()}-{vin.lower()}"
		try:
			# vehicle_doc = ES.get(index=ES_VEHICLE_INDEX, doc_type='inventory', id=vehicle_id)['_source']

			# TODO players here
			result_json['full_player'] = f'https://player.sister.tv/?project_id={project_id}&vin={vin}'

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

			interior_360 = vehicle_doc.get('interior_panorama')
			if interior_360:
				result_json['interior_360'] = interior_360
				result_json['interior_player'] = f'https://ivana.sister.tv/models/interior360/index.html?header=false&project_id={project_id}&vin={vin}&idx_spin=0'

			display_pics = vehicle_doc.get('display_pics')
			if display_pics and len(display_pics) > 0:
				result_json['display_pics'] = display_pics

			detail_pics = vehicle_doc.get('detail_pics')
			if detail_pics and len(detail_pics) > 0:
				result_json['detail_pics'] = detail_pics

			spin_pics = vehicle_doc.get('spin_pics')
			if (
				spin_pics
				and isinstance(spin_pics, list)
				and len(spin_pics) > 0
				and spin_pics[0]
			):
				result_json['spin_pics'] = spin_pics[0]
				result_json['exterior_player'] = f'https://ivana.sister.tv/models/exterior360/index.html?vin={vin}&project_id={project_id}'

			spin_detail_pics = vehicle_doc.get('spin_detail_pics')
			if (
				spin_detail_pics
				and isinstance(spin_detail_pics, list)
				and len(spin_detail_pics) > 0
				and spin_detail_pics[0]
			):
				result_json['spin_detail_pics'] = spin_detail_pics[0]

			third_party_pics = vehicle_doc.get('third_party_pics')
			if third_party_pics and len(third_party_pics) > 0:
				result_json['third_party_pics'] = third_party_pics

			thumbnail_pics = vehicle_doc.get('thumbnail_pics')
			if thumbnail_pics and len(thumbnail_pics) > 0:
				result_json['thumbnail_pics'] = thumbnail_pics

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			#email_alert = email_alert_EZ360()
			#email_alert.send(os.path.basename(__file__),
							# f'ID: {vehicle_id}. Line: {exc_tb.tb_lineno}. Error:{e}')
			return Response(f'Getting Display Pictures Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		return Response(result_json, status=status.HTTP_200_OK)

class GetInterior(views.APIView):


	def post(self, request):
		date_today = datetime.datetime.now().strftime("%Y-%m-%d")
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
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})

				interiors = vehicle_doc.get('interior_panorama')

				if not interiors:
					return Response(
						'No Interior Found',
						status=status.HTTP_404_NOT_FOUND
					)

				project_id = vehicle_doc.get('project_id')

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

			except Exception as e:
				return Response(
					f'KBB Getting Interior Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})

				interiors = vehicle_doc.get('interior_panorama')
				if not interiors:
					return Response('No Interior Found', status=status.HTTP_404_NOT_FOUND)

				project_id = vehicle_doc.get('project_id')
				for idx, link in enumerate(interiors):
					if '.html' in link:
						result.append(link)
					elif '.jpg' in link:
						ivana_interior_url = BASE_iVanaInteriorUrl + 'header=false' + '&project_id=' + project_id.lower() + '&vin=' + vin.upper() + '&idx_spin=' + str(
							idx)
						result.append(ivana_interior_url)
			except Exception as e:
				return Response(f'KBB Getting Interior Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				vehicle_doc = ES.search(index=ES_VEHICLE_INDEX, body={
																	"query":{
																		"term": {
																			"vin.keyword": vin.lower()
																		}
																	}
																})
				num_of_target = vehicle_doc.get('hits', {}).get('total', {}).get('value', 0)
				if num_of_target == 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					if not hits:
						return Response(
							"No vehicle found",
							status=status.HTTP_404_NOT_FOUND
						)

					project_id = hits[0].get("_source", {}).get("project_id")
				elif num_of_target > 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					for hit in hits:

						project_id = hit.get("_source", {}).get("project_id")

						if project_id and checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Interior Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
						vehicle_doc = response.get('_source', {})

						if not vehicle_doc:
							return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
						interiors = vehicle_doc.get('interior_panorama')
						for idx, link in enumerate(interiors):
							if '.html' in link:
								result.append(link)
							elif '.jpg' in link:
								ivana_interior_url = BASE_iVanaInteriorUrl + 'header=false' + '&project_id=' + project_id.lower() + '&vin=' + vin.upper() + '&idx_spin=' + str(
									idx)
								result.append(ivana_interior_url)

					except Exception as e:
						return Response(f'Getting Interior Failed: {e}.',
										status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				else:
					return Response('Getting Interior Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
			except Exception as e:
				return Response(f'Getting Interior Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		else:
			vehicle_id = f"{project_id.lower()}-{vin.lower()}"

			'''
				Getting Interior html for pixzero & iVana
			'''
			try:
				response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
				vehicle_doc = response.get('_source', {})

				if not vehicle_doc:
					return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
				if 'interior_panorama' not in vehicle_doc:
					return Response('No Interior Found', status=status.HTTP_404_NOT_FOUND)
				interiors = vehicle_doc.get('interior_panorama')

				for idx, link in enumerate(interiors):
					if '.html' in link:
						result.append(link)
					elif '.jpg' in link:
						ivana_interior_url = BASE_iVanaInteriorUrl + 'header=false' + '&project_id=' + project_id.lower() + '&vin=' + vin.upper() + '&idx_spin=' + str(
							idx)
						result.append(ivana_interior_url)

			except Exception as e:
				try:
					if e.status_code == 404:
						return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
					else:
						return Response('Getting Interior Failed', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				except Exception:
					return Response('Getting Interior Failed', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

		if result:
			return Response(result, status=status.HTTP_200_OK)
		else:
			return Response('No Interior Found', status=status.HTTP_404_NOT_FOUND)

class GetExterior(views.APIView):
	def post(self, request):
		print('POST get_exterior360')

		date_today = datetime.datetime.now().strftime("%Y-%m-%d")
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
				response = ES.search(
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
				

				hits = response.get("hits", {}).get("hits", [])

				if not hits:
					return Response(
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})

				exterior = vehicle_doc.get('spin_pics')

				if (
					exterior
					and isinstance(exterior, list)
					and len(exterior) > 0
					and exterior[0]
					and len(exterior[0]) > 10
				):
					project_id = vehicle_doc.get('project_id')

					exterior360url = (
						BASE_exterior360Url
						+ 'vin=' + vin.upper()
						+ '&project_id=' + project_id.lower()
					)

					result.append(exterior360url)

			except Exception as e:
				return Response(
					f'KBB Getting Interior Failed: {e}',
					status=status.HTTP_500_INTERNAL_SERVER_ERROR
				)
		elif project_id == "ignored":
			try:
				date_today = datetime.datetime.now().strftime("%Y-%m-%d")
				library_id = request_body.get('library_id')
				
				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})
				exterior = vehicle_doc.get('spin_pics')
				project_id = vehicle_doc.get('project_id')

				if (
					exterior
					and isinstance(exterior, list)
					and len(exterior) > 0
					and exterior[0]
					and len(exterior[0]) > 10
				):
					exterior360url = BASE_exterior360Url + 'vin=' + vin.upper() + '&project_id=' + project_id.lower()
					result.append(exterior360url)
			except Exception as e:
				return Response(f'KBB Getting Exterior360 Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				vehicle_doc = ES.search(index=ES_VEHICLE_INDEX, body={
																	"query": {
																		"term": {
																			"vin.keyword": vin.lower()
																		}
																	}
																})
				num_of_target = vehicle_doc.get('hits', {}).get('total', {}).get('value', 0)
				if num_of_target == 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					if not hits:
						return Response(
							"No vehicle found",
							status=status.HTTP_404_NOT_FOUND
						)

					project_id = hits[0].get("_source", {}).get("project_id")
				elif num_of_target > 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					for hit in hits:

						project_id = hit.get("_source", {}).get("project_id")

						if project_id and checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Exterior360 Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
						vehicle_doc = response.get('_source', {})

						if not vehicle_doc:
							return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
						exterior = vehicle_doc.get('spin_pics')
						if (
					exterior
					and isinstance(exterior, list)
					and len(exterior) > 0
					and exterior[0]
					and len(exterior[0]) > 10
				):
							exterior360url = BASE_exterior360Url + 'vin=' + vin.upper() + '&project_id=' + project_id.lower()
							result.append(exterior360url)
					except Exception as e:
						return Response(f'Getting Exterior360 Failed: {e}.',
										status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				else:
					return Response('Getting Exterior360 Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
			except Exception as e:
				return Response(f'Getting Exterior360 Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		else:
			vehicle_id = f"{project_id.lower()}-{vin.lower()}"

			'''
				Getting Exterior html for pixzero & iVana
			'''
			try:
				response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
				vehicle_doc = response.get('_source', {})

				if not vehicle_doc:
					return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)

				if 'spin_pics' not in vehicle_doc:
					return Response('No Exterior360 Found', status=status.HTTP_404_NOT_FOUND)

				exterior = vehicle_doc.get('spin_pics')

				# if isinstance(exterior, list):
				# 	exterior = exterior[0]

				if (
					exterior
					and isinstance(exterior, list)
					and len(exterior) > 0
					and exterior[0]
					and len(exterior[0]) > 10
				):
					exterior360url = BASE_exterior360Url + 'vin=' + vin.upper() + '&project_id=' + project_id.lower()
					result.append(exterior360url)

			except Exception as e:
				try:
					if e.status_code == 404:
						return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
					else:
						return Response('Getting Exterior360 Failed', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				except Exception:
					return Response('Getting Exterior360 Failed', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

		if project_id:
			project_id = removeNonAscii(project_id)

		if vin:
			vin = removeNonAscii(vin)

		if not project_id or not vin:
			return Response('Please Enter Project ID and VIN', status=status.HTTP_400_BAD_REQUEST)
		elif project_id == "ignored":
			try:
				date_today = datetime.datetime.now().strftime("%Y-%m-%d")
				library_id = request_body.get('library_id')
				
				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})
				result = vehicle_doc.get('detail_pics')
			except Exception as e:
				return Response(f'KBB Getting Details Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				vehicle_doc = ES.search(index=ES_VEHICLE_INDEX, body={
																	"query":{
																		"term": {
																			"vin.keyword": vin.lower()
																		}
																	}
															})
				num_of_target = vehicle_doc.get('hits', {}).get('total', {}).get('value', 0)
				if num_of_target == 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					if not hits:
						return Response(
							"No vehicle found",
							status=status.HTTP_404_NOT_FOUND
						)

					project_id = hits[0].get("_source", {}).get("project_id")
				elif num_of_target > 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					for hit in hits:

						project_id = hit.get("_source", {}).get("project_id")

						if project_id and checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Details Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
						vehicle_doc = response.get('_source', {})

						if not vehicle_doc:
							return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
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
				response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
				vehicle_doc = response.get('_source', {})

				if not vehicle_doc:
					return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
				if 'detail_pics' not in vehicle_doc:
					return Response('No Details Found', status=status.HTTP_404_NOT_FOUND)
				result = vehicle_doc.get('detail_pics')
			except Exception as e:
				try:
					if e.status_code == 404:
						return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
					else:
						return Response('Getting Details Failed', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				except Exception:
					return Response('Getting Details Failed', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

		if result:
			return Response(result, status=status.HTTP_200_OK)
		else:
			return Response('No Details Found', status=status.HTTP_404_NOT_FOUND)

class GetDisplayPics(views.APIView):
	def post(self, request):
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
				date_today = datetime.datetime.now().strftime("%Y-%m-%d")
				library_id = request_body.get('library_id')
				
				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})
				# result = vehicle_doc.get('display_pics')
			except Exception as e:
				return Response(f'KBB Getting Display Pictures Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				vehicle_doc = ES.search(index=ES_VEHICLE_INDEX, body={
																	"query": {
																		"term": {
																			"vin.keyword": vin.lower()
																		}
																	}
														})
				num_of_target = vehicle_doc.get('hits', {}).get('total', {}).get('value', 0)
				if num_of_target == 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					if not hits:
						return Response(
							"No vehicle found",
							status=status.HTTP_404_NOT_FOUND
						)

					project_id = hits[0].get("_source", {}).get("project_id")
				elif num_of_target > 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					for hit in hits:

						project_id = hit.get("_source", {}).get("project_id")

						if project_id and checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Display Pictures Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
						vehicle_doc = response.get('_source', {})

						if not vehicle_doc:
							return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
						# result = vehicle_doc.get('display_pics')
					except Exception as e:
						return Response(f'Getting Display Pictures Failed: {e}.',
										status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				else:
					return Response('Getting Display Pictures Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
			except Exception as e:
				return Response(f'Getting Display Pictures Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		else:
			vehicle_id = f"{project_id.lower()}-{vin.lower()}"
			try:
				response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
				vehicle_doc = response.get('_source', {})

				if not vehicle_doc:
					return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
				# result = vehicle_doc.get('display_pics')
			except Exception as e:
				try:
					if e.status_code == 404:
						return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
					else:
						return Response('Getting Display Pictures Failed', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				except Exception:
					return Response('Getting Display Pictures Failed', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

		if not vehicle_doc:
			return Response('No Display Pictures Found', status=status.HTTP_404_NOT_FOUND)
		else:
			if 'display_pics' not in vehicle_doc:
				return Response('No Display Pictures Found', status=status.HTTP_404_NOT_FOUND)
			else:
				result = vehicle_doc.get('display_pics')
				if result:
					return Response(result, status=status.HTTP_200_OK)
				else:
					return Response('No Display Pictures Found', status=status.HTTP_404_NOT_FOUND)
		# if not result or len(result) == 0:
		# 	result = vehicle_doc.get('display_pics')
		#
		# if result:
		# 	return Response(result, status=status.HTTP_200_OK)
		# else:
		# 	return Response('No Display Pictures Found', status=status.HTTP_404_NOT_FOUND)

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
			return Response('Please Enter Project ID and VIN', status=status.HTTP_400_BAD_REQUEST)
		elif project_id == "ignored":
			try:
				date_today = datetime.datetime.now().strftime("%Y-%m-%d")
				library_id = request_body.get('library_id')
				
				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})
				project_id = vehicle_doc.get('project_id')

			except Exception as e:
				return Response(f'KBB Getting Player Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				vehicle_doc = ES.search(index=ES_VEHICLE_INDEX, body={
																	"query": {
																		"term": {
																			"vin.keyword": vin.lower()
																		}
																	}
																})
				num_of_target = vehicle_doc.get('hits', {}).get('total', {}).get('value', 0)
				if num_of_target == 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					if not hits:
						return Response(
							"No vehicle found",
							status=status.HTTP_404_NOT_FOUND
						)

					project_id = hits[0].get("_source", {}).get("project_id")
				elif num_of_target > 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					for hit in hits:

						project_id = hit.get("_source", {}).get("project_id")

						if project_id and checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Player Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					pass
				else:
					return Response('Getting Player Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
			except Exception as e:
				return Response(f'Getting Player Failed: {e}.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


		# if galleryMode:
		# 	if galleryMode == 'bar':
		# 		playerUrl = 'https://ivana.sister.tv/models/picture_player/index.html?projectid={}&vin={}&galleryMode=bar'.format(
		# 			project_id, vin)
		# else:
		# 	playerUrl = 'https://ivana.sister.tv/models/picture_player/index.html?projectid={}&vin={}'.format(
		# 		project_id, vin)

		if galleryMode == 'bar':

			playerUrl = (
				'https://ivana.sister.tv/models/picture_player/'
				'index.html?projectid={}&vin={}&galleryMode=bar'
			).format(project_id, vin)

		else:

			playerUrl = (
				'https://ivana.sister.tv/models/picture_player/'
				'index.html?projectid={}&vin={}'
			).format(project_id, vin)
		result.append(playerUrl)
		return Response(result, status=status.HTTP_200_OK)

class GetVideos(views.APIView):
	def post(self, request):
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
				date_today = datetime.datetime.now().strftime("%Y-%m-%d")
				library_id = request_body.get('library_id')
				
				if library_id:
					library_id = removeNonAscii(library_id)
				else:
					return Response(
						'Please Enter Library ID',
						status=status.HTTP_400_BAD_REQUEST
					)
				response = ES.search(
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
						"No vehicle found",
						status=status.HTTP_404_NOT_FOUND
					)

				vehicle_doc = hits[0].get("_source", {})
				fullmo_sis = vehicle_doc.get('fullmo_sis')
			except Exception as e:
				return Response(f'KBB Getting Video Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
		elif project_id == "rollinghill_01042020":
			try:
				vehicle_doc = ES.search(index=ES_VEHICLE_INDEX, body={
																	"query": {
																		"term": {
																			"vin.keyword": vin.lower()
																		}
																	}
																})
				num_of_target = vehicle_doc.get('hits', {}).get('total', {}).get('value', 0)
				if num_of_target == 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					if not hits:
						return Response(
							"No vehicle found",
							status=status.HTTP_404_NOT_FOUND
						)

					project_id = hits[0].get("_source", {}).get("project_id")
				elif num_of_target > 1:
					hits = vehicle_doc.get("hits", {}).get("hits", [])

					for hit in hits:

						project_id = hit.get("_source", {}).get("project_id")

						if project_id and checkIfRollingHillDealer(project_id):
							break
				else:
					return Response('Getting Video Failed: Cannot find the vehicle',
									status=status.HTTP_404_NOT_FOUND)
				if checkIfRollingHillDealer(project_id):
					vehicle_id = f"{project_id.lower()}-{vin.lower()}"
					try:
						response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
						vehicle_doc = response.get('_source', {})

						if not vehicle_doc:
							return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
						fullmo_sis = vehicle_doc.get('fullmo_sis')
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
				response = ES.get(index=ES_VEHICLE_INDEX, id=vehicle_id)
				vehicle_doc = response.get('_source', {})

				if not vehicle_doc:
					return Response('No Vehicle Found', status=status.HTTP_404_NOT_FOUND)
				fullmo_sis = vehicle_doc.get('fullmo_sis')
			except Exception as e:
				return Response(f'Getting Video Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

		if fullmo_sis:
			result.append(fullmo_sis)

		try:
			pic2vid = vehicle_doc.get('pic2vid_en_US')
		except Exception as e:
			return Response(f'Getting Video Failed: {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

		if pic2vid:
			if isinstance(pic2vid,str):
				if pic2vid.lower().startswith("http://"):
					pic2vid = pic2vid.replace("http://", "https://", 1)
			elif isinstance(pic2vid,list):
				pic2vid = [
					url.replace("http://", "https://", 1)
					if isinstance(url, str) and url.lower().startswith("http://")
					else url
					for url in pic2vid
				]
			result.append(pic2vid)

		if result:
			return Response(result, status=status.HTTP_200_OK)
		else:
			return Response('No Video Found', status=status.HTTP_404_NOT_FOUND)
