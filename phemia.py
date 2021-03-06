# -*- coding: UTF-8 -*-

__version__			= '0.2.0'
__version_info__	= tuple(int(num) for num in __version__.split('.'))

import os
import sys
import json
import requests
import urllib
import collections
import time

# Phemia - Python Messenger AI
class Messaging:

	ALLOWED_PLATFORMS	= ('facebook','raw')
	ALLOWED_ATTACHMENTS	= ('image','audio','video','file')
	DEFAULT_BUTTON		= 'UNDEFINED'
	
	ALLOWED_FACEBOOK_TITLE_LENGTH	= 80
	ALLOWED_FACEBOOK_SUBTITLE_LENGTH= 80
	ALLOWED_FACEBOOK_BUTTONS_LENGTH	= 3
	ALLOWED_FACEBOOK_MESSAGE_LENGTH	= 320
	
	
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
		# TODO: implement for Python server apps
		get 	= urllib.parse.parse_qs(os.getenv('QUERY_STRING'), encoding='utf-8')
		data	= {}
		for key, value in get.items():
			data[key]=get[key][0]
		return data	
	
	### read HTTP POST JSON vars based on environment
	def _http_request_post(self):
		# NOTE: can only be read once
		# TODO: implement for Python server apps
		return json.load(sys.stdin, encoding='utf-8')
		#return json.loads(io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8').read())
	
	### convert received message to a simple dict
	def receive(self):
		data		= self._http_request_post()
		return self.translate(data)
		
	def translate(self,data):
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
					
					if 'postback' in data['entry'][0]['messaging'][0]:
						text 				= data['entry'][0]['messaging'][0]['postback']['payload']
						other['is_postback']= True
					
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
				response['message']['text']			= message['text'][:self.ALLOWED_FACEBOOK_MESSAGE_LENGTH]
			# attachment
			if 'attachment' in message:
				# send ONE file / image
				if len(message['attachment'])==1 and 'url' in message['attachment'][0] and message['attachment'][0]['url']:
					if 'type' not in message['attachment'][0] or message['attachment'][0]['type'] not in self.ALLOWED_ATTACHMENTS:
						message['attachment'][0]['type']	= get_attachment_type(message['attachment'][0]['url'])
					if 'cache' in message['attachment'][0] and message['attachment'][0]['cache']:
						if message['attachment'][0]['cache']>int(time.time()):
							reusable	= True
						else:
							reusable	= False
					else:
						reusable	= False
					
					if 'text' in message and message['text']:
						if 'title' not in message['attachment'][0]:
							message['attachment'][0]['title']= message['text'][:self.ALLOWED_FACEBOOK_TITLE_LENGTH]
						elif 'description' not in message['attachment'][0]:
							message['attachment'][0]['description']= message['text'][:self.ALLOWED_FACEBOOK_SUBTITLE_LENGTH]
						## DELETE
						response['message'].pop('text')	# facebook won't send attachments with text
				
					# send ONE file / image as a simple attachment WITHOUT text	or buttons		
					if (('title' not in message['attachment'][0] or not message['attachment'][0]['title']) and ('description' not in message['attachment'][0] or not message['attachment'][0]['description']) and ('buttons' not in message['attachment'][0] or not message['attachment'][0]['buttons'])) or message['attachment'][0]['type'] != 'image':
						response['message']['attachment']	= {
							"type"		: message['attachment'][0]['type'],
							"payload"	: {
								"url"		: message['attachment'][0]['url'],
								"is_reusable":reusable
							}
						}
					# send ONE image WITH text and/or buttons	
					elif message['attachment'][0]['type'] == 'image':
						if 'title' not in message['attachment'][0]:
							message['attachment'][0]['title']	= message['attachment'][0]['url']
						if 'description' not in message['attachment'][0]:
							message['attachment'][0]['description']= ""
						if 'buttons' in message['attachment'][0]:
							buttons								= self._generate_facebook_buttons(message['attachment'][0]['buttons'])[:self.ALLOWED_FACEBOOK_BUTTONS_LENGTH]
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
									"subtitle"		: message['attachment'][0]['description'],
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
				# send text with buttons
				elif len(message['attachment'])==1 and ('url' not in message['attachment'][0] or not message['attachment'][0]['url']) and ('type' not in message['attachment'][0] or message['attachment'][0]['type']=='none'):
					if 'buttons' in message['attachment'][0]:
						response['message']['quick_replies']= self._generate_facebook_buttons(message['attachment'][0]['buttons'], 'quick_reply')					
				
			# other
			if 'other' in message:
				# sender action such as typing_on, typing_off, mark_seen			
				if 'action' in message['other']:
					if not response['message']:	# facebook won't send actions with attachments or text
						response['sender_action']			= message['other']['action']
						response['message']					= None
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
		
	def _generate_facebook_buttons(self,buttons,type='attachment'):
		if buttons:
			facebook_buttons	= []
			for button in buttons:
				tmp					= {}
				if type=='quick_reply':
					if 'type' in button and button['type'] == 'location':
						tmp['content_type']	= 'location'
					else:
						tmp['content_type']	= 'text'
						if 'text' in button:
							tmp['title']		= button['text']
						else:
							tmp['title']		= self.DEFAULT_BUTTON
						if 'value' in button:
							tmp['payload']		= tmp['title']
						else:
							tmp['payload']		= tmp['title']
						if 'image' in button:
							tmp['image_url']	= button['image']
				elif type=='menu':
					if 'text' in button:
						tmp['title']		= button['text']
					else:
						tmp['title']		= self.DEFAULT_BUTTON
					if 'type' in button and button['type'] == 'url' and 'value' in button:
						tmp['type']			= 'web_url'
						tmp['url']			= button['value']
					else:
						tmp['type']			= 'postback'
						tmp['payload']		= button['value']
					
				else: 
					if 'text' in button:
						tmp['title']		= button['text']
					else:
						tmp['title']		= self.DEFAULT_BUTTON
					if 'type' in button and button['type'] == 'url' and 'value' in button:
						tmp['type']			= 'web_url'
						tmp['url']			= button['value']
						#tmp['fallback_url']	= button['value']
					else:
						tmp['type']			= 'postback'
						if 'value' in button:
							tmp['payload']		= button['value']
						else:
							tmp['payload']		= tmp['title']
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
		if self.is_platform('facebook'):
			if action=="get":
				data	= requests.get("https://graph.facebook.com/v2.6/me/thread_settings?fields=whitelisted_domains&access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, timeout=self.get_value('timeout'))
			elif action in ('add','remove','set'):
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
		return {}
		
	def menu(self,menu={}):
		if self.is_platform('facebook'):
			if menu:
				if 'attachment' in menu and len(menu['attachment'])==1 and 'buttons' in menu['attachment'][0] and menu['attachment'][0]['buttons']:
					curl	= {
						"setting_type"		: "call_to_actions",
						"thread_state"		: "existing_thread",
						"call_to_actions"	: self._generate_facebook_buttons(menu['attachment'][0]['buttons'],'menu')
					}
					data	= requests.post("https://graph.facebook.com/v2.6/me/thread_settings?access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, data=json.dumps(curl), timeout=self.get_value('timeout'))
					return data.json()
				else:
					raise ValueError('No attachment with buttons found.')
					return {}
			else:
				curl	= {
					"setting_type"		: "call_to_actions",
					"thread_state"		: "existing_thread"
				}
				data	= requests.delete("https://graph.facebook.com/v2.6/me/thread_settings?access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, data=json.dumps(curl), timeout=self.get_value('timeout'))
				return data.json()
		return {}

	def welcome(self,payload=None):
		if self.is_platform('facebook'):
			curl	= {
				"setting_type"		: "call_to_actions",
				"thread_state"		: "new_thread"
			}
			if payload is not None:
				curl['call_to_actions']	= [{"payload":payload}]
				data	= requests.post("https://graph.facebook.com/v2.6/me/thread_settings?access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, data=json.dumps(curl), timeout=self.get_value('timeout'))
			else:
				data	= requests.delete("https://graph.facebook.com/v2.6/me/thread_settings?access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, data=json.dumps(curl), timeout=self.get_value('timeout'))
			return data.json()
		return {}
		
	def get_user_info(self,user={}):
		if self.is_platform('facebook'):
			if user and 'id' in user:
				data	= requests.get("https://graph.facebook.com/v2.6/"+str(user['id'])+"?fields=first_name,last_name,profile_pic,locale,timezone,gender&access_token=" + self.get_value('access_token'), headers={'Content-type': 'application/json', 'Accept': 'text/plain'}, timeout=self.get_value('timeout'))
				return data.json()
		return {}

class Session:

	ALLOWED_PLATFORMS	= ('raw')
	
	##### CONSTRUCTOR #####
	def __init__(self,options={}):
		default_settings	= {
			"platform"	: "raw",				# save session as text files by default
			"raw"		: {						# saving sessions as text files containing JSON objects
				"path"				: '',		# server to send messages to (if given)
				"extension"			: 'txt'		# file extension
			}
		}
		self.settings		= deep_dict_merge(default_settings,options)
	
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
			
	def file_command(self,command,id,new_contents=None):
		if self.get_value('extension'):
			if self.get_value('extension')[0]=='.':
				id	+= self.get_value('extension')
			else:
				id	+= '.'+self.get_value('extension')
		file	= os.path.join(self.get_value('path'), id)	
		if command=='remove':
			os.remove(file)
		else:
			if command=='get':
				if not os.path.isfile(file):
					data	= open(file, 'a').close()
					return {}
				else:
					data	= open(file, 'r').read()
					if data:
						return json.loads(data)
					else:
						return {}
						
			else:
				data	= open(file, 'w')
				if command=='set':
					if new_contents:
						data.write(json.dumps(new_contents))
					else:
						data.write('{}')
					data.close()
				elif command=='clear':
					data.write('{}')
					data.close()
		return {}

	def file_as_dict(self,id,key,value=None):
		data	= self.file_command('get',id)
		if value is not None:
			data['last_update']= int(time.time())
			data[key]	= value
			new_data	= self.file_command('set',id,data)
		if key in data:
			return data[key]
		return None
	
	def get(self,id,key):
		if self.is_platform('raw'):
			return self.file_as_dict(id,key)
	
	def set(self,id,key,value):
		if self.is_platform('raw'):
			return self.file_as_dict(id,key,value)
	
	def clear(self,id):
		if self.is_platform('raw'):
			return self.file_command('clear',id)
		
	def remove(self,id):
		if self.is_platform('raw'):
			return self.file_command('remove',id)
	
	def append(self,id,key,value=None,max_length=7):
		if self.is_platform('raw'):
			data	= self.file_command('get',id)
			if max_length>0:
				if value is not None:
					data['last_update']= int(time.time())
					if key in data and isinstance(data[key], list):
						start		= len(data[key])-max_length+1
						if start<0:
								start	= 0
						data[key]	= data[key][start:]
					else:
						data[key]	= []
					data[key].append(value)
					new_data	= self.file_command('set',id,data)
			else:
				raise ValueError('Array length must be more than 0')
			return data[key]
	
	def dict_path(self,data={},path=[]):
		if data and path:
			if path[0] in data:
				if isinstance(data[path[0]], dict):
					return self.dict_path(data[path[0]],path[1:])
				elif len(path)==1:
					return data[path[0]]
		return None
	
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
