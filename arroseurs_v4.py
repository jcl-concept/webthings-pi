from __future__ import division, print_function
from webthing import (Action, Event, MultipleThings, Property, Thing, Value,
                      WebThingServer)
import logging
import random
import time
import tornado.ioloop
import uuid

import RPi.GPIO as GPIO

def toggle_gpio(self, pin,v):
    brightness = self.get_property('brightness')
    io_loop = tornado.ioloop.IOLoop.current()
    if not v == False :
        logging.debug('Launch a %d seconds timeout before shutdown of the sprinkler',brightness)
        self.timer = io_loop.call_later(
            brightness,
            self.timeout_shutdown_level,
        )
        logging.info('On-State of sprinkler %d is now %s for %s sec.',pin,v,brightness)
    else :
        if self.timer != 0:
            logging.debug('Cancel or timeout for sprinkler %d',pin)
            io_loop.remove_timeout(self.timer)
            logging.info('On-State of sprinkler %d is now %s',pin,v)
    GPIO.output(pin,not v)

def off_gpio(self,pin):
    logging.info('Force On-State of sprinkler %d to off ',pin,v)
    GPIO.output(pin,False)

def on_gpio(self,pin):
    logging.info('Force On-State of sprinkler %d to on ',pin,v)
    GPIO.output(pin,True)


class ArroseurGPIO(Thing):
    """Pilotage d'un arroseur via relais sur port GPIO."""

    def __init__(self, gpio: int, urn: str, title: str, description: str):
        Thing.__init__(
            self,
            urn,
            title,
            ['OnOffSwitch', 'Light'],
            description
        )

        self.add_property(
            Property(self,
                     'on',
                     Value(False, lambda v:
                         self.toggle_level(gpio,v)
                         ),
                     metadata={
                         '@type': 'OnOffProperty',
                         'title': 'On/Off',
                         'type': 'boolean',
                         'description': 'Sprinkler state',
                     }))

        self.add_property(
            Property(self,
                     'brightness',
                     Value(120, lambda v: logging.info('Timeout is now %d min. %d sec.',  v / 60 , v % 60)),
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Durée',
                         'type': 'integer',
                         'description': 'Time of sprinkle from 60 to 300 seconds',
                         'minimum': 60,
                         'maximum': 300,
                         'unit': 'second',
                     }))

    def toggle_level(self,pin,v):
        logging.debug('Toggle sprinkler')
        toggle_gpio(self,pin,v)

    def timeout_shutdown_level(self):
        logging.debug('Timeout Shutdown sprinkler')
        self.set_property('on', False)

    def cancel_update_level_task(self):
        if self.timer != 0:
            io_loop = tornado.ioloop.IOLoop.current()
            io_loop.remove_timeout(self.timer)


class ArroseurTournantGPIO(ArroseurGPIO):

    def __init__(self, gpio: int, urn: str, title: str, description: str):
        Thing.__init__(
            self,
            urn,
            title,
            ['OnOffSwitch', 'Light'],
            description
        )

        ArroseurGPIO.__init__(self, gpio, urn, title, description)

        self.listofcolors = ['#89d8f8','#2078f3','#6841d8','#640156','#eb0b19','#fc7223']
        self.index = 5
        self.add_property(
            Property(self,
                     'color',
                     Value(self.listofcolors[ self.index ], lambda v:
                         logging.info('New color : %s', v)
                         ),
                     metadata={
                         '@type': 'ColorProperty',
                         'title': 'Couleur',
                         'type': 'string',
                         'description': 'Couleur du prochain arroseur',
                     }))

        self.add_property(
            Property(self,
                     'valindex',
                     Value(0, lambda v: self.update_index(v)),
                     metadata={
                         '@type': 'LevelProperty',
                         'title': 'Index',
                         'type': 'integer',
                         'description': 'Index courant de l\'arrosage',
                         'minimum': 0,
                         'maximum': 5,
                         'unit': 'second',
                     }))

    def increment_index(self):
        self.index = (self.index + 1) % len(self.listofcolors)
        self.set_property('valindex', self.index)
        logging.debug('Increment index to %d',self.index)

    def update_index(self,v):
        self.index = v
        self.set_property('color', self.listofcolors[ self.index ])
        logging.debug('Update index to %d',self.index)


def run_server():
    
    # Initialisation des ports GPIO
    logging.info('Initialisation des arroseurs.')
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    pins = [4,17,27,22,18,23,24,25]
    for pin in pins:
        GPIO.setup(pin,GPIO.OUT)
        GPIO.output(pin,1)

    # Create a thing that represents a l'arroseur sur le GPIO 04
    arroseur17 = ArroseurGPIO(17,'urn:dev:ops:arroseurs-gpio-17', 'Relais 17', 'Arroseur 17')
    arroseur27 = ArroseurGPIO(27,'urn:dev:ops:arroseurs-gpio-27', 'Relais 27', 'Arroseur 27')
    arroseur22 = ArroseurGPIO(22,'urn:dev:ops:arroseurs-gpio-22', 'Relais 22', 'Arroseur 22')
    arroseur18 = ArroseurGPIO(18,'urn:dev:ops:arroseurs-gpio-18', 'Relais 18', 'Arroseur 18')
    arroseur23 = ArroseurGPIO(23,'urn:dev:ops:arroseurs-gpio-23', 'Relais 23', 'Arroseur 23')
    arroseur24 = ArroseurGPIO(24,'urn:dev:ops:arroseurs-gpio-24', 'Relais 24', 'Arroseur 24')

    arroseur04 = ArroseurTournantGPIO( 4,'urn:dev:ops:arroseurs-gpio-04', 'Relais 04', 'Arroseur 04')
    arroseur25 = ArroseurTournantGPIO(25,'urn:dev:ops:arroseurs-gpio-25', 'Relais 25', 'Arroseur 25')

    # If adding more than one thing, use MultipleThings() with a name.
    # In the single thing case, the thing's name will be broadcast.
    server = WebThingServer(MultipleThings([arroseur04, arroseur17, arroseur27, arroseur22, arroseur18, arroseur23, arroseur24, arroseur25],
                            'ArroseursDevice'),
                            port=8888)
    try:
        logging.info('starting the server')
        server.start()
    except KeyboardInterrupt:
        # logging.debug('canceling the sensor update looping task')
        # sensor.cancel_update_level_task()
        logging.info('stopping the server')
        server.stop()
        logging.info('done')


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s %(message)s"
    )
    run_server()
