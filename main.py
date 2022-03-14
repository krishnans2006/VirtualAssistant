from __future__ import print_function
import datetime
import pickle
from dotenv import load_dotenv

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pytz
from gtts import gTTS
import pyttsx3
import pygame
import requests

load_dotenv()

WAKE = "assistant"
SCOPES = ['https://www.googleapis.com/auth/calendar']
MONTHS = [datetime.date(2015, num, 1).strftime('%B').lower() for num in range(1, 13)]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_EXTS = ["st", "nd", "rd", "th"]


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


# def textify(time_limit=None):
#     r = sr.Recognizer()
#     with sr.Microphone() as source:
#         try:
#             r.adjust_for_ambient_noise(source)
#             print("Listening!")
#             voice = r.listen(source, time_limit)
#             return r.recognize_google(voice).lower()
#         except:
#             return None


def voiceify(text, filename="voice.mp3"):
    global online
    try:
        tts = gTTS(text, lang="en")
        tts.save(filename)
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        os.remove(filename)
    except Exception as e:
        print(e)
        tts = pyttsx3.init()
        tts.setProperty("rate", 150)
        tts.say(text)
        tts.runAndWait()


def get_events(service, date=datetime.datetime.today(), number_of_events=None):
    utc = pytz.UTC
    min_time = datetime.datetime.combine(date, datetime.datetime.now().timetz() if date == datetime.datetime.today() else datetime.datetime.min.time()).astimezone(utc)
    max_time = datetime.datetime.combine(date, datetime.datetime.max.time()).astimezone(utc)
    calendar_list = service.calendarList().list(pageToken=None).execute()
    print(len(calendar_list["items"]))
    events = []
    for calendar_list_entry in calendar_list['items']:
        print(f"Going through calendar {calendar_list_entry['kind']}")
        if number_of_events is None:
            events_result = service.events().list(calendarId=calendar_list_entry["id"], timeMin=min_time.isoformat(),
                                                  timeMax=max_time.isoformat(), singleEvents=True,
                                                  orderBy="startTime").execute().get("items", [])
            events.extend(events_result)
        else:
            events_result = service.events().list(calendarId=calendar_list_entry["id"], timeMin=min_time.isoformat(),
                                                  timeMax=max_time.isoformat(), maxResults=number_of_events,
                                                  singleEvents=True, orderBy="startTime").execute().get("items", [])
            events.extend(events_result)

    print(events)
    if not events:
        summary = "No events found."
        print(summary)
        voiceify(summary)
        return summary
    else:
        summary = f"You have {len(events)} events on {DAYS[date.weekday()].title()} {MONTHS[date.month - 1].title()} {date.day}, {str(date.year)[:2]}" if len(
            events) > 1 else f"You have {len(events)} event on {DAYS[date.weekday()].title()} {MONTHS[date.month - 1].title()} {date.day}, {str(date.year)[:2]}. They are:"
        print(summary + f"{str(date.year)[2:]}")
        voiceify(summary + f"{str(date.year)[2:]}")
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            try:
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
                date_str = " at " + f"{start_time_1}:{start_time_2}"
            except:
                date_str = ""
            if not event.get("summary"):
                event["summary"] = "School"
            event_desc = event["summary"] + date_str
            print(event_desc)
            voiceify(event_desc)


def get_tasks():
    tasks = requests.get(f"https://api.airtable.com/v0/{os.getenv('AIRTABLE_PROJECT')}/{os.getenv('AIRTABLE_TABLE')}?api_key={os.getenv('AIRTABLE_KEY')}&filterByFormula=NOT(%7BStatus%7D+%3D+%27Done%27)&maxRecords=10&sort%5B0%5D%5Bfield%5D=Due&sort%5B0%5D%5Bdirection%5D=asc").json()
    summary = f"Here are your next {5 if len(tasks['records']) > 5 else len(tasks['records'])} tasks"
    print(summary)
    voiceify(summary)
    for task in tasks["records"]:
        task = task["fields"]
        due = task['Due'].split("T")
        date = due[0]
        time = due[1].split("Z")[0].split(".")[0] if len(due) > 0 else None
        due_str = f"{datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%A %B %d')}"
        due_str += f"at {datetime.datetime.strptime(time, '%H:%M:%S').strftime('%I:%M %p')}" if time else ""
        event_desc = f"{task['Name']}. Is {task['Status']}, and is due on {due_str}"
        print(event_desc)
        voiceify(event_desc)

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
    if day is not None or month is not None:
        return datetime.date(year, month, day)
    return datetime.datetime.today()

if __name__ == "__main__":
    pygame.mixer.init()
    while True:
        text = input("Text: ")
        voiceify(text)
        if WAKE in text:
            print("Hello!")
            voiceify("Hello!")
            text = input("Text: ")
            print(f"You said: {text.title()}")
            if "hello" in text or "hi" in text:
                message = "Hello!"
                print(message)
                voiceify(message)
            elif "my events" in text:
                service = calendar_auth()
                get_events(service, get_date(text))
            elif "my tasks" in text:
                get_tasks()
            else:
                message = "I couldn't recognize this!!"
                print(message)
                voiceify(message)
