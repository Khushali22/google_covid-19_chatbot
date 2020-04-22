from flask import Flask, request, make_response
import json
import os
from flask_cors import cross_origin
from flask_mysqldb import MySQL
import datetime
from SendEmail.sendEmail import EmailSender
from logger import logger
from email_templates import template_reader
from geopy.geocoders import Nominatim
import requests
import pandas as pd
import folium
import pandas as pd
from folium.plugins import MarkerCluster # for clustering the markers

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'covid-19'

mysql = MySQL(app)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# geting and sending response to dialogflow
@app.route('/webhook', methods=['POST'])
@cross_origin()
def webhook():
    req = request.get_json(silent=True, force=True)
    result = req.get("queryResult")
    intent = result.get("intent").get('displayName')
    if (intent=='getStatsCovid-19'):
        res = processRequest(req)
    elif(intent=='Welcome'):
        res = welcome(req)
    elif(intent=='worldStatCorona'):
        res = worldData(req)
    elif(intent=='continueConversation'):
        res = continueConversation(req)
    elif(intent=='endConversation'):
        res = endConversation(req)
    # res = processRequest(req)
    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def welcome(req):
    sessionID=req.get('responseId')
    result = req.get("queryResult")
    user_says=result.get("queryText")
    fulfillmentText = "Welcome to the COVID-19 info chatbot! Get statistics and guidance regarding the current outbreak of coronavirus disease (COVID-19). I am here to help you. How am i assist you?"
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "User says: " + user_says, datetime.datetime.utcnow()))
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "Bot says: " + fulfillmentText, datetime.datetime.utcnow()))
    mysql.connection.commit()
    cur.close()
    return {
            "fulfillmentText": fulfillmentText
        }

@app.route('/hello')
def hello():
    return "Welcome!!"

# processing the request from dialogflow
def processRequest(req):
    sessionID=req.get('responseId')
    result = req.get("queryResult")
    user_says=result.get("queryText")
    parameters = result.get("parameters")
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "User says: " + user_says + "With parameters:- "+ str(parameters), datetime.datetime.utcnow()))
    mysql.connection.commit()
    cur.close()
    name=parameters.get("name")
    mobile_number = parameters.get("mobile_number")
    email=parameters.get("email")
    pin_code=parameters.get("pin_code")
    geolocator = Nominatim(user_agent="geoapiExercises")
    location = geolocator.geocode(pin_code)
    address_info = location.raw["display_name"]
    print(address_info)
    data_from_address = geolocator.geocode(address_info, addressdetails=True)
    address = data_from_address.raw["address"]
    print(address)
    country = address["country"]
    country_code = address["country_code"]
    if("state" in address.keys()):
        state = address["state"]
    elif("state_district" in address.keys()):
        state = address["state_district"]
    else:
        state = country
    if("city" in address.keys()):
        city = address["city"]
    elif("state_district" in address.keys()):
        city = address["state_district"]
    elif("city_district" in address.keys()):
        city = address["city_district"]
    else:
        city = country
    if city == "Ahmedabad District":
        city = "Ahmadabad"
    if(country == "India"):
        url = "https://api.covid19india.org/v2/state_district_wise.json"
        headers = {}
        response = requests.request("GET", url, headers=headers)
        res = next((sub for sub in json.loads(response.text) if sub['state'] == state), None)
        state_data = res
        city_data = next((sub for sub in state_data['districtData'] if sub['district'] in city), None)
        if city_data != None:
            total_confimred_cases_in_district = city_data["confirmed"]
            total_confimred_cases_in_state = sum(d['confirmed'] for d in state_data['districtData'] if d)
        else:
            total_confimred_cases_in_district = 0
            total_confimred_cases_in_state = 0
        print(total_confimred_cases_in_district,total_confimred_cases_in_state)

        email_sender=EmailSender()
        template= template_reader.TemplateReader()
        email_message=template.read_course_template("India_template")
        email_message = email_message.replace('User',name)
        email_message = email_message.replace('pin_code', pin_code)
        email_message = email_message.replace('state', state)
        email_message = email_message.replace('city', city)
        email_message = email_message.replace('total_No_cases_c', str(total_confimred_cases_in_district))
        email_message = email_message.replace('total_No_cases_s', str(total_confimred_cases_in_state))
        email_sender.send_email_to_student(email,email_message)
        fulfillmentText="We have sent the number of corona virus cases in your area and other relevant details to you via email.Do you have further queries?"
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "Bot says: " + fulfillmentText , datetime.datetime.utcnow()))
        mysql.connection.commit()
        cur.close()
        return {
            "fulfillmentText": fulfillmentText
        }
    else:
        url = "https://covid-19-data.p.rapidapi.com/country/code"

        querystring = {"format":"json","code":country_code}

        headers = {
            'x-rapidapi-host': "covid-19-data.p.rapidapi.com",
            'x-rapidapi-key': "e468d98724msh7380b7960df4c02p18c627jsnffbdc0763d43"
            }

        response = requests.request("GET", url, headers=headers, params=querystring)

        counntry_info = json.loads(response.text)
        confirmed = counntry_info[0]["confirmed"]
        recovered = counntry_info[0]["recovered"]
        critical = counntry_info[0]["critical"]
        deaths = counntry_info[0]["deaths"]
        email_sender=EmailSender()
        template= template_reader.TemplateReader()
        email_message=template.read_course_template("NotIndia_template")
        email_message = email_message.replace('User',name)
        email_message = email_message.replace('pin_code', pin_code)
        email_message = email_message.replace('Country', country)
        email_message = email_message.replace('total_No_cases_c', str(confirmed))
        email_message = email_message.replace('total_No_cases_r', str(recovered))
        email_message = email_message.replace('total_No_cases_t', str(critical))
        email_message = email_message.replace('total_No_cases_d', str(deaths))
        email_sender.send_email_to_student(email,email_message)
        fulfillmentText="We have sent the number of corona virus cases in your area and other relevant details to you via email.Do you have further queries?"
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "Bot says: " + fulfillmentText , datetime.datetime.utcnow()))
        mysql.connection.commit()
        cur.close()
        return {
            "fulfillmentText": fulfillmentText
        }


@app.route('/worldData')
def worldData(req):
    sessionID=req.get('responseId')
    result = req.get("queryResult")
    user_says=result.get("queryText")
    parameters = result.get("parameters")
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "User says: " + user_says + "With parameters:- "+ str(parameters), datetime.datetime.utcnow()))
    mysql.connection.commit()
    cur.close()
    name=parameters.get("name")
    email=parameters.get("email")
    url = " https://corona-api.com/countries"
    headers = {}
    response = requests.request("GET", url, headers=headers)

    data = json.loads(response.text)
    country = []
    country_code = []
    latitude =[]
    longitude = []
    population = []
    confirmed = []
    recoverd = []
    deaths = []
    for items in data["data"]:
        latitude.append(items["coordinates"]["latitude"])
        longitude.append(items["coordinates"]["longitude"])
        population.append(items["population"])
        country.append(items["name"])
        country_code.append(items["code"])
        confirmed.append(items["latest_data"]["confirmed"])
        recoverd.append(items["latest_data"]["recovered"])
        deaths.append(items["latest_data"]["deaths"])

    dict1 = {'country': country,'county_code': country_code, 'latitude': latitude, 'longitude': longitude,'population': population,'confirmed': confirmed,'recoverd': recoverd,'deaths': deaths}
    df = pd.DataFrame(dict1)

    # saving the dataframe
    df.to_csv('world_stats.csv')
    a = createMap()
    email_sender=EmailSender()
    template= template_reader.TemplateReader()
    email_message=template.read_course_template("Worldwide_Template")
    email_message = email_message.replace('User',name)
    email_message =  email_message.replace('corona-url',os.path.join(BASE_DIR, 'covid-19\email_templates\world_map.html'))
    email_sender.send_email_to_student(email,email_message)
    fulfillmentText="We have sent the visulization of corona effects world wide and other relevant details to you via email.Do you have further queries?"
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "Bot says: " + fulfillmentText , datetime.datetime.utcnow()))
    mysql.connection.commit()
    cur.close()
    return {
        "fulfillmentText": fulfillmentText
    }

def createMap():
    country_geo = 'world-countries.json'
    data = pd.read_csv('world_stats.csv')
    data = data.fillna(0)
    map = folium.Map(location=[20.5937, 78.9629], zoom_start=3)
    folium.Marker(location=[19.0760, 72.8777],popup='Welcome to <b>Mumbai</b>',tooltip = "Click for more").add_to(map)
    map.choropleth(geo_data="world-countries.json",
             data=data, # my dataset
             columns=['county_code', 'confirmed'], # zip code is here for matching the geojson zipcode, sales price is the column that changes the color of zipcode areas
             key_on='feature.id', # this path contains zipcodes in str type, this zipcodes should match with our ZIP CODE column
             fill_color='BuPu', fill_opacity=0.7, line_opacity=0.2,
             legend_name='Confirmed cases')
    marker_cluster = MarkerCluster().add_to(map)
    for i in range(data.shape[0]):
        location = [data['latitude'][i],data['longitude'][i]]
        tooltip = "Corona virus cases:{}<br> Total population: {}<br>".format(data["confirmed"][i], data['population'][i])

        folium.Marker(location, # adding more details to the popup screen using HTML
                  popup="""
                  <i>Country: </i> <br> <b>${}</b> <br> 
                  <i>Total confirmed cases: </i><b><br>{}</b><br>
                  <i>Total recovered cases: </i><b><br>{}</b><br>
                  <i>Total deaths: </i><b><br>{}</b><br>""".format(
                    data['country'][i],
                   data['confirmed'][i],
                    data['recoverd'][i],
                  data['deaths'][i]),
                  tooltip=tooltip).add_to(marker_cluster)
    print(os.path.join(BASE_DIR, 'covid-19\email_templates\world_map.html'))
    map.save(os.path.join(BASE_DIR, 'covid-19\email_templates\world_map.html'))
    return "map created"

def continueConversation(req):
    sessionID=req.get('responseId')
    result = req.get("queryResult")
    user_says=result.get("queryText")
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "User says: " + user_says , datetime.datetime.utcnow()))
    fulfillmentText="Tell me the query."
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "Bot says: " + fulfillmentText , datetime.datetime.utcnow()))
    mysql.connection.commit()
    cur.close()
    return {
        "fulfillmentText": fulfillmentText
    }

def endConversation(req):
    sessionID=req.get('responseId')
    result = req.get("queryResult")
    user_says=result.get("queryText")
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "User says: " + user_says , datetime.datetime.utcnow()))
    fulfillmentText="Thank you for contacting us.Have a good day! Bye!"
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO user_chat_history(sessionId,message, updated_time) VALUES (%s, %s, %s)", (sessionID, "Bot says: " + fulfillmentText , datetime.datetime.utcnow()))
    mysql.connection.commit()
    cur.close()
    return {
        "fulfillmentText": fulfillmentText
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("Starting app on port %d" % port)
    app.run(debug=False, port=port, host='0.0.0.0')
