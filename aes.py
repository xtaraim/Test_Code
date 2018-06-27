'''
Filename: aes.py
Description: This module deals with the encryption and decryption using aes method. 
'''

import os, random, sys
import StringIO
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
 
def encrypt(filename, password):
    '''
    This takes the filename and password as input and creates an encrypted file (encrypted)<filename> as an output
    '''
    
    chunksize = 64 * 1024
    key = SHA256.new(password).digest()

    outFile = os.path.join(os.path.dirname(filename), 
        '(encrypted)' + os.path.basename(filename))
    filesize = str(os.path.getsize(filename)).zfill(16)
    IV = ''
 
    for i in range(16):
        IV += chr(random.randint(0, 0xFF))
       
    encryptor = AES.new(key, AES.MODE_CBC, IV)
 
    with open(filename, 'rb') as infile:
        with open(outFile, 'wb') as outfile:
            outfile.write(filesize)
            outfile.write(IV)
            while True:
                chunk = infile.read(chunksize)
                   
                if len(chunk) == 0:
                    break
 
                elif len(chunk) % 16 !=0:
                    chunk += ' ' *  (16 - (len(chunk) % 16))
 
                outfile.write(encryptor.encrypt(chunk))
 
def decrypt(filename, password):    
    '''
    This takes the filename and password as input and creates an decrypted file 
    (decrypted)<filename> as an output if the ```password``` is same as the one used 
    for the file's encryption. Else it gives an error.
    ''' 
    output = ''
    key = SHA256.new(password).digest()
    chunksize = 64 * 1024

    with open(filename, 'rb') as infile:
        filesize = infile.read(16)
        IV = infile.read(16) 

        decryptor = AES.new(key, AES.MODE_CBC, IV)   

        while True:
            chunk = infile.read(chunksize)
            if len(chunk) == 0:
                break 
            output += decryptor.decrypt(chunk)

    return output

# Generate an encrypted file
if __name__ == '__main__':
    filename = sys.argv[1]
    password = 'DeepSightAILabs'

    if os.path.basename(filename).startswith('(encrypted)'):
        print '%s is already encrypted'%str(filename)
        pass     
    elif filename == os.path.join(os.getcwd(), sys.argv[0]):
        pass
    else:
        encrypt(str(filename), password)
        print 'Done encrypting %s'%str(filename)
