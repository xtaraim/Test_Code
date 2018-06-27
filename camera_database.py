# -*- coding: utf-8 -*-
'''
Filename: camera_database.py
Description: This module handles the creation and updation of the database.
All MySQL database operations are present in this module
'''

import os
import sys
import json

import MySQLdb as mdb
import _mysql_exceptions	

import config

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")

# For developer mode only
if __name__ == '__main__':
	# Set base directory
	config.set_base_dir(os.path.dirname(os.path.realpath(__file__)))

	# Set resource directory
	config.set_resource_dir()

	# Initialize configurations
	config.config_init()

from utils import bgcolors

GLOBAL_HOST = config.get_config('camera_database', 'GLOBAL_HOST')
GLOBAL_USER = config.get_config('camera_database', 'GLOBAL_USER') 
GLOBAL_PWD = config.get_config('camera_database', 'GLOBAL_PWD')

class CameraDatabase():
	
	def __init__(self, db_name, db_table, host=GLOBAL_HOST, user=GLOBAL_USER, password=GLOBAL_PWD, verbose=False):
		self.DB_HOST = host
		self.DB_USER = user
		self.DB_PWD = password	
		self.DB_NAME = db_name
		self.DB_TABLE = db_table
		self.DB_SUCCESS = False
		self.VERBOSE = verbose

		# Check if MySQL server is running
		# TODO: Handle the error
		if not self.test_server():
			print bgcolors.FAIL + bgcolors.BOLD + 'ERROR: Cannot access MySQL server\n' + bgcolors.ENDC
			self.DB_SUCCESS = False
			sys.exit(1)
		else: self.DB_SUCCESS = True

		# Create the database
		self.create_db()

		# Create a table in the database
		self.create_table()

	def execute(self, command, data='', db_exists=True):
		'''Connect to MySQL server and execute the command'''

		# Connect to database server
		if db_exists: db = mdb.connect(self.DB_HOST, self.DB_USER, self.DB_PWD, self.DB_NAME)
		else: db = mdb.connect(host=self.DB_HOST, user=self.DB_USER, passwd=self.DB_PWD)

		# Database cursor
		cursor = db.cursor()

		# Display MySQL command
		# TODO: Replace with logger
		if self.VERBOSE:
			print 'mysql> {0};'.format(command)
			if data: print 'data> {0}'.format(data)

		# Execute MySQL command
		ret = False
		results = []
		try: 
			ret = cursor.execute(command, data)
			for result in list(cursor): 
				results.append(list(result))
		# TODO: Handle the error
		except Exception as e:
			if 'Duplicate entry' in str(e): print bgcolors.BOLD + bgcolors.WARNING + '\nWARNING: Entry with primary key already exists' + bgcolors.ENDC

		# Commit changes
		db.commit()

		# Disconnect from database server
		db.close()

		# Return status and fetched data
		if self.VERBOSE:
			print 'ret>', ret
			print 'results>', results, '\n'
		return ret, results

	def test_server(self):
		'''Test if database is setup and MySQL server is running'''
		try:
			ret, results = self.execute('SELECT VERSION()', db_exists=False)
			ver = results[0][0]
			# TODO: Log this version
			if self.VERBOSE:
				print 'Database version: %s' % ver
			return True

		# TODO: Log this error
		except Exception as e:	
			print e
			return False

	def create_db(self):
		'''Create the database if it doesn't exist'''
		return self.execute('CREATE DATABASE IF NOT EXISTS %s'%(self.DB_NAME), db_exists=False)

	def remove_db(self):
		'''Delete the default database'''
		return self.execute('DROP DATABASE IF EXISTS %s'%(self.DB_NAME), db_exists=False)

	def create_table(self):
		'''Create the default camera table'''
		return self.execute('CREATE TABLE IF NOT EXISTS %s (ID INT, JSON BLOB NOT NULL, PRIMARY KEY (ID))' \
			% (self.DB_TABLE))		

	def insert(self, cam_id, cam_dict):
		'''Insert an entry into the default mysql table'''
		cam_json = json.dumps(cam_dict)
		return self.execute('INSERT INTO ' + self.DB_TABLE + ' (ID, JSON) VALUES (%s, %s)',
			(str(cam_id), cam_json))

	def edit(self, cam_id, cam_dict):
		'''Edit a camera'''
		cam_json = json.dumps(cam_dict)
		return self.execute('UPDATE ' + self.DB_TABLE + ' SET JSON=%s WHERE ID=%s',
			(cam_json, str(cam_id)))

	def delete(self, cam_id):
		'''Delete a camera'''
		return self.execute('DELETE FROM %s WHERE ID=%d'%(self.DB_TABLE, cam_id))

	def retrieve(self, cam_id=None):
		'''Retrieve all camera info or single camera info if cam_id is given'''
		dict_list = []
		if cam_id is not None:
			ret, results = self.execute('SELECT * FROM %s WHERE ID=%d'%(self.DB_TABLE, cam_id))
		else:
			ret, results = self.execute('SELECT * FROM %s'%(self.DB_TABLE))
		for result in results:
			dict_list.append((result[0], json.loads(result[1])))
		return dict_list

	def get_max_id(self):
		'''Returns the maximum value ID in the table'''
		ret, results = self.execute('SELECT MAX(ID) FROM %s'%(self.DB_TABLE))
		return results[0][0]
		
# Unit Test
if __name__ == '__main__':

	# Delete existing database entries
	cdb = CameraDatabase('camDB', 'camTable')
	cdb.remove_db()
	cdb = CameraDatabase('camDB', 'camTable')

	# Load data from JSON file
	data = json.load(open('cameras.json'))

	allow_all = False
	allowed = range(1,2000)

	# Add entries into database from JSON file
	for d in data:
		camID = d['id']
		blob = d['blob']

		if not allow_all:
			if camID not in allowed:
				continue

		print 'Adding ID: %d | Name: %s | Floor: %s'%(d['id'], d['blob']['camera_name'], d['blob']['floor'])
		print 'RTSP URL: %s\n'%(d['blob']['rtsp_url'])

		cdb.insert(camID, blob)
