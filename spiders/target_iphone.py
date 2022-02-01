import scrapy
import requests
from scrapy.http import TextResponse
import json
from lxml import html
import logging
import traceback

logging.basicConfig(filename="newfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
logger=logging.getLogger()


class TargetSpider(scrapy.Spider):
	name = "target_iphone_data"
	
	def start_requests(self):

		url = (
			"https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1?"
			"key=ff457966e64d5e877fdbad070f276d18ecec4a01&tcin=84616123&store_id=1232"
			"&pricing_store_id=1232&scheduled_delivery_store_id=1232&has_financing_options=true&"
			"visitor_id=017EB11D315C0201BDF7BF6A3EA115EE&has_size_context=true&latitude=52.320&"
			"longitude=4.980&state=NH&zip=01104"
		)
		yield scrapy.Request(url=url, callback=self.parse_product_page)
		
	def parse_product_page(self, response):
		if response.status == 200:
			logger.info("Succefully extracted the product page")
		else:
			logger.warning("Product page is blocked")
			return

		product_json = self.get_json_response(response)

		options_list = []
		spec_clean_list = []

		raw_product_dict = product_json.get("data", {}).get("product", {})
		raw_description_dict = raw_product_dict.get('item', {}).get('product_description', {})

		hierarchy_level_1 = raw_product_dict.get('variation_hierarchy', [])
		children = raw_product_dict.get('children', [])

		raw_bullet_pints  = raw_description_dict.get('bullet_descriptions', [])
		soft_bullet = raw_description_dict.get('soft_bullets', {}).get('bullets', [])
		
		for attribute in hierarchy_level_1:
			hierarchy_level_2 = attribute.get('variation_hierarchy', [])
			for option in hierarchy_level_2:
				option_dict = {
					'color': attribute.get('value'), 
					'size': option.get('value'),
					'tcin':option.get('tcin'),
					'image':option.get('primary_image_url') 
				}
				options_list.append(option_dict)

		for bullet in raw_bullet_pints:
			data = self.clean_html_content(bullet)
			if not data:
				continue
			spec_clean_list.append(' '.join(''.join(data).split()))

		bullet_points = ' | '.join(spec_clean_list)
		highlights = ' | '.join(soft_bullet)

		for child in children:
			price_tcin = child.get("tcin")
			for item in options_list:
				option_tcin = item.get('tcin')
				if (price_tcin != option_tcin):
					continue
				raw_product_description = child.get("item", {}).get('product_description', {})	
				raw_discription = raw_product_description.get('downstream_description')
				description = self.clean_html_content(raw_discription)

				item['price'] = child.get('price', {}).get('current_retail')
				item['title'] = raw_product_description.get('title')
				item['image'] = option.get('primary_image_url')
				item['description'] = description
				item['specification'] = bullet_points
				item['highlights'] = highlights
				
		meta_data = {
			"product_data": options_list
		}

		question_url = (
			"https://r2d2.target.com/ggc/Q&A/v1/question-answer?type=product"
			"&questionedId=84616123&page=0&size=10&sortBy=MOST_ANSWERS&"
			"key=c6b68aaef0eac4df4931aae70500b7056531cb37&"
			"errorTag=drax_domain_questions_api_error"
		)
		yield scrapy.Request(url=question_url, callback=self.parse_questions, meta=meta_data)

	def parse_questions(self, response):
		product_data = response.meta['product_data']
		if response.status == 200:
			logger.info("Succefully extracted the QA page")
		else:
			logger.warning("QA  page is blocked")
			return

		question_json = self.get_json_response(response)
		
		qa_clean_list = []

		questions = question_json.get('results', [])
		for question in questions:
			qustion_text = question.get('text')
			qa_clean_list.append(' '.join(''.join(qustion_text).split()))
		for data in product_data:
			data['questions'] = qa_clean_list

		print(product_data)

	def get_json_response(self, response):

		try:
			response_json = json.loads(response.text)
		except Exception:
			log_dict = {
		        "message": "json response not found",
		        "traceback": traceback.format_exc()
    		}
			logger.warning(json.dumps(log_dict))
			response_json = {}
		return response_json

	def clean_html_content(self, raw_content):
		if not raw_content:
			return 
		parser = html.fromstring(raw_content)
		parsed_data = parser.xpath('//text()')
		cleaned_content = ' '.join(' '.join(parsed_data).split())
		return cleaned_content
