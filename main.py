from flask import Flask, logging, request  # import flask
import requests
import json
from timezonefinder import TimezoneFinder
import pytz
import datetime
from db import get_current_crowd

app = Flask(__name__)  # create an app instance

GOOGLE_API_KEY = ""
base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?location="

def perform_ordering_restaurant(result, occupancy_map):
    final_results = []
    for res in result:
        if res["place_id"] in occupancy_map:
            final_results.append(res)
            final_results[-1]["cur_occupancy"] = occupancy_map[res["place_id"]]
            if "rating" not in final_results[-1]:
                final_results[-1]["rating"] = 1
            if final_results[-1]["cur_occupancy"] <= 30:
                final_results[-1]["place_safety"] = "Very Safe"
            elif 30 < final_results[-1]["cur_occupancy"] <= 60:
                final_results[-1]["place_safety"] = "Safe"
            else:
                final_results[-1]["place_safety"] = "Hard to Maintain Social distancing"

    final_results = sorted(final_results, key=lambda X: [X["cur_occupancy"], -X["rating"]])
    return final_results

def perform_ordering_grocery(result, occupancy_map):
    final_results = []
    for res in result:
        if res["place_id"] in occupancy_map:
            final_results.append(res)
            final_results[-1]["cur_occupancy"] = occupancy_map[res["place_id"]]
            if "rating" not in final_results[-1]:
                final_results[-1]["rating"] = 1
            if final_results[-1]["cur_occupancy"] <= 40:
                final_results[-1]["place_safety"] = "Very Safe"
            elif 40 < final_results[-1]["cur_occupancy"] <= 70:
                final_results[-1]["place_safety"] = "Safe"
            else:
                final_results[-1]["place_safety"] = "Hard to Maintain Social distancing"

    final_results = sorted(final_results, key=lambda X: [X["cur_occupancy"], -X["rating"]])
    return final_results


def find_restaurants(lat, long, radius):
    subPart = "{},{}&radius={}&type=restaurant&key={}".format(lat, long, radius, GOOGLE_API_KEY)
    url = base_url + subPart
    # print(url)
    response = requests.get(url)
    jsn = response.json()
    result = []
    st = set()
    for place in jsn["results"]:
        result.append(place)
        st.add(place["place_id"])

    tf = TimezoneFinder()
    time_zone = tf.timezone_at(lng=long, lat=lat)
    timezone = pytz.timezone(time_zone)
    dt = datetime.datetime.utcnow()
    dt = timezone.utcoffset(dt)

    print(dt)
    occupancy_map = get_current_crowd(list(st), GOOGLE_API_KEY, dt)

    ordered_results = perform_ordering_restaurant(result, occupancy_map)

    my_json = {'results': ordered_results}

    return json.dumps(my_json), 200


def find_store(lat, long, radius):
    subPart1 = "{},{}&radius={}&type=supermarket&key={}".format(lat, long, radius, GOOGLE_API_KEY)
    subPart2 = "{},{}&radius={}&keyword=grocerystore&key={}".format(lat, long, radius, GOOGLE_API_KEY)
    url = base_url + subPart1
    # print(url)
    response1 = requests.get(url)
    response2 = requests.get(base_url + subPart2)
    json1 = response1.json()
    json2 = response2.json()
    result = []
    st = set()
    for place in json1["results"]:
        if place["place_id"] not in st:
            result.append(place)
            st.add(place["place_id"])
    for place in json2["results"]:
        if place["place_id"] not in st:
            result.append(place)
            st.add(place["place_id"])

    tf = TimezoneFinder()
    time_zone = tf.timezone_at(lng=long, lat=lat)
    timezone = pytz.timezone(time_zone)
    dt = datetime.datetime.utcnow()
    dt = timezone.utcoffset(dt)

    occupancy_map = get_current_crowd(list(st), GOOGLE_API_KEY, dt)

    ordered_results = perform_ordering_grocery(result, occupancy_map)

    # to_send = []
    my_json = {'results': ordered_results}
    # to_send.append(my_json)
    return json.dumps(my_json), 200


@app.route("/")  # at the end point /
def hello():  # call method hello
    return "Hello World!"  # which returns "hello world"


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


@app.route("/places", methods=['POST', 'GET'])
def places():
    body = request.json
    print(body)
    query_type = body["qtype"]
    lat = body["latitude"]
    long = body["longitude"]
    distance = int(body["range"])
    snd = str(lat) + " " + str(long) + " Result"
    print(snd)
    if query_type == "restaurant":
        return find_restaurants(lat, long, distance)
    else:
        return find_store(lat, long, distance)


if __name__ == "__main__":  # on running python app.py
    app.run(debug=True)  # run the flask app
