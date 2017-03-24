# -*- coding: UTF-8 -*-

__version__			= '0.2.0'
__version_info__	= tuple(int(num) for num in __version__.split('.'))

import os
import sys
import json
import requests
import urllib
import collections

# Phemia - Python Messenger AI
class Messaging:

	ALLOWED_PLATFORMS	= ('facebook','raw')
	ALLOWED_ATTACHMENTS	= ('image','audio','video','file')
	ALLOWED_TITLE_LENGTH= 80
	ALLOWED_SUBTITLE_LENGTH=80
	
	##### CONSTRUCTOR #####
	def __init__(self,options={}):
		default_settings	= {
			"platform"	: "facebook",			# use facebook by default
			"log_file"	: None,					# error log file
			
			"facebook"	: {						# variables for facebook messaging
				"access_token"		: None,		# facebook access token
				"verify_token"		: None,		# facebook verify token			
				"timeout"			: 5			# timeout for requests
			},
			
			"raw"		: {						# variables for messaging with custom platforms accepting the same API calls
				"server"			: None,		# server to send messages to (if given)
				"allow_ips"			: [],		# list of websites allowed to access
				"disallow_ips"		: [],		# list of websites allowed to access
				"print"				: True,		# print data to be sent to stdout
				"print_text_only"	: True,		# only invoke print if there is actual text to be sent
				"jsonp"				: None,		# data to be printed as a JSONP object
				"timeout"			: 5			# timeout for requests
			}
		}	
		self.settings		= deep_dict_merge(default_settings,options)
		self.last_sender	= {}
		self.last_recipient	= {}
		
		# Automatically register to webhook on INIT
		if self.settings['platform'] not in self.ALLOWED_PLATFORMS:
			raise ValueError('Platform "%s" is not supported.' % (self.settings['platform']))
		elif self.settings['platform'] == 'facebook':
			if self.get_value('verify_token') is not None and self.get_value('access_token') is not None:
				arguments						= self._http_request_get()
				if 'hub.verify_token' in arguments and 'hub.challenge' in arguments:
					if arguments['hub.verify_token'] == self.get_value('verify_token'):
						print(arguments['hub.challenge'])
	
	def is_platform(self,compare):
		if compare:
			return compare==self.settings['platform']
		return False
		
	def set_platform(self,new_platform):
		if new_platform and new_platform in self.ALLOWED_PLATFORMS:
			self.settings['platform']	= new_platform
		else:
			raise ValueError('Platform "%s" is not supported.' % (new_platform))
	
	def get_value(self,variable):
		return self.settings[self.settings['platform']][variable]
		
	def log_txt(self,text):
		if self.settings['log_file']:
			with open(self.settings['log_file'], 'a') as out:
				out.write(str(text) + '\n')
		
	### read HTTP GET vars based on environment
	def _http_request_get(self):
		get 	= urllib.parse.parse_qs(os.getenv('QUERY_STRING'), encoding='utf-8')
		data	= {}
		for key, value in get.items():
			data[key]=get[key][0]
		return data	
	
	### read HTTP POST JSON vars based on environment
	def _http_request_post(self):
		#NOTE: can only be read once
		return json.load(sys.stdin, encoding='utf-8')
		#return json.loads(io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8').read())
	
	### convert received message to a simple dict
	def receive(self):
		data		= self._http_request_post()
		sender		= {"id":None}
		recipient	= {"id":None}
		text		= None
		attachment	= []
		other		= {}
		
		if self.is_platform('facebook'):
			if 'entry' in data and data['entry'] and 'messaging' in data['entry'][0]:
				try:
					sender['id']		= data['entry'][0]['messaging'][0]['sender']['id']
					recipient['id']		= data['entry'][0]['messaging'][0]['recipient']['id']
					
					if 'timestamp' in data['entry'][0]['messaging'][0]:
						other['timestamp']	= data['entry'][0]['messaging'][0]['timestamp']
					if 'delivery' in data['entry'][0]['messaging'][0]:
						if 'watermark' in data['entry'][0]['messaging'][0]['delivery']:
							other['delivery']	= data['entry'][0]['messaging'][0]['delivery']['watermark']
						if 'mids' in data['entry'][0]['messaging'][0]['delivery']:
							other['mids']		= data['entry'][0]['messaging'][0]['delivery']['watermark']
					if 'read' in data['entry'][0]['messaging'][0] and 'watermark' in data['entry'][0]['messaging'][0]['read']:
						other['read']		= data['entry'][0]['messaging'][0]['read']['watermark']

					if 'message' in data['entry'][0]['messaging'][0]:
						if 'text' in data['entry'][0]['messaging'][0]['message']:
							text 				= data['entry'][0]['messaging'][0]['message']['text']
						else:
							text				= ""
						
						if 'is_echo' in data['entry'][0]['messaging'][0]['message']:
							other['is_echo']	=  data['entry'][0]['messaging'][0]['message']['is_echo']
						if 'mid' in data['entry'][0]['messaging'][0]['message']:
							other['mids']		= [data['entry'][0]['messaging'][0]['message']['mid']]
						
						if 'attachments' in data['entry'][0]['messaging'][0]['message']:
							for item in data['entry'][0]['messaging'][0]['message']['attachments']:
								if item and 'payload' in item:									
									tmp					= {
										"url"		: None,
										"type"		: item['type'],
										"reusable"	: None,
										"title"		: None,
										"description": None,
										"sticker"	: None,
										"latitude"	: None,
										"longitude"	: None,
										"buttons"	: []
									}
									if item['payload']:
										if 'url' in item['payload']:
											tmp['url']		= item['payload']['url']
										if 'title' in item['payload']:
											tmp['title']	= item['payload']['title']
										if 'subtitle' in item['payload']:
											tmp['description']= item['payload']['subtitle']
										if 'sticker_id' in item['payload']:
											tmp['sticker']	= item['payload']['sticker_id']
										if 'coordinates' in item['payload']:
											tmp['latitude']	= item['payload']['coordinates']['lat']
											tmp['longitude']= item['payload']['coordinates']['long']
										if 'is_reusable' in item['payload']:
											tmp['reusable']= item['payload']['is_reusable']
									else:
										# undocumented fallback for URL attachments
										if 'url' in item:
											tmp['url']		= item['url']
										if 'title' in item:
											tmp['title']	= item['title']
										if 'subtitle' in item:
											tmp['description']= item['subtitle']

									attachment.append(tmp)
				except Exception as e:
					self.log_txt("Unexpected data ' {0} ': {1}\n".format(json.dumps(data), repr(e)))
		
		elif self.is_platform('raw'):
			# TODO: check if allowed sender's os.environ.get('REMOTE_ADDR')/os.environ.get('HTTP_REFERER')/os.environ.get('HTTP_USER_AGENT') are allowed
			try:
				sender 		= deep_dict_merge(sender,data['sender'])
				recipient	= deep_dict_merge(recipient,data['recipient'])
				if 'text' in data:
					text 		= data['text']
				else:
					text		= ""
				if 'attachment' in data:
					for item in data['attachment']:
						item_fix	= {}
						for key, value in item.items():
							if key in ('url','type','reusable','title','description','sticker','latitude','longitude'):
								item_fix[key]	= value
						if item_fix:
							attachment.append(item_fix)
				if 'other' in data:
					other	= data['other']				
			except:
				self.log_txt("Unexpected data ' {0} ': {1}\n".format(json.dumps(data), str(e)))
			
		self.last_sender	= sender
		self.last_recipient	= recipient

		return {
			"sender"		: sender,
			"recipient"		: recipient,
			"text"			: text,
			"attachment"	: attachment,
			"other"			: other,
			"raw"			: data
		}
	
	### send message
	def send(self,message={}):
		if self.is_platform('facebook'):
			response	= {
				"recipient"		: {"id"		: message['recipient']['id']},
				"message"		: {}
			}
			# text
			if 'text' in message:
				response['message']['text']			= message['text']
			# attachment
			if 'attachment' in message:
				# send one file / image
				if len(message['attachment'])==1 and message['attachment'][0]['url']:
					if 'type' not in message['attachment'][0] or message['attachment'][0]['type'] not in ALLOWED_ATTACHMENTS:
						message['attachment'][0]['type']	= get_attachment_type(message['attachment'][0]['url'])
					if 'reusable' not in message['attachment'][0]:
						message['attachment'][0]['reusable']= False
					
					if 'text' in message and message['text']:
						if 'title' not in message['attachment'][0]:
							message['attachment'][0]['title']= message['text'][:self.ALLOWED_TITLE_LENGTH]
						elif 'description' not in message['attachment'][0]:
							message['attachment'][0]['subtitle']= message['text'][:self.ALLOWED_SUBTITLE_LENGTH]
						## DELETE
						response['message'].pop('text')	# facebook won't send attachments with text
				
					# send one file / image as a simple attachment without text				
					if (('title' not in message['attachment'][0] or not message['attachment'][0]['title']) and ('description' not in message['attachment'][0] or not message['attachment'][0]['description'])) or message['attachment'][0]['type'] != 'image':
						response['message']['attachment']	= {
							"type"		: message['attachment'][0]['type'],
							"payload"	: {
								"url"		: message['attachment'][0]['url'],
								"is_reusable":message['attachment'][0]['reusable']
							}
						}
					if message['attachment'][0]['type'] == 'image':
						if 'title' not in message['attachment'][0]:
							message['attachment'][0]['title']	= message['attachment'][0]['url']
						if 'description' not in message['attachment'][0]:
							message['attachment'][0]['subtitle']= ""
						if 'buttons' in message['attachment'][0]:
							buttons								= self._generate_facebook_buttons(message['attachment'][0]['buttons'])
						else:
							buttons								= None
						
						response['message']['attachment']	= {
							"type"		: "template",
							"payload"	:{
								"template_type"	:"generic",
								"elements"		:[
								   {
									"title"			: message['attachment'][0]['title'],
									"image_url"		: message['attachment'][0]['url'],
									"subtitle"		: message['attachment'][0]['subtitle'],
									"default_action": {
									  "type"			: "web_url",
									  "url"				: message['attachment'][0]['url'],
									  "messenger_extensions": True,
									  "webview_height_ratio": "full",	# compact|tall|full
									  "fallback_url"	: message['attachment'][0]['url']
									},
									"buttons"	: buttons     
								  }
								]
							}
						}
						
			# other
			if 'other' in message:
				# sender action such as typing_on, typing_off, mark_seen			
				if 'action' in message['other']:
					if not response['message']:	# facebook won't send actions with attachments or text
						response['sender_action']			= message['other']['action']
				# documented on facebook but does not work
				if 'notification' in message['other']:
					response['notification_type']		= message['other']['notification']
			
			data_json	= {}
			recipient	= {}
			other		= {}
			error		= {}
			try:
				data	= requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, data=json.dumps(response), timeout=self.get_value('timeout'))
			#except requests.exceptions.Timeout as e:
			#except requests.exceptions.TooManyRedirects as e:
			#except requests.exceptions.HTTPError as e:
			except requests.exceptions.RequestException as e:
				error['platform']	= "python"
				error['type']		= "PhemiaRequestError"
				error['message']	= str(e)
			
			try:
				data_json	= data.json()
				if 'recipient_id' in data_json:
					recipient		= {"id"		: data_json['recipient_id']}
				else:
					recipient		= message['recipient']
				if 'message_id' in data_json:
					other['mids']	= [data_json['message_id']]
			except:
				error['platform']	= "python"
				error['type']		= "PhemiaRequestError"
				error['message']	= "Failed to convert received data to JSON"
				data_json	= {}
			
			if 'error' in data_json:
				error				= data_json['error']
				error['platform']	= "facebook"				
			
			try:
				request	= {
					"status_code"	: data.status_code,
					"headers"		: dict(data.headers),
					"encoding"		: data.encoding
				}
			except:
				if data:
					request	= {
						"status_code"	: data.status_code,
						"headers"		: None,
						"encoding"		: None
					}
				else:
					request	= {
						"status_code"	: None,
						"headers"		: None,
						"encoding"		: None
					}
					
			return {
				"request"	: request,
				"sender"	: {},
				"recipient"	: recipient,
				"other"		: other,
				"raw"		: data_json,
				"error"		: error
			}
			
		elif self.is_platform('raw'):
			response	= {}
			for item in ('recipient','sender','text','attachment','other'):
				if item in message:
					response[item]	= message[item]
			
			data_json	= {}
			sender		= {}
			recipient	= {}
			other		= {}
			error		= {}
			try:
				if self.get_value('print'):
					if not self.get_value('print_text_only') or (self.get_value('print_text_only') and 'text' in response and response['text']):
						if self.get_value('jsonp'):
							print(str(get_value('jsonp'))+'('+json.dumps(response)+');')
						else:
							print(json.dumps(response))
			except:
				error['platform']	= "python"
				error['type']		= "PhemiaOutputError"
				error['message']	= "Could not print response data to STDOUT."
			try:
				if self.get_value('server'):
					data	= requests.post(server, headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, data=json.dumps(response), timeout=self.get_value('timeout'))	
					if 'sender' in data:
						sender		= data['sender']
					elif 'sender' in message:
						sender		= message['sender']
					if 'recipient' in data:
						recipient	= data['recipient']
					elif 'recipient' in message:
						recipient	= message['recipient']
					if 'other' in data:
						other		= data['other']
				else:
					data	= {}
			except requests.exceptions.RequestException as e:
				error['platform']	= "python"
				error['type']		= "PhemiaRequestError"
				error['message']	= str(e)
			try:
				if data:
					data_json	= data.json()
				else:
					data_json	= {}
			except:
				error['platform']	= "python"
				error['type']		= "PhemiaRequestError"
				error['message']	= "Failed to convert received data to JSON"
				data_json	= {}
			
			if 'error' in data_json:
				error				= data_json['error']
				error['platform']	= "raw"				
			
			try:
				request	= {
					"status_code"	: data.status_code,
					"headers"		: dict(data.headers),
					"encoding"		: data.encoding
				}
			except:
				if data:
					request	= {
						"status_code"	: data.status_code,
						"headers"		: None,
						"encoding"		: None
					}
				else:
					request	= {
						"status_code"	: None,
						"headers"		: None,
						"encoding"		: None
					}
			
			return {
				"request"	: request,
				"sender"	: sender,
				"recipient"	: recipient,
				"other"		: other,
				"raw"		: data_json,
				"error"		: error
			}
			
	def _generate_fallback_url(self,url):
		if url:
			return "{0.scheme}://{0.netloc}/".format(urllib.parse.urlsplit(url))
		return ''
		
	def _generate_facebook_buttons(self,buttons,quick_reply=False):
		if buttons:
			facebook_buttons	= []
			for button in buttons:
				tmp					= {}
				if quick_reply:
					if 'type' in button and button['type'] == 'location':
						tmp['content_type']	= 'location'
					else:
						tmp['content_type']	= 'text'
						if 'text' in button:
							tmp['title']		= button['text']
						if 'url' in button:
							tmp['payload']		= button['url']
						if 'image' in button:
							tmp['image_url']	= button['image']
				else:
					if 'type' in button and button['type'] == 'url':
						tmp['type']			= 'web_url'
						if 'url' in button:
							tmp['url']			= button['url']
							tmp['fallback_url']	= button['url']
					else:
						tmp['type']			= 'postback'
						if 'url' in button:
							tmp['payload']		= button['url']
					if 'text' in button:
						tmp['title']		= button['text']
					tmp['messenger_extensions']= True
					#TODO: webview_height_ratio
					
				facebook_buttons.append(tmp)
			return facebook_buttons
		return []
	
	### send reply (send message to last sender)
	def reply(self,message={}):
		if 'recipient' not in message:
			message['recipient']	= self.last_sender
		return self.send(message)
	
	def whitelist(self,action="get",domains=[]):
		if action=="get":
			data	= requests.get("https://graph.facebook.com/v2.6/me/thread_settings?fields=whitelisted_domains&access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, timeout=self.get_value('timeout'))
		elif action in ('add','remove'):
			if not domains:
				#domains	= ['https://'+os.environ.get('HTTP_HOST')+'/']
				raise ValueError('No list of domains is given.')
			curl	= {
				"setting_type"		: "domain_whitelisting",
				"whitelisted_domains": domains,
				"domain_action_type": "add"
			}
			data	= requests.post("https://graph.facebook.com/v2.6/me/thread_settings?access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, data=json.dumps(curl), timeout=self.get_value('timeout'))
		else:
			raise ValueError('Only "get", "add" and "remove" are supported.')
			return {}
		return data.json()

def deep_dict_merge(d, u):
	''' VIA http://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth '''
	for k, v in u.items():
		if isinstance(v, collections.Mapping):
			r = deep_dict_merge(d.get(k, {}), v)
			d[k] = r
		else:
			d[k] = u[k]
	return d	

def get_attachment_type(file):
	if file:
		extension	= file.lower().split(".")[-1]
		if extension in ('jpg','jpeg','gif','png','bmp','tiff'):
			return 'image'
		elif extension in ('wav','ogg','mp3','wma','aiff','3gp'):
			return 'audio'
		elif extension in ('webm','flv','ogv','gifv','avi','mov','qt','wmv','mpg','mpeg','mp4'):
			return 'video'
	return 'file'

'''
	Message JSON model:
	
	{
		"sender"	: {
			"id"		: "1234"
		},
		"recipient"	: {
			"id"		: "1234"
		}
		"text"		: "utf-8 text message"
		"attachment": [
			{
				"url"		: "http://cache.to-file.com/filepath/file.jpg",
				"type"		: "image",
				"reusable"	: False,
				"title"		: "A JPG image attachment",
				"description": "a simple example",
				"sticker"	: "1234",
				"latitude"	: 1.0000,
				"longitude"	: 2.0000,
				"buttons"	: [
					{},
					{}
				]
			}
		],
		"other"		: {
			"action"	: "typing_on",
			"notification": "regular"
		}
	}
'''
