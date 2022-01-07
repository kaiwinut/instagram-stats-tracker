import os
import json
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

""" Configurations

path = 'data/info.txt'
path = os.path.join(os.path.dirname(__file__), 'data', 'info.txt')
fields = 'name,username,biography,follows_count,followers_count,media_count'
media_fields = 'timestamp,id,like_count,comments_count,caption,media_type'
"""

def get_user_info(path, fields = 'name,username,biography,follows_count,followers_count,media_count'):
	if os.path.exists(path):
		with open(path, 'r') as f:
			data = f.read()
			info = json.loads(data)
	else:
		raise Exception(f"Could not load existing info data from {path}.")

	url = f'https://graph.facebook.com/v11.0/{info["business_account_id"]}?fields=business_discovery.username({info["username"]}){{{fields}}}&access_token={info["token"]}'
	response = requests.get(url)
	result = response.json()['business_discovery']
	result['Timestamp'] = pd.Timestamp.now()
	user_df = pd.DataFrame([result])
	user_df = user_df.set_index('Timestamp')

	user_df.to_csv('data/user_info.csv')
	return user_df

def get_media_info(path, media_fields = 'timestamp,id,like_count,comments_count,caption,media_type'):
	if os.path.exists(path):
		with open(path, 'r') as f:
			data = f.read()
			info = json.loads(data)
	else:
		raise Exception(f"Could not load existing info data from {path}.")   

	all_responses = []
	url = f'https://graph.facebook.com/v11.0/{info["business_account_id"]}?fields=business_discovery.username({info["username"]}){{media{{{media_fields}}}}}&access_token={info["token"]}'
	response = requests.get(url)
	result = response.json()['business_discovery']
	all_responses.append(result['media']['data'])

	if 'after' in result['media']['paging']['cursors'].keys():
		next_token = result['media']['paging']['cursors']['after']
		while next_token is not None:
			url = f'https://graph.facebook.com/v11.0/{info["business_account_id"]}?fields=business_discovery.username({info["username"]}){{media.after({next_token}){{{media_fields}}}}}&access_token={info["token"]}'
			response = requests.get(url)
			result = response.json()['business_discovery']
			all_responses.append(result['media']['data'])

			if 'after' in result['media']['paging']['cursors'].keys():
				next_token = result['media']['paging']['cursors']['after']
			else:
				next_token = None

	media_df = pd.DataFrame(all_responses[0])
	if len(all_responses) > 1:
		for i in range(1, len(all_responses)):
			media_df = pd.concat([pd.DataFrame(all_responses[i]), media_df])

	media_df_sorted = media_df.sort_values('timestamp').drop_duplicates('id').reset_index(drop=True)
	media_df_sorted.set_index('timestamp')

	data = {'engagement': [], 'impressions': [], 'reach': []}

	for i in range(len(media_df_sorted)):
		url = f'https://graph.facebook.com/v11.0/{media_df_sorted.loc[i, :]["id"]}/insights?metric=engagement,impressions,reach&access_token={info["token"]}'
		response = requests.get(url)
		result = response.json()
		data[result['data'][0]['name']].append(result['data'][0]['values'][0]['value'])
		data[result['data'][1]['name']].append(result['data'][1]['values'][0]['value'])
		data[result['data'][2]['name']].append(result['data'][2]['values'][0]['value'])

	for d, v in data.items():
		media_df_sorted[d] = v

	media_df_sorted.to_csv('data/media_info.csv')
	return media_df_sorted

def display(media_info, to_file='data/media_info.png'):
	plt.style.use('ggplot')

	fig, ax1 = plt.subplots(figsize=(10, 7))

	ax1.set_xlabel('Post Date')
	ax1.set_ylabel('engagement')
	media_info.plot(x='timestamp', y='engagement', kind='bar', ax=ax1, alpha=1.0, color='#FFD07F')
	media_info.plot(x='timestamp', y='like_count', kind='bar', ax=ax1, alpha=1.0, color='#FDA65D')
	media_info.plot(x='timestamp', y='comments_count', kind='bar', ax=ax1, alpha=1.0, color='#E26A2C')
	ax1.legend(['engagement', 'likes', 'comments'])

	ax2 = ax1.twinx()
	ax2.set_ylabel('impressions & reach')
	media_info.plot(x='timestamp', y='impressions', kind='line', ax=ax2, alpha=1.0, color='#082032')
	media_info.plot(x='timestamp', y='reach', kind='line', ax=ax2, alpha=1.0, color='#5089C6')
	ax2.legend(['impressions', 'reach'], loc="upper right")

	lst = []
	labels = []
	for i, l in enumerate(media_info['timestamp'].str[:10]):
		if i % 1 == 0:
			lst.append(i)
			labels.append(l)

	ax1.set_xticks(lst)
	ax1.set_xticklabels(labels, rotation=90)

	plt.savefig(to_file)
	plt.show()