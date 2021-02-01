from __future__ import print_function
import datetime
import pickle

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pytz
import time
import playsound
from gtts import gTTS
import pyttsx3
import speech_recognition as sr
import subprocess

WAKE = "assistant"
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/gmail']
MONTHS = [datetime.date(2015, num, 1).strftime('%B').lower() for num in range(1, 13)]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_EXTS = ["st", "nd", "rd", "th"]
online = False


def calendar_auth():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('calendar', 'v3', credentials=creds)
    return service


def gmail_auth():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service


def textify(time_limit=None):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            r.adjust_for_ambient_noise(source)
            print("Listening!")
            voice = r.listen(source, time_limit)
            return r.recognize_google(voice).lower()
        except:
            return None


def voiceify(text, filename="voice.mp3"):
    global online
    try:
        tts = gTTS(text, lang="en")
        tts.save(filename)
        playsound.playsound(filename)
        os.remove(filename)
        online = True
    except:
        tts = pyttsx3.init()
        tts.setProperty("rate", 150)
        tts.say(text)
        tts.runAndWait()


def take_note(filename, text):
    print(f"Using \"{filename}\" as the filename and \"{notetext}\" as the text...")
    filename = "C:\\Users\\krish\\Desktop\\" + filename
    with open(filename, "w") as note:
        note.write(text)


def get_events(service, date=datetime.datetime.today(), number_of_events=None):
    utc = pytz.UTC
    min_time = datetime.datetime.combine(date, datetime.datetime.min.time()).astimezone(utc)
    max_time = datetime.datetime.combine(date, datetime.datetime.max.time()).astimezone(utc)
    if number_of_events is None:
        events_result = service.events().list(calendarId="primary", timeMin=min_time.isoformat(),
                                              timeMax=max_time.isoformat(), singleEvents=True,
                                              orderBy="startTime").execute()
    else:
        events_result = service.events().list(calendarId="primary", timeMin=min_time.isoformat(),
                                              timeMax=max_time.isoformat(), maxResults=number_of_events,
                                              singleEvents=True, orderBy="startTime").execute()

    events = events_result.get("items", [])
    if not events:
        summary = "No events found."
        print(summary)
        voiceify(summary)
        return summary
    else:
        summary = f"You have {len(events)} events on {DAYS[date.weekday()].title()} {MONTHS[date.month - 1].title()} {date.day}, {str(date.year)[:2]}" if len(
            events) > 1 else f"You have {len(events)} event on {DAYS[date.weekday()].title()} {MONTHS[date.month - 1].title()} {date.day}, {str(date.year)[:2]}"
        print(summary + f"{str(date.year)[2:]}")
        voiceify(summary + f"{str(date.year)[2:]}")
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            start_time = str(start.split("T")[1].split("-")[0])
            start_time_1 = int(start_time.split(":")[0])
            start_time_2 = start_time.split(":")[1]
            if int(start_time.split(":")[0]) < 12:
                start_time_2 += " AM"
            else:
                start_time_2 += " PM"
            start_time_1 = start_time_1 % 12
            if start_time_1 == 0:
                start_time_1 = 12
            event_desc = "You have an event named " + event["summary"] + " at " + f"{start_time_1}:{start_time_2}"
            print(event_desc)
            voiceify(event_desc)


def add_event(service, start, end, location=None):
    pass


def get_date(text):
    today = datetime.date.today()

    if "today" in text:
        return today

    day = None
    day_of_week = None
    month = None
    year = today.year

    for word in text.split():
        if word in MONTHS:
            month = MONTHS.index(word) + 1
        elif word in DAYS:
            day_of_week = DAYS.index(word)
        elif word.isdigit():
            day = int(word)
        else:
            for ext in DAY_EXTS:
                found = word.find(ext)
                if found > 0:
                    try:
                        day = int(word[:found])
                    except:
                        pass

    if month is not None and month < today.month: year += 1

    if month is None and day is not None:
        if day < today.day:
            month = today.month + 1
        else:
            month = today.month

    if month is None and day is None and day_of_week is not None:
        current_day_of_week = today.weekday()
        difference = day_of_week - current_day_of_week
        if difference < 0: difference += 7
        if text.count("next") > 0: difference += 7

        return today + datetime.timedelta(difference)
    if day is not None or month is not None or year is not None:
        return datetime.date(year, month, day)
    else:
        return datetime.datetime.today()


while True:
    text = textify()
    try:
        if WAKE in text:
            print("Hello!")
            voiceify("Hello!")
            if not online:
                message = "You are offline! Goodbye!"
                print(message)
                voiceify(message)
                quit()
            text = textify()
            print(f"You said: {text.title()}")
            if "hello" in text or "hi" in text:
                message = "Hello, Krishnan"
                print(message)
                voiceify(message)
            if "search the web" in text:
                subprocess.Popen(
                    ["C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome", str(text[18:]) + " "])
            elif "note" in text:
                message = "Please say the file name, or the current date and time will be used by default."
                print(message)
                voiceify(message)
                filename = textify(5)
                if filename is None:
                    filename = str(datetime.datetime.now())[:-7]
                    filename = filename.replace(":", "-")
                filename = filename.replace(" ", "_")
                filename += ".txt"
                message = "Please say the note you want to take."
                print(message)
                voiceify(message)
                notetext = textify().title()
                take_note(filename, notetext)
                message = "I have saved the note. Here it is in Notepad."
                print(message)
                voiceify(message)
                subprocess.Popen(["notepad.exe", "C:\\Users\\krish\\Desktop\\" + filename])
            elif "ask calendar" in text:
                service = calendar_auth()
                get_events(service, get_date(text))
            else:
                message = "I couldn't recognize this!!"
                print(message)
                voiceify(message)
    except:
        pass
