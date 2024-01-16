#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Written by:  Shell M. Shrader (https://github.com/synman/OctoPrint-MqttChamberTemperature/archive/main.zip)
# Copyright [2024] [Shell M. Shrader] - WTFPL

from __future__ import absolute_import
from pydoc import Helper
from octoprint.events import Events
from octoprint.logging.handlers import CleaningTimedRotatingFileHandler

import logging
import logging.handlers
import threading

import octoprint.plugin
from octoprint.schema.webcam import RatioEnum, Webcam, WebcamCompatibility
from octoprint.webcams import WebcamNotAbleToTakeSnapshotException


class BambuWebCamPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.WebcamProviderPlugin):
    # octoprint.plugin.WizardPlugin):

    def __init__(self):
        self._capture_mutex = threading.Lock()
        self._webcam_name = "classic"

    # ~~ TemplatePlugin API

    def get_assets(self):
        # return {
        #     "js": [
        #         "js/classicwebcam.js",
        #         "js/classicwebcam_settings.js",
        #         "js/classicwebcam_wizard.js",
        #     ],
        #     "less": ["less/classicwebcam.less"],
        #     "css": ["css/classicwebcam.css"],
        # }
        return {
            "js": [
                "js/classicwebcam.js",
                "js/classicwebcam_settings.js",
            ],
            "less": ["less/classicwebcam.less"],
            "css": ["css/classicwebcam.css"],
        }

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "template": "classicwebcam_settings.jinja2",
                "custom_bindings": True,
            },
            {
                "type": "webcam",
                "name": "Bambu Webcam",
                "template": "classicwebcam_webcam.jinja2",
                "custom_bindings": True,
                "suffix": "_real",
            },
            # {
            #     "type": "wizard",
            #     "name": "Bambu Webcam Wizard",
            #     "template": "classicwebcam_wizard.jinja2",
            #     "suffix": "_wizard",
            # },
        ]

    # ~~ WebcamProviderPlugin API

    def get_webcam_configurations(self):
        streamRatio = self._settings.get(["streamRatio"])
        if streamRatio == "4:3":
            streamRatio = RatioEnum.four_three
        else:
            streamRatio = RatioEnum.sixteen_nine
        webRtcServers = self._settings.get(["streamWebrtcIceServers"])
        cacheBuster = self._settings.get_boolean(["cacheBuster"])
        stream = self._get_stream_url()
        snapshot = self._get_snapshot_url()
        flipH = self._settings.get_boolean(["flipH"])
        flipV = self._settings.get_boolean(["flipV"])
        rotate90 = self._settings.get_boolean(["rotate90"])
        snapshotSslValidation = self._settings.get_boolean(["snapshotSslValidation"])

        try:
            streamTimeout = int(self._settings.get(["streamTimeout"]))
        except Exception:
            streamTimeout = 5

        try:
            snapshotTimeout = int(self._settings.get(["snapshotTimeout"]))
        except Exception:
            snapshotTimeout = 5

        return [
            Webcam(
                name=self._webcam_name,
                displayName="Bambu Webcam",
                flipH=flipH,
                flipV=flipV,
                rotate90=rotate90,
                snapshotDisplay=snapshot,
                canSnapshot=self._can_snapshot(),
                compat=WebcamCompatibility(
                    stream=stream,
                    streamTimeout=streamTimeout,
                    streamRatio=streamRatio,
                    cacheBuster=cacheBuster,
                    streamWebrtcIceServers=webRtcServers,
                    snapshot=snapshot,
                    snapshotTimeout=snapshotTimeout,
                    snapshotSslValidation=snapshotSslValidation,
                ),
                extras=dict(
                    stream=stream,
                    streamTimeout=streamTimeout,
                    streamRatio=streamRatio,
                    streamWebrtcIceServers=webRtcServers,
                    cacheBuster=cacheBuster,
                ),
            ),
        ]

    def _get_snapshot_url(self):
        return self._settings.get(["snapshot"])

    def _get_stream_url(self):
        return self._settings.get(["stream"])

    def _can_snapshot(self):
        snapshot = self._get_snapshot_url()
        return snapshot is not None and snapshot.strip() != ""

    def take_webcam_snapshot(self, _):
        snapshot_url = self._get_snapshot_url()
        if not self._can_snapshot():
            raise WebcamNotAbleToTakeSnapshotException(self._webcam_name)

        with self._capture_mutex:
            self._logger.debug(f"Capturing image from {snapshot_url}")
            r = requests.get(
                snapshot_url,
                stream=True,
                timeout=self._settings.get_int(["snapshotTimeout"]),
                verify=self._settings.get_boolean(["snapshotSslValidation"]),
            )
            r.raise_for_status()
            return r.iter_content(chunk_size=1024)

    # ~~ SettingsPlugin API

    def get_settings_defaults(self):
        return dict(
            flipH=False,
            flipV=False,
            rotate90=False,
            stream="",
            streamTimeout=5,
            streamRatio="16:9",
            streamWebrtcIceServers=["stun:stun.l.google.com:19302"],
            snapshot="",
            cacheBuster=False,
            snapshotSslValidation=True,
            snapshotTimeout=5,
        )

    def get_settings_version(self):
        return 1

    # def on_settings_migrate(self, target, current):
    #     if current is None:
    #         config = self._settings.global_get(["webcam"])
    #         if config:
    #             self._logger.info(
    #                 "Migrating settings from webcam to plugins.classicwebcam..."
    #             )

    #             # flipH
    #             self._settings.set_boolean(["flipH"], config.get("flipH", False))
    #             self._settings.global_remove(["webcam", "flipH"])

    #             # flipV
    #             self._settings.set_boolean(["flipV"], config.get("flipV", False))
    #             self._settings.global_remove(["webcam", "flipV"])

    #             # rotate90
    #             self._settings.set_boolean(["rotate90"], config.get("rotate90", False))
    #             self._settings.global_remove(["webcam", "rotate90"])

    #             # stream
    #             self._settings.set(["stream"], config.get("stream", ""))
    #             self._settings.global_remove(["webcam", "stream"])

    #             # streamTimeout
    #             self._settings.set_int(["streamTimeout"], config.get("streamTimeout", 5))
    #             self._settings.global_remove(["webcam", "streamTimeout"])

    #             # streamRatio
    #             self._settings.set(["streamRatio"], config.get("streamRatio", "16:9"))
    #             self._settings.global_remove(["webcam", "streamRatio"])

    #             # streamWebrtcIceServers
    #             self._settings.set(
    #                 ["streamWebrtcIceServers"],
    #                 config.get(
    #                     "streamWebrtcIceServers", ["stun:stun.l.google.com:19302"]
    #                 ),
    #             )
    #             self._settings.global_remove(["webcam", "streamWebrtcIceServers"])

    #             # snapshot
    #             self._settings.set(["snapshot"], config.get("snapshot", ""))
    #             self._settings.global_remove(["webcam", "snapshot"])

    #             # cacheBuster
    #             self._settings.set_boolean(
    #                 ["cacheBuster"], config.get("cacheBuster", False)
    #             )
    #             self._settings.global_remove(["webcam", "cacheBuster"])

    #             # snapshotTimeout
    #             self._settings.set_int(
    #                 ["snapshotTimeout"], config.get("snapshotTimeout", 5)
    #             )
    #             self._settings.global_remove(["webcam", "snapshotTimeout"])

    #             # snapshotSslValidation
    #             self._settings.set_boolean(
    #                 ["snapshotSslValidation"], config.get("snapshotSslValidation", True)
    #             )
    #             self._settings.global_remove(["webcam", "snapshotSslValidation"])

    # ~~ WizardPlugin API

    # def is_wizard_required(self):
    #     required = (
    #         not self._get_stream_url()
    #         or not self._get_snapshot_url()
    #         or not self._settings.global_get(["webcam", "ffmpegPath"])
    #     )
    #     firstrun = self._settings.global_get(["server", "firstRun"])
    #     return required and firstrun

    # def get_wizard_version(self):
    #     return 1


__plugin_name__ = "Bambu Lab Webcam Plugin"
__plugin_author__ = "Shell M. Shrader"
__plugin_description__ = "Provides a simple webcam viewer in OctoPrint's UI, images provided by an MJPEG webcam."

__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = BambuWebCamPlugin()


import os
import sys
import io
import time
import datetime
# import signal
# import threading
import traceback
import socket
import argparse
import json

import struct
import ssl

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from PIL import ImageFont, ImageDraw, Image
from io import BytesIO

exitCode = os.EX_OK
myargs = None
webserver = None
lastImage = None
encoderLock = None
encodeFps = 0.0
streamFps = {}
snapshots = 0

class WebRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global exitCode
        global myargs
        global streamFps
        global snapshots

        if self.path.lower().startswith("/?snapshot"):
            snapshots = snapshots + 1
            qs = parse_qs(urlparse(self.path).query)
            if "rotate" in qs:
                self.sendSnapshot(rotate=int(qs["rotate"][0]))
                return
            if myargs.rotate != -1:
                self.sendSnapshot(rotate=myargs.rotate)
                return
            self.sendSnapshot()
            return

        if self.path.lower().startswith("/?stream"):
            qs = parse_qs(urlparse(self.path).query)
            if "encodewait" in qs:
                myargs.encodewait = float(qs["encodewait"][0])
            showFps = myargs.showfps 
            if "showfps" in self.path.lower():
                showFps = True
            if "hidefps" in self.path.lower():
                showFps = False
            if "rotate" in qs:
                self.streamVideo(rotate=int(qs["rotate"][0]), showFps=showFps)
                return
            if myargs.rotate != -1:
                self.streamVideo(rotate=myargs.rotate, showFps=showFps)
                return
            self.streamVideo(showFps=showFps)
            return

        if self.path.lower().startswith("/?info"):
            self.send_response(200)
            self.send_header("Content-type", "text/json")
            self.end_headers()
            host = self.headers.get('Host')

            fpssum = 0.
            fpsavg = 0.

            for fps in streamFps:
                fpssum = fpssum + streamFps[fps]

            if len(streamFps) > 0:
                fpsavg = fpssum / len(streamFps)
            else:
                fpsavg = 0.

            jsonstr = ('{"stats":{"server": "%s", "encodeFps": %.2f, "sessionCount": %d, "avgStreamFps": %.2f, "sessions": %s, "snapshots": %d}, "config": %s}' % (host, self.server.getEncodeFps(), len(streamFps), fpsavg, json.dumps(streamFps) if len(streamFps) > 0 else "{}", snapshots, json.dumps(vars(myargs))))
            self.wfile.write(jsonstr.encode("utf-8"))
            return

        if self.path.lower().startswith("/?shutdown"):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            self.wfile.write(("<html><head><title>webcamd - A High Performance MJPEG HTTP Server</title></head><body>" +
                             "webcamd is shutting down now!</body></html>").encode("utf-8"))

            client = ("%s:%d" % (self.client_address[0], self.client_address[1]))
            print(f"{datetime.datetime.now()}: shutdown requested by {client}", flush=True)

            exitCode = os.EX_TEMPFAIL
            self.server.die()
            self.server.unlockEncoder()
            return

        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        host = self.headers.get('Host')
        self.wfile.write((
            "<html><head><title>webcamd - A High Performance MJPEG HTTP Server</title></head><body>Specify <a href='http://" + host +
            "/?stream'>/?stream</a> to stream, <a href='http://" + host +
            "/?snapshot'>/?snapshot</a> for a picture, or <a href='http://" + host +
            "/?info'>/?info</a> for statistics and configuration information</body></html>").encode("utf-8"))

    def log_message(self, format, *args):
        global myargs
        if not myargs.loghttp: return
        print(f"{datetime.datetime.now()}: {self.client_address[0]} {format % args}", flush=True)


    def streamVideo(self, rotate=-1, showFps = False):
        global myargs
        global streamFps

        try:
            if self.server.getImage() is None:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write((
                    "<html><head><title>webcamd - A High Performance MJPEG HTTP Server</title><meta http-equiv='refresh' content='5'>" +
                    "</head><body>Loading MJPEG Stream . . .</body></html>").encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-type", "multipart/x-mixed-replace; boundary=boundarydonotcross")
            self.end_headers()
        except Exception as e:
            print("%s: error in stream header %s: [%s]" % (datetime.datetime.now(), streamKey, e), flush=True)
            return

        frames = 0
        self.server.addSession()
        streamKey = ("%s:%d" % (socket.getnameinfo((self.client_address[0], 0), 0)[0], self.client_address[1]))

        fpsFont = ImageFont.truetype("SourceCodePro-Regular.ttf", 14)
        fmA, fmD = fpsFont.getmetrics()
        fmD = fmD * -1
        
        startTime = time.time()
        primed = False
        addBreaks = False

        while not self is None and not self.server is None and self.server.isRunning():
            if time.time() > startTime + 5:
                streamFps[streamKey] = frames / 5.
                # if showfps: print("%s: streaming @ %.2f FPS to %s - wait time %.5f" % (datetime.datetime.now(), streamFps[streamKey], streamKey, myargs.streamwait), flush=True)
                frames = 0
                startTime = time.time()
                primed = True

            jpg = self.server.getImage()

            if rotate != -1: jpg = jpg.rotate(rotate)

            if showFps and primed: 
                draw = ImageDraw.Draw(jpg)

                message = f"{streamKey}\n{datetime.datetime.now()}\nEncode: {round(self.server.getEncodeFps(), 1)} FPS"

                if streamKey in streamFps:
                    fpssum = 0.
                    fpsavg = 0.
                    for fps in streamFps:
                        fpssum = fpssum + streamFps[fps]
                    fpsavg = fpssum / len(streamFps)
                    message = message + f"\nStreams: {len(streamFps)} @ {round(streamFps[streamKey], 1)} FPS"

                bbox = draw.textbbox((0, fmD), message, font=fpsFont)
                draw.rectangle(bbox, fill="black")
                draw.text((0, fmD), message, font=fpsFont)

            try:
                tmpFile = BytesIO()
                jpg.save(tmpFile, format="JPEG")

                if not addBreaks:
                    self.wfile.write(b"--boundarydonotcross\r\n")
                    addBreaks = True
                else:
                    self.wfile.write(b"\r\n--boundarydonotcross\r\n")

                self.send_header("Content-type", "image/jpeg")
                self.send_header("Content-length", str(tmpFile.getbuffer().nbytes))
                self.send_header("X-Timestamp", "0.000000")
                self.end_headers()

                self.wfile.write(tmpFile.getvalue())

                time.sleep(myargs.streamwait)
                frames = frames + 1
            except Exception as e:
                # ignore broken pipes & connection reset
                if e.args[0] not in (32, 104): print(f"{datetime.datetime.now()}: error in stream {streamKey}:: [{e}]", flush=True)
                break

        if streamKey in streamFps: streamFps.pop(streamKey)
        self.server.dropSession()

    def sendSnapshot(self, rotate=-1):
        try:
            jpg = self.server.getImage()

            if jpg is None:
                self.send_error(425, "Too Early", "The server is not yet ready to serve requests.  Please try again momentarily.")
                return

            self.send_response(200)
            self.send_header("Content-type", "image/jpeg")
            self.send_header("Content-length", str(len(tmpFile.getvalue())))
            self.end_headers()

            self.server.addSession()

            if rotate != -1: jpg = jpg.rotate(rotate)
            fpsFont = ImageFont.truetype("SourceCodePro-Regular.ttf", 14)
            fmA, fmD = fpsFont.getmetrics()
            fmD = fmD * -1 

            draw = ImageDraw.Draw(jpg)

            message = f"{socket.getnameinfo((self.client_address[0], 0), 0)[0]}\n{datetime.datetime.now()}"            

            bbox = draw.textbbox((0, fmD), message, font=fpsFont)
            draw.rectangle(bbox, fill="black")
            draw.text((0, fmD), message, font=fpsFont)

            tmpFile = BytesIO()
            jpg.save(tmpFile, "JPEG")

            self.wfile.write(tmpFile.getvalue())
        except Exception as e:
            print(f"{datetime.datetime.now()}: error in snapshot: [{e}]", flush=True)

        self.server.dropSession()

def web_server_thread():
    global exitCode
    global myargs
    global webserver
    global encoderLock
    global encodeFps

    try:
        if myargs.ipv == 4:
            webserver = ThreadingHTTPServer((myargs.v4bindaddress, myargs.port), WebRequestHandler)
        else:
            webserver = ThreadingHTTPServerV6((myargs.v6bindaddress, myargs.port), WebRequestHandler)

        print(f"{datetime.datetime.now()}: web server started", flush=True)
        webserver.serve_forever()
    except Exception as e:
        exitCode = os.EX_SOFTWARE
        print(f"{datetime.datetime.now()}: web server error: [{e}]" , flush=True)

    print(f"{datetime.datetime.now()}: web server thread died", flush=True)

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    running = True
    sessions = 0

    def __init__(self, mixin, server):
        global encoderLock
        encoderLock.acquire()
        super().__init__(mixin, server)

    def getImage(self):
        global lastImage
        if not lastImage is None:
            return lastImage.copy()
        else:
            return None
        
    def die(self):
        super().shutdown()
        self.running = False
    def isRunning(self):
        return self.running
    def addSession(self):
        global encoderLock
        if self.sessions == 0 and encoderLock.locked(): encoderLock.release()
        self.sessions = self.sessions + 1
    def dropSession(self):
        global encoderLock
        global encodeFps
        global streamFps
        self.sessions = self.sessions - 1
        if self.sessions == 0 and not encoderLock.locked():
            encoderLock.acquire()
            encodeFps = 0.0
            streamFps = {}
    def unlockEncoder(self):
        global encoderLock
        if encoderLock.locked(): encoderLock.release()
    def getSessions(self):
        return self.sessions
    def getEncodeFps(self):
        global encodeFps
        return encodeFps

class ThreadingHTTPServerV6(ThreadingHTTPServer):
        address_family = socket.AF_INET6