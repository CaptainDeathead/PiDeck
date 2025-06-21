import pygame as pg
import requests
import math
import pytz

from random import randint
from datetime import datetime
from datetime import time as dtime
from astral import LocationInfo
from astral.sun import sun
from io import BytesIO
from threading import Thread
from time import strftime, time, localtime
from typing import Tuple, List, Dict

class WeatherAPI:
    ZOOM = 8

    def __init__(self) -> None:
        with open("apps/weather/key.txt") as f:
            self.api_key = f.read()

        #self.get_location()
        self.lat = -31.9514
        self.lon = 115.8617

        self.city = "Perth"

        self.CURR_WEATHER_DATA_URL = f"https://api.openweathermap.org/data/2.5/weather?lat={self.lat}&lon={self.lon}&appid={self.api_key}"
        self.FORECAST_WEATHER_DATA_URL = f"https://api.openweathermap.org/data/2.5/forecast?lat={self.lat}&lon={self.lon}&appid={self.api_key}"

        x, y = self.latlon_to_tile_coords(self.lat, self.lon, self.ZOOM)
        self.x = x
        self.y = y

        self.BASE_MAP_URL = f"https://tile.openstreetmap.org/{self.ZOOM}/X/Y.png"
        self.WEATHER_MAPS_DATA_URL = f"https://tile.openweathermap.org/map/LAYER/{self.ZOOM}/X/Y.png?appid={self.api_key}"
        self.ICON_URL = f"https://openweathermap.org/img/wn/ICON_ID@4x.png"

        headers = {
            "User-Agent": "PiDeck/1.0 (unstableplazma@gmail.com)"
        }

        self.BASE_MAP = pg.Surface((256*3, 256*2), pg.SRCALPHA)

        for x in range(-1, 2):
            for y in range(2):
                tx = str(self.x + x)
                ty = str(self.y + y)
                img = pg.image.load(BytesIO(requests.get(self.BASE_MAP_URL.replace("X", tx).replace("Y", ty), headers=headers).content)).convert_alpha()
                self.BASE_MAP.blit(img, (256 * (x+1), 256 * y))

    def get_location(self) -> None:
        location = requests.get("http://ipinfo.io/json").json()
        
        self.city = location["city"]
        lat, lon = location["loc"].split(',')
        self.lat, self.lon = float(lat), float(lon)

    def latlon_to_tile_coords(self, lat: float, lon: float, zoom: float) -> Tuple[float, float]:
        """Converts latitude and longitude to slippy map tile coordinates (x, y) at the given zoom level."""
        lat_rad = math.radians(lat)
        n = 2 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return x, y

    def curr_weather(self) -> Dict[str, any]:
        return requests.get(self.CURR_WEATHER_DATA_URL).json()

    def forecast(self) -> List[Dict[str, any]]:
        return requests.get(self.FORECAST_WEATHER_DATA_URL).json()["list"]

    def weather_map(self, layer: str) -> pg.Surface:
        """layers: clouds_new, precipitation_new, temp_new"""
        image = self.BASE_MAP.copy()

        print(f"Loading {layer} map...")
        for x in range(-1, 2):
            for y in range(2):
                tx = str(self.x + x)
                ty = str(self.y + y)
                img = pg.image.load(BytesIO(requests.get(self.WEATHER_MAPS_DATA_URL.replace("LAYER", layer).replace("X", tx).replace("Y", ty)).content)).convert_alpha()
                image.blit(img, (256 * (x+1), 256 * y))

                print(x, y)

        return pg.transform.smoothscale(image, (480, 320))

    def get_icon(self, icon_id: str) -> pg.Surface:
        return pg.image.load(BytesIO(requests.get(self.ICON_URL.replace("ICON_ID", icon_id)).content)).convert_alpha()

class Raindrop:
    def __init__(self, screen: pg.Surface, x: int, y: int) -> None:
        self.screen = screen

        surface = pg.Surface((4, 10), pg.SRCALPHA)
        surface.fill((74, 101, 131))
        self.surface = pg.transform.rotate(surface, -45)

        self.rect = self.surface.get_rect()
        self.rect.x = x
        self.rect.y = y

    def draw(self) -> None:
        self.screen.blit(self.surface, self.rect)
        self.rect.move_ip(-1, 1)

        if self.rect.x + self.rect.w <= 0 or self.rect.y >= 320:
            self.rect.x = randint(0, int(480 * 1.6))
            self.rect.y = randint(-320, 320)

class WeatherBase:
    NUM_RAINDROPS: int = 60

    def __init__(self, screen: pg.Surface) -> None:
        self.screen = screen
        self.weather_api = WeatherAPI()

        self.last_update = 0

        self.fonts = {
            60: pg.font.SysFont(None, 60),
            40: pg.font.SysFont(None, 40),
            35: pg.font.SysFont(None, 35),
            30: pg.font.SysFont(None, 30),
            25: pg.font.SysFont(None, 25),
            20: pg.font.SysFont(None, 20),
            15: pg.font.SysFont(None, 15),
            10: pg.font.SysFont(None, 10)
        }

        self.raining = False
        self.surface = pg.Surface((480, 320))
        self.raindrops = []

        self.update_sun_info()

    def set_rain(self, on: bool) -> None:
        if on == self.raining: return

        if on:
            self.raindrops = [Raindrop(self.screen, randint(0, int(480 * 1.6)), randint(-320, 320)) for i in range(self.NUM_RAINDROPS)]
            self.raining = True
        else:
            self.raindrops = []
            self.raining = False

    def seconds_since_midnight(self, dt: datetime) -> int:
        return dt.hour * 3600 + dt.minute * 60 + dt.second

    def update_sun_info(self) -> None:
        city = LocationInfo(self.weather_api.city, self.weather_api.city, "Australia/Perth", self.weather_api.lat, self.weather_api.lon)

        timezone = pytz.timezone(city.timezone)
        now = datetime.now(timezone)
        self.day = now.strftime("%A")

        s = sun(city.observer, date=now, tzinfo=timezone)

        self.sunrise = s['sunrise']
        self.sunset = s['sunset']

        day_start = timezone.localize(datetime.combine(now.date(), dtime.min))
        day_end = timezone.localize(datetime.combine(now.date(), dtime.max))

        day_secs = (day_end - day_start).total_seconds()
        elapsed_secs = (now - day_start).total_seconds()

        self.day_percent = (elapsed_secs / day_secs)

        self.sunrise_percent = self.seconds_since_midnight(self.sunrise) / day_secs
        self.sunset_percent = self.seconds_since_midnight(self.sunset) / day_secs

    def generate_day_colors(self, weather_description: str) -> List[Tuple[float, pg.Color]]:
        if weather_description in ("clear sky", "few clouds", "scattered clouds", "broken clouds"):
            day_color = (62, 179, 214)
            evening_color = (212, 127, 0)
        elif weather_description in ("shower rain", "rain", "thunderstorm", "mist"):
            day_color = (140, 140, 140)
            evening_color = (194, 158, 105)
        else:
            day_color = (200, 200, 200)
            evening_color = (194, 158, 105)
            
        night_color = (30, 30, 30)

        true_midday = (self.sunrise_percent + self.sunset_percent) / 2

        day_colors = [
            (0.00, night_color),
            (self.sunrise_percent - 0.025, night_color),
            (self.sunrise_percent, evening_color),
            (self.sunrise_percent + 0.025, day_color),
            (self.sunset_percent - 0.025, day_color),
            (self.sunset_percent, evening_color),
            (self.sunset_percent + 0.025, night_color)
        ]

        return day_colors

    def lerp_color(self, c1: Tuple[int], c2: Tuple[int], t: float) -> Tuple[int]:
        return tuple(
            int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)
        )

    def color_from_day_percent(self, weather_description: str) -> pg.Color:
        day_colors = self.generate_day_colors(weather_description)

        for i in range(len(day_colors) - 1):
            p1, c1 = day_colors[i]
            p2, c2 = day_colors[i + 1]

            if p1 <= self.day_percent and self.day_percent <= p2:
                t = (self.day_percent - p1) / (p2 - p1)
                return self.lerp_color(c1, c2, t)

        return day_colors[-1][1] # fallback

    def deg_to_compass(self, deg: int) -> str:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = int((deg + 22.5) / 45) % 8

        return directions[index]

    def get_next_day(self, curr_day: str) -> str:
        days = ["Monday", "Tuesday", "Wednessday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[days.index(curr_day) + 1]

    def blit_centered(self, surface: pg.Surface, pos: Tuple[int, int]) -> pg.Rect:
        x, y = pos
        return self.surface.blit(surface, (x - surface.width / 2, y - surface.height / 2))

    def update(self) -> None:
        if strftime("%M", localtime()) != self.last_update: 
            print("redrawing")
            self.draw()
            self.last_update = strftime("%M", localtime())

        self.screen.blit(self.surface)

        for raindrop in self.raindrops:
            raindrop.draw()

        pg.display.flip()

    def draw(self) -> None:
        self.update_sun_info()

        curr_weather = self.weather_api.curr_weather()
        forecast = self.weather_api.forecast()

        self.surface.fill(self.color_from_day_percent(curr_weather["weather"][0]["description"]))

        time_lbl = self.fonts[60].render(strftime("%H:%M", localtime()), True, (255, 255, 255))
        self.surface.blit(time_lbl, (390 - time_lbl.width / 2, 250 - time_lbl.height / 2))

        day_pct_lbl = self.fonts[35].render(f"{(self.day_percent * 100):.2f}%", True, (220, 220, 220))
        self.surface.blit(day_pct_lbl, (390 - day_pct_lbl.width / 2, 290 - time_lbl.height / 2 + day_pct_lbl.height / 4))

        # Now
        self.blit_centered(self.fonts[35].render("Now", True, (255, 255, 255)), (90, 40))
        self.blit_centered(self.weather_api.get_icon(curr_weather['weather'][0]['icon']), (90, 120))

        self.blit_centered(self.fonts[30].render(curr_weather["weather"][0]['main'].capitalize(), True, (255, 255, 255)), (90, 200))
        self.blit_centered(self.fonts[30].render(f"Rain: {(forecast[0]['pop'] * 100):.0f}%", True, (255, 255, 255)), (90, 225))
        self.blit_centered(self.fonts[30].render(f"Wind: {(curr_weather['wind']['speed'] * 3.6):.0f}km {self.deg_to_compass(curr_weather['wind']['deg'])}", True, (255, 255, 255)), (90, 250))

        temp = curr_weather["main"]["temp"] - 273.15
        self.blit_centered(self.fonts[30].render(f"Temp: {temp:.1f}C", True, (255, 255, 255)), (90, 275))

        if "rain" in curr_weather["weather"][0]["main"].lower():
            print("Raining")
            self.set_rain(True)
        else:
            print("Not raining")
            self.set_rain(False)

        # Forecast
        o = 0
        while 1:
            dt_txt = forecast[o+1]["dt_txt"]
            dt = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = dt - now
            seconds = diff.total_seconds()
            hours = int(round(seconds / 3600, 0))
            
            if hours < 1:
                o += 1
            else: break

        for index in range(4):
            i = index + o
            x = 120 + 80 * (index+1)

            dt_txt = forecast[i+1]["dt_txt"]
            dt = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = dt - now
            seconds = diff.total_seconds()
            hours = int(round(seconds / 3600, 0))
            
            self.blit_centered(self.fonts[30].render(f"{hours}h", True, (255, 255, 255)), (x, 40))
            print(forecast[i+1])
            self.blit_centered(pg.transform.smoothscale_by(self.weather_api.get_icon(forecast[i+1]['weather'][0]['icon']), 0.4), (x, 100))

            self.blit_centered(self.fonts[30].render(forecast[i+1]['weather'][0]['main'].capitalize(), True, (255, 255, 255)), (x, 160))
            self.blit_centered(self.fonts[30].render(f"{(forecast[i+1]['pop'] * 100):.0f}%", True, (255, 255, 255)), (x, 182))
            temp = forecast[i+1]["main"]["temp"] - 273.15
            self.blit_centered(self.fonts[30].render(f"{temp:.1f}C", True, (255, 255, 255)), (x, 204))

        #pg.image.save(self.weather_api.weather_map('clouds_new'), 'cloud.png')
        #pg.image.save(self.weather_api.weather_map('precipitation_new'), 'rain.png')
        #pg.image.save(self.weather_api.weather_map('temp_new'), 'temp.png')