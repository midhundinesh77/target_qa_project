import scrapy
import requests
from scrapy.http import TextResponse
import json
from lxml import html

class TargetSpider(scrapy.Spider):
	name = "target_iphone_data"
	
	def start_requests(self):
		url ="https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1?key=ff457966e64d5e877fdbad070f276d18ecec4a01&tcin=84616123&store_id=1232&pricing_store_id=1232&scheduled_delivery_store_id=1232&has_financing_options=true&visitor_id=017EB11D315C0201BDF7BF6A3EA115EE&has_size_context=true&latitude=52.320&longitude=4.980&state=NH&zip=01104"
		yield scrapy.Request(url=url, callback=self.parse_product_page)
		
	def parse_product_page(self, response):

		product_json = json.loads(response.text)

		options_list = []
		spec_clean_list = []

		hierarchy_level_1 = product_json.get("data").get("product").get('variation_hierarchy')
		children = product_json.get("data").get("product").get('children')
		raw_bullet_pints  =product_json.get("data").get("product").get('item').get('product_description').get('bullet_descriptions')
		soft_bullet = product_json.get("data").get("product").get('item').get('product_description').get('soft_bullets').get('bullets')
		
		for attribute in hierarchy_level_1:
			hierarchy_level_2 = attribute.get('variation_hierarchy')
			for option in hierarchy_level_2:
				option_dict = {'color': attribute.get('value',None), 'size': option.get('value'),'tcin':option.get('tcin'),'image':option.get('primary_image_url') }
				options_list.append(option_dict)

		for bullet in raw_bullet_pints:
			parser = html.fromstring(bullet)
			data = parser.xpath('//text()')
			if data:
				spec_clean_list.append(' '.join(''.join(data).split()))

		bullet_points = ' | '.join(spec_clean_list)
		highlights = ' '.join(soft_bullet)


		for child in children:
			price_tcin = child.get("tcin")
			for item in options_list:
				option_tcin = item.get('tcin')
				if(price_tcin==option_tcin):
					
					raw_discription = child.get("item").get('product_description').get('downstream_description')
					parser = html.fromstring(raw_discription)
					parsed_data = parser.xpath('//text()')
					description = ' '.join(' '.join(parsed_data).split())

					item['price']=child.get('price').get('current_retail')
					item['image']= option.get('primary_image_url')
					item['description'] = description
					item['specification'] = bullet_points
					item['highlights'] = highlights
		# print(options_list)

	# 	qa_url = "https://r2d2.target.com/ggc/Q&A/v1/question-answer?type=product&questionedId=84616123&page=0&size=10&sortBy=MOST_ANSWERS&key=c6b68aaef0eac4df4931aae70500b7056531cb37&errorTag=drax_domain_questions_api_error"
	# 	yield scrapy.Request(url=qa_url, callback=self.parse_qustions,meta =dict)

	# def parse_qustions(self,response):
	# 	print("ddddddd",response.status)
