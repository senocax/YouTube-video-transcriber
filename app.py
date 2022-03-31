from ctypes.wintypes import POINT
import streamlit as st
from config import auth_key
import youtube_dl
import requests



if 'status' not in st.session_state:
    st.session_state['status'] = 'submitted'


ydl_opts = {
   'format': 'bestaudio/best',
   'postprocessors': [{
       'key': 'FFmpegExtractAudio',
       'preferredcodec': 'mp3',
       'preferredquality': '192',
   }],
   'ffmpeg-location': './',
   'outtmpl': "./%(id)s.%(ext)s",
}


transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
upload_endpoint = 'https://api.assemblyai.com/v2/upload'

headers_auth_only = {'authorization': auth_key}

headers = {
   "authorization": auth_key,
   "content-type": "application/json"
}
CHUNK_SIZE = 5242880

@st.cache
def transcribe_from_link (link,categories: bool):
    id = link.strip()

    def get_video(id):
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
          return ydl.extract_info(id)

    meta = get_video(id)
    
    save_location = meta['id'] + ".mp3"
    print("mp3 donwloaded in ", save_location)

    def read_file(filename):

        with open(filename, 'rb') as file:
            while True:
                data = file.read(CHUNK_SIZE)
                if not data:
                    break
                yield data
    
    # upload file to api assenbly 
    upload_response = requests.post(
		upload_endpoint,
		headers=headers_auth_only, data=read_file(save_location)
	)

    response_url = upload_response.json()['upload_url']
    print('url upload is', response_url)

    transcript_request = {
		'audio_url': response_url,
		'iab_categories': 'True' if categories else 'False',
	}

    transcript_response = requests.post(transcript_endpoint, json= transcript_request, headers=headers)

    transcript_id = transcript_response.json()['id']
    polling_endpoint = transcript_endpoint + "/" + transcript_id
    print("Transcribing at", polling_endpoint)

    
    return polling_endpoint

def get_status(polling_endpoint):
    polling_response = requests.get(polling_endpoint, headers= headers)
    st.session_state['status'] = polling_response.json()['status']




def refresh_status():
        st.session_state['status'] = 'submitted'


st.title('Youtube video transcriber')
link = st.text_input('Input youtube video link', 'https://www.youtube.com/watch?v=3MA-7N1zcBc', on_change= refresh_status)
st.video(link)
st.text('The transcript is...' + st.session_state['status'])
polling_endpoint = transcribe_from_link(link, False)

st.button('check_status', on_click=get_status, args=(polling_endpoint,))

transcript = ''
if st.session_state['status'] == 'completed':
    polling_response = requests.get(polling_endpoint, headers= headers)
    transcript = polling_response.json()['text']


st.markdown(transcript)


