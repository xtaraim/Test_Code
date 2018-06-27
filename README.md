# Go Deep POC - Master Branch

## 1. Setup
Go to the misc folder and follow instructions on running install.sh

## 2. Data File Encryption

### Usage

To encrypt the config file:
```
python aes.py settings.conf
```

The output file will be generated in the same folder.
```
(encrypted)settings.conf
```

Default password is ```DeepSightAILabs```. You can change the password variable under ```if __name__ == 'main'``` block  in ```aes.py```.

All you have to do is update the ```config_init()``` call in ```http_handler.py``` and pass the encrypted file name.

**NOTE**: Please save (encrypted)settings.conf to ```/var/www/html/godeep/(encrypted)settings.conf```

## 3. Build using PyInstaller

### Usage

#### Building and Using your Package
To build just run:
```
pyinstaller GoDeep.spec
```

To run the built package:
```
cd dist/
./GoDeep
```

#### Create or Modify the ```.spec``` file
The ```GoDeep.spec``` file has been included in this repo. To create a custom ```.spec``` file, follow the instructions as explained below.

The ```.spec``` file contains all the information, package dependencies and data files required in the package. Apart from the standard format of the ```.spec``` file, please note the following changes that have to be made to build and run the package properly.

First, specify the main Python script and the absolute path to the script.
```
a = Analysis(['http_handler.py'],
             pathex=['/home/deepinsightlabs/Projects/POC/POC-build/POC'],
             binaries=[],
             datas=data_files,
             hiddenimports=['pandas._libs.tslibs.timedeltas'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
```

**NOTE: You have to include all the hidden imports which will be required at run time. Here, ```pandas._libs.tslibs.timedeltas``` is a hidden import which is necessary to run the package properly.**

Now, create a list of all the dependent data files or resources as follows. The ```.spec``` file follows the Python syntax.

```
data_files = [
                ('settings.conf', '.'),
                ('model/frozen_inference_graph.pb', 'model'),
                ('model/mscoco_label_map.pbtxt', 'model'),
                ('model/output_graph_inception_resnet_v2.pb', 'model'),
                ('model/output_labels.txt', 'model')
             ]
```

The first element of the tuple is the relative path of the **resource file** with respect to the **main Python script**. 

The second element of the tuple is the relative path to the **folder** which will contain the resource file with respect to the **temporary folder** which PyInstaller will create at run time. A ```.``` is used to specify that the resource file should be in the root of the temporary folder created. The temp folder will be assigned dynamically at run time and can be accessed as follows in your Python script.

```
import sys
print sys._MEIPASS
```
Example temp folder path:
```
/tmp/_MEIbyu6vV/
```
Finally, assign your ```data_files``` list to ```a.datas``` object of ```Analysis``` class as shown above.

The name of your software can be specified in ```exe.name``` field as shown below.
```
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='GoDeep',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True)
```

### Notes

Refer [this](https://github.com/DeepInsightLabs/Miscellaneuos/tree/master/pyinstaller) repo for more details about PyInstaller.

## 4. Auto-Running backend using Cron
### Usage
#### Create the Cron Service
You can edit the cron job by typing the command
```
crontab -e
```
Add the following line to the file when it opens for editing
```
*/1 * * * * /usr/bin/python /home/ritwik/deepInsight/poc/check_process_status.py
```
**NOTE: Please write the full path of the check_process_status.py as the second argument. This can be different for your system**

After Abobe Step Press ESCAPE)
:wq
#### Edit check_process_status.py

check_process_status.py has some configuration that you can change as per your setup:
1. CODE_DIR = '/home/ritwik/deepInsight/poc'
2. MAIN_FILE = 'http_handler.py'
3. CHECK_INTERVAL = 10

**NOTE: You would need to change the CODE_DIR which is the full path of the base directory where your executable/files lie.**

### Notes

Refer [this](https://github.com/DeepInsightLabs/Miscellaneuos/tree/master/restart_script) repo for more details about Cron services.

## 5. MySQL Database Integration
POC code integrated with MySQL Database for CCTV Cameras

### Notes
Install the [Chrome MySQL Admin](https://chrome.google.com/webstore/detail/chrome-mysql-admin/ndgnpnpakfcdjmpgmcaknimfgcldechn?hl=en)  app to view the MySQL database and tables. 

#### Quick Update Database from JSON File
To add multiple cameras for testing, one can specify the various camera details along with the unique Camera ID in ```cameras.json``` and update the database. This will be much quicker than entering them manually from  the GUI.

To update the database with the entries from this JSON file, just run the following script.

**NOTE: This will delete any existing entries in the database.**

```
python camera_database.py
```

### CameraDatabase API Usage
#### Create Object
Create a ```CameraDatabase``` object with a database name and table name. 

```
cdb = CameraDatabase('db', 'test')
```

Default host is ```localhost```, user is ```root```, password is ```root```. You can modify them by passing the arguments as follows.

```
cdb = CameraDatabase('db', 'test', host='192.168.1.10', user='DSAL', password='1234')
```

#### Insert Entry
To insert an entry, invoke the ```CameraDatabase.insert()``` method and pass the unique *Camera ID* and *Camera Info Dictionary*.

```
cdb.insert(0, dict)
```

#### Delete Entry
To delete an entry, invoke the ```CameraDatabase.delete()``` method and pass the unique *Camera ID*.

```
cdb.delete(1)
```

#### Edit Entry
To edit an existing entry, invoke the ```CameraDatabase.edit()``` method and pass the unique *Camera ID* and *Edited Camera Info Dictionary*.

```
cdb.edit(0, edited_dict)
```

#### Retrieve Entry
To retrieve an entry, invoke the ```CameraDatabase.retrieve()``` method and pass the unique *Camera ID*.

```
cdb.retrieve(1)
```

To retrieve all the entries from the database, invoke the ```CameraDatabase.retrieve()``` without any arguments.

```
cdb.retrieve()
```

#### Get Max ID
To retrieve the maximum value of the ID in the table, invoke the ```CameraDatabase.get_max_id()``` without any arguments.

```
cdb.get_max_id()
```
