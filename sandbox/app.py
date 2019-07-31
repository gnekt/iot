from flask import Flask
from flask import jsonify
from xml.dom import minidom
from json import dumps
app = Flask(__name__)

@app.route('/plant/<int:id_plant>')
def get_plant(id_plant):
	mydoc = minidom.parse('C:/Users/dima9/sandbox/plant.xml')
	name = mydoc.getElementsByTagName('name')[id_plant-1].firstChild.data
	light_min = mydoc.getElementsByTagName('luce_min')[id_plant-1].firstChild.data
	hum_min = mydoc.getElementsByTagName('hum_terreno_max')[id_plant-1].firstChild.data
	hum_max = mydoc.getElementsByTagName('hum_terreno_min')[id_plant-1].firstChild.data
	return  jsonify(name=name,light_min=light_min,hum_max=hum_max,hum_min=hum_min)

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error('Server Error: %s', (error))
    return jsonify(name='',light_min='',hum_max='',hum_min='')

@app.errorhandler(404)
def page_not_found(error):
	app.logger.error('Page not found: %s', (request.path))
	return jsonify(name='',light_min='',hum_max='',hum_min='')


@app.route('/')
def index():
  return 'Server Works!'
  
