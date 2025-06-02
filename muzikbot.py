import asyncio
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from youtube_search import YoutubeSearch
import yt_dlp
from pydub import AudioSegment
import tempfile
import requests
import json

TOKEN = "bot tokenini yapıştır"
SPOTIFY_CLIENT_ID = "spotify ıdni yapıştır"
SPOTIFY_CLIENT_SECRET = "spotify client secretini yapıştır"
SPOTIFY_TOKEN = os.getenv("SPOTIFY_TOKEN", "BQC0MpaKDAxgfauc48pQk_iQPn2_fvlbHBwEEqqBVKzPyLQ-eQJ8DVjX93mH_OW_ojjvnQu9qW0abVdt7QDrUvf-XMeW-JSL5dsTtznu75GQkQFmEEQcW7-0DDpNGze-sapw8RvZCF5wv_FCfd-TjeUr9qAr4dt92nlW9tF95wEXi35GJuj3pRxa3b0ocgOi7xspzYrD1uBBQQzPBWFnY7WYfP6FLfgZjS5RvIRh6aBcCtRfWTpQYgHCGzkaJDDlgCO_jeDm1rbNqqIEszlZkzVbtjDSdBYdNH9I2MIYe_w4XgYtRTjDPyJoMqVhrChBdOWI")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

async def fetch_web_api(endpoint, method, body=None):
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    url = f"https://api.spotify.com/{endpoint}"
    if method == "GET":
        response = requests.get(url, headers=headers)
    else:
        response = requests.request(method, url, headers=headers, json=body)
    return response.json()

async def get_top_tracks():
    return (await fetch_web_api("v1/me/top/tracks?time_range=long_term&limit=5", "GET"))["items"]

async def entop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        top_tracks = await get_top_tracks()
        if not top_tracks:
            await update.message.reply_text("En çok dinlenen şarkılar bulunamadı!")
            return
        track_list = "\n".join([f"{track['name']} by {', '.join(artist['name'] for artist in track['artists'])}" for track in top_tracks])
        await update.message.reply_text(f"En çok dinlediğiniz 5 şarkı:\n{track_list}")
    except Exception as e:
        await update.message.reply_text(f"Hata: {str(e)}")

async def oynat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Lütfen bir şarkı adı girin: /oynat <şarkı_adı>")
        return
    
    results = sp.search(q=query, type="track", limit=1)
    if not results["tracks"]["items"]:
        await update.message.reply_text("Şarkı bulunamadı!")
        return
    
    track = results["tracks"]["items"][0]
    track_name = track["name"]
    artist_name = track["artists"][0]["name"]
    search_query = f"{track_name} {artist_name}"
    
    youtube_results = YoutubeSearch(search_query, max_results=1).to_dict()
    if not youtube_results:
        await update.message.reply_text("YouTube'da şarkı bulunamadı!")
        return
    
    youtube_url = f"https://www.youtube.com{youtube_results[0]['url_suffix']}"
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "%(id)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        file_path = f"{info['id']}.mp3"
    
    audio = AudioSegment.from_mp3(file_path)
    if len(audio) > 300000:
        audio = audio[:300000]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
        audio.export(temp_file.name, format="ogg", codec="libopus")
        temp_file_path = temp_file.name
    
    with open(temp_file_path, "rb") as audio_file:
        await context.bot.send_voice(chat_id=chat_id, voice=audio_file, duration=len(audio)//1000)
    
    os.remove(file_path)
    os.remove(temp_file_path)
    
    voice_chat = await context.bot.get_chat(chat_id)
    if voice_chat.voice_chat:
        await context.bot.send_message(chat_id=chat_id, text=f"Şimdi oynatılıyor: {track_name} - {artist_name}")
    else:
        await context.bot.send_message(chat_id=chat_id, text="Sesli sohbet başlatılmadı, sadece ses dosyası gönderildi.")

async def settoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    token = " ".join(context.args)
    if not token:
        await update.message.reply_text("Lütfen Spotify kullanıcı token’ınızı girin: /settoken <token>")
        return
    global SPOTIFY_TOKEN
    SPOTIFY_TOKEN = token
    await update.message.reply_text("Spotify token’ı ayarlandı!")

async def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("oynat", oynat))
    application.add_handler(CommandHandler("entop", entop))
    application.add_handler(CommandHandler("settoken", settoken))
    await application.bot.set_my_commands([
        ("oynat", "Şarkıyı Spotify'dan arar ve oynatır"),
        ("entop", "En çok dinlenen 5 şarkıyı listeler"),
        ("settoken", "Spotify kullanıcı token’ını ayarlar")
    ])
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())