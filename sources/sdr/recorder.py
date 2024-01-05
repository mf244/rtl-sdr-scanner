#!/usr/bin/python3

import datetime
import logging
import os
import sdr.tools
import subprocess
import wave
import time

def record(device, frequency, power, config, **kwargs):
    logger = logging.getLogger("sdr")
    logger.info("start recording %s" % sdr.tools.format_frequency_power(frequency, power))
    ppm_error = str(kwargs["ppm_error"])
    tuner_gain = str(kwargs["tuner_gain"])
    squelch = str(kwargs["squelch"])
    dir = kwargs["wav_directory"]
    min_recording_time = kwargs["min_recording_time"]
    max_silence_time = kwargs["max_silence_time"]
    samples_rate = kwargs["samples_rate"]
    modulation = config["modulation"]

    now = datetime.datetime.now()
    dir = "%s/%04d-%02d-%02d" % (dir, now.year, now.month, now.day)
    os.makedirs(dir, exist_ok=True)
    filename = "%s/%02d_%02d_%02d_%09d.wav" % (dir, now.hour, now.minute, now.second, frequency)

    device.close()

    p1 = subprocess.Popen(
        ["rtl_fm", "-p", ppm_error, "-g", tuner_gain, "-M", modulation, "-f", str(frequency), "-s", str(samples_rate), "-l", squelch],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=True,
    )

    frames = b''  # Initialize an empty byte string for frames

    try:
        with wave.open(filename, "wb") as wave_file:
            wave_file.setnchannels(1)  # Assuming mono
            wave_file.setsampwidth(2)  # Assuming 16-bit
            wave_file.setframerate(samples_rate)

            start_time = time.time()

            while True:
                data = p1.stdout.read(1024)  # Adjust the buffer size as needed
                if not data:
                    break
                frames += data
                wave_file.writeframes(data)

                # Check for silence and stop if needed
                if time.time() - start_time > max_silence_time:
                    break

    except Exception as e:
        logger.error("Error during recording: %s" % str(e))
    finally:
        p1.terminate()
        p1.wait()

    if len(frames) > 0:
        with wave.open(filename, "r") as f:
            frames = f.getnframes()
            rate = f.getframerate()
            length = frames / float(rate)
            logger.info("recording time: %.2f seconds" % length)

            if length < min_recording_time:
                os.remove(filename)
                logger.warning("recording time too short, removing")

    device.open()
    device.ppm_error = kwargs["ppm_error"]
    device.gain = kwargs["tuner_gain"]
    device.sample_rate = kwargs["samples_rate"]