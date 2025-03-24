
import os
import sys
import configparser
import qgis.core
import qgis.PyQt
import osgeo.gdal
import re
import math
import pandas as pd
from zipfile import ZipFile
from datetime import datetime
from qgis.core import QgsProject
import shutil


def getDateTime():
    current_datetime = datetime.now()
    year = str(current_datetime.year)[-2:]
    month = str(current_datetime.month).zfill(2)
    day = str(current_datetime.day).zfill(2)
    hour = str(current_datetime.hour).zfill(2)
    minute = str(current_datetime.minute).zfill(2)
    second = str(current_datetime.second).zfill(2)
    return f"{year}{month}{day}_{hour}{minute}{second}"


def get_version_from_metadata():

    current_dir = os.path.dirname(
        os.path.abspath(__file__))  # path to the current file
    plugin_dir = os.path.dirname(current_dir)  # path to the plugin folder

    file_path = os.path.join(plugin_dir, 'metadata.txt')

    config = configparser.ConfigParser()
    config.read(file_path)

    if 'general' in config and 'version' in config['general']:
        return config['general']['version']

    return ""


def get_qgis_info():
    qgis_info = {}
    qgis_info['QGIS version'] = qgis.core.Qgis.QGIS_VERSION
    qgis_info['Qt version'] = qgis.PyQt.QtCore.QT_VERSION_STR
    qgis_info['Python version'] = sys.version
    qgis_info['GDAL version'] = osgeo.gdal.VersionInfo('RELEASE_NAME')
    qgis_info['Accessibility plugin version'] = get_version_from_metadata()
    return qgis_info


def is_valid_folder_name(folder_name):
    # check for the presence of invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    if re.search(invalid_chars, folder_name):
        return False

    # check the length of the folder name
    if len(folder_name) == 0 or len(folder_name) > 255:
        return False
    return True


def get_prefix_alias(PT, protocol, mode, timetable=None, field_name="", full_prefix=True):
    """
    Point/Region - P/R  (protocol 2,1)
    Forward/Backward - F/B (mode 1,2)
    Fixed/Scheduled - X/S  (false,true)
    """
    """
    P/C (Public/Car), F/T (From/To), X/S (Fixed/Scheduled time), A/R (Service Area/Region).
    """
    date_time = getDateTime()
    prefix = "P" if PT else "C"
    protocol_char = "R" if protocol == 1 else "A"
    mode_char = "F" if mode == 1 else "T"
    timetable_char = "" if timetable is None else ("S" if timetable else "X")

    result = f"{date_time}_{prefix}{mode_char}{timetable_char}{protocol_char}"
    if full_prefix:
        if field_name:
            result = f"{result}_{field_name}"
    
    return result


def zip_directory(directory):
    file_list = ['stops.txt', 'trips.txt', 'routes.txt',
                 'stop_times.txt', 'calendar.txt', 'rev_stop_times.txt']
    timestamp = getDateTime()
    zip_name = os.path.join(directory, f'gtfs_{timestamp}.zip')
    with ZipFile(zip_name, 'w') as zipf:
        for file_name in file_list:
            file_path = os.path.join(directory, file_name)
            if os.path.isfile(file_path):
                relative_path = os.path.relpath(file_path, directory)
                zipf.write(file_path, relative_path)
                os.remove(file_path)

def convert_meters_to_degrees(distance_in_meters, latitude):
    # length of one degree of longitude at a given latitude in meters
    meters_per_degree_longitude = 111320 * math.cos(math.radians(latitude))
    # convert distance from meters to degrees
    return abs(distance_in_meters / meters_per_degree_longitude)


def convert_distance_to_meters(distance_in_degrees, latitude):
    return distance_in_degrees * 111132.92 * math.cos(math.radians(latitude))

def time_to_seconds(t):
    if pd.isna(t):
        return None
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s

# Convert seconds to time string (e.g., total seconds -> HH:MM:SS)
def seconds_to_time(seconds):
    if not pd.notnull(seconds):  # Проверяем, что значение не None и не NaN
        return ""
    total_seconds = round(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

def check_file_parameters_accessibility ():
    project_directory = os.path.dirname(QgsProject.instance().fileName())
    parameters_path = os.path.join(project_directory, 'parameters_accessibility.txt')

    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(current_dir, 'config')
    source_path = os.path.join(config_path, 'parameters_accessibility_shablon.txt')
    if not os.path.exists(parameters_path):
        shutil.copy(source_path, parameters_path)