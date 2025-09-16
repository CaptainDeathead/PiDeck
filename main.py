import pygame as pg
import sys
import os

from time import sleep

# Apps
from apps.weather.weather import WeatherBase
# ----------------

pg.init()
pg.mouse.set_visible(False)

class Deck:
    SCREEN_WIDTH: int = 480
    SCREEN_HEIGHT: int = 320

    def __init__(self) -> None:
        self.screen = pg.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pg.FULLSCREEN)
        self.clock = pg.time.Clock()

        self.weather_app = WeatherBase(self.screen)

        self.main()

    def main(self) -> None:
        while 1:
            dt = self.clock.tick(10)

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit(0)
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_RETURN:
                        os.system("./apps/snake/build")

            self.weather_app.update()
            

if __name__ == "__main__":
    Deck()
