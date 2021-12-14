# TheBlackmad
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import gpxpy.gpx
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt

filename = "<YOUR-GPX-FILE>"
api_key_weatherbit = "<YOUR-KEY-FROM-WEATHERBIT.IO>"
url_weatherbit = "https://api.weatherbit.io/v2.0/history/hourly?lat=%s&lon=%s&start_date=%s&end_date=%s&tz=local&key=%s"
weather = None
route_info = []
i=0
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

def get_hr (point):
	"""
        Returns the heart rate exercise at the GPX point. Heart rate is provided by the GPX equipment.
        If not exist 0 is returned

        Parameters
        ----------
        point: point where to get prower

        """

	for extension in point.extensions:
		if extension.tag != 'power':
			for exten in extension:
				if exten.tag == '{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr':
					return int(exten.text)

	return 0

def get_cad (point):
	"""
        Returns the cadence exercise at the GPX point. Cadence is provided by the GPX equipment.
        If not exist 0 is returned

        Parameters
        ----------
        point: point where to get cadence

        """

	for extension in point.extensions:
		if extension.tag != 'power':
			for exten in extension:
				if exten.tag == '{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}cad':
					return int(exten.text)

	return 0

def get_power(point):
	"""
        Returns the power exercise at the GPX point. Power is provided by the GPX equipment.
        If not exist 0 is returned

        Parameters
        ----------
        point: point where to get prower

        """

	for extension in point.extensions:
		if extension.tag == 'power':
			return int(extension.text)

	return 0

def get_slope (points, i):
	"""
        Returns the slope at a certain point in %

        Parameters
        ----------
        points: list of points
        i: 		point no to calculate slope from

        """

	if i == 0 or points[i].distance_3d(points[i-1]) == 0:
		return 0

	return 100 * (points[i].elevation - points[i - 1].elevation) / points[i].distance_3d(points[i - 1])

def get_weather(point):
	"""
        Returns the weather conditions at this specific GPX point. Weather is specific for that hour in this point.
        The weather information is retrieve via the web service from www.weatherbit.io

        Parameters
        ----------
        point: point where to get weather on

        """

	global weather

	# initialize variables if no weather has been retrieved so far.
	if weather == None:

		# Get the weather data for that position (lat, lon) at that specific date and hour (mins and secs are omitted
		lat = point.latitude
		lon = point.longitude
		start_date = "%s-%s-%s"%(point.time.year, point.time.month, point.time.day)
		t = point.time + datetime.timedelta(days=1)
		end_date = "%s-%s-%s" % (t.year, t.month, t.day)

		url = url_weatherbit%(lat, lon, start_date, end_date, api_key_weatherbit)
		response = requests.get(url)
		weather = json.loads(response.text)
#		print(url)
#		print('Response from WeatherBit API: ', weather)

	# The weather information is already retrieved
	data = weather['data']
	for entry in data:
		t = datetime.datetime.strptime(entry['timestamp_local'], '%Y-%m-%dT%H:%M:%S')

		# if same hour, return the weather conditions for that hour
		if point.time.year == t.year and point.time.month == t.month and point.time.day == t.day and point.time.hour == t.hour:
			return entry

	weather = None

	return None

def estimate_temp_altitude (ele, ele_base, temp_base, rh_base):
	"""
        Returns the estimated temperature at the given elevation.
        This is an estimated temperature given the relative humidity rh and temperature at a given base elevation.
        if the relative humidity is high, then the temp is assumed to change with altitude as 3.3°C / 1000mts
		otherwise at a dry day, it changes as per 5.6°C / 1000mts
		Source: https://newsonthesnow.com/news/does-elevation-affect-temperature/

        Parameters
        ----------
        ele: elevation at which to estimate temperature in m
        ele_base: elevation base in m
        temp_base: temperature at the ele_base elevation in °C
        rh_base: relative humidity at ele_base elevation in %

        """

	if rh_base > 65:
		factor = -3.3
	else:
		factor = -5.6

	return (temp_base + factor * (ele - ele_base) / 1000.0)


with open(filename, 'r') as gpx_file:
	gpx = gpxpy.parse(gpx_file)

gpx_mv = gpx.get_moving_data(raw=True, speed_extreemes_percentiles=0.05, ignore_nonstandard_distances=False)
print('Get moving distance: ', gpx_mv.moving_distance/1000)
print('Get moving time: ', gpx_mv.moving_time/60)
print('Get max speed: ', gpx_mv.max_speed)

print('Number of data Points: ', gpx.get_track_points_no())
print('Get extreme elevation values: ', gpx.get_elevation_extremes())
print('Get uphills/downhills: ', gpx.get_uphill_downhill())
print('Get duration: ', gpx.get_duration()/60)

for track in gpx.tracks:
	print('Track moving data: ', track.get_moving_data())
	for segment in track.segments:
		print('Segment moving data: ', segment.get_moving_data())
		print('Segment length 2D data: ', segment.length_2d())
		print('Segment length 3D data: ', segment.length_3d())
		print('Completing route info with further data . . .')

		for point in segment.points:

			if i != 0:
				#calculate the weather conditions for that point
				w = get_weather(point)

				# estimates the temperature at the given elevation
				temp_elev = estimate_temp_altitude (point.elevation, segment.points[0].elevation, w['temp'], w['rh'])

				route_info.append({
					'latitude': point.latitude,
					'longitude': point.longitude,
					'elevation': point.elevation,
					'speed': segment.get_speed(i) * 3.6,
					'slope': get_slope(segment.points, i),
					'power': get_power(point),
					'hr': get_hr(point),
					'cad': get_cad(point),
					'temp_base': w['temp'],
					'temp': temp_elev,
					'rh': w['rh'],
					'wind_spd': w['wind_spd'],
					'wind_dir': w['wind_dir'],
					'pres': w['pres'],
					'slp': w['slp'],
					'app_temp': w['app_temp'],
					'dewpt': w['dewpt'],
					'clouds': w['clouds'],
					'pod': w['pod'],
					'weather_desc': w['weather']['description'],
					'vis': w['vis'],
					'precip': w['precip'],
					'snow': w['snow'],
					'uv': w['uv']
					})

			i=i+1

# Create the dataframe and export to CSV
route_df = pd.DataFrame(route_info)
print(route_df.head(100))
print('Exporting to CSV . . .')
route_df.to_csv('GPX_Track.csv')
print ('Exporting to CSV . . . DONE')

# Plot diagram for temp and speed
plt.figure(figsize=(14,8))
plt.scatter(route_df['temp'], route_df['speed'])
plt.title('Relationship slope and speed', size=20)
plt.show()
