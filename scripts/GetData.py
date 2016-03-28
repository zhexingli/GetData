##################################################################################
#                               GETDATA
#
# This script is used to automatically query over the LCOGT online archive and
# download the requested images. Meanwhile, it calculates the time used for
# obtaining each frame that has been downloaded and calculates the total time that
# have been used towards the total time allocation for LCOGT Microlensing Key
# Project. A HTML page is generated as a final product of this script.
#
# Author        Date        Comments
# Zhexing Li    2016-03-23  Initial Version
# Zhexing Li    2016-03-25  Added lock file feature when the script is running
# Zhexing Li    2016-03-28  Changed the log feature where the download log is to be
#                           ouput everyday.
#
##################################################################################


#######################################
# Import necessary modules

import os
import numpy as np
from astropy.io import fits
import requests
import datetime
import re
import shutil
import sys

# Get current time from computer.
    
time = datetime.datetime.utcnow().strftime("%Y-%m-%d" + "T" + "%H:%M:%S")
time0 = datetime.datetime.utcnow().strftime("%Y-%m-%d")


##################################################################################
#
# FUNCTION: OUTPUT_HTML
#
##################################################################################

def Output_HTML():
    '''
    Function to read values from the TimeLog.txt file, which contains time spent for
    obtaining each frame. This function adds up times from all the frames in the log
    and calculates the total time that have been used so far towards the total time
    allocation for LCOGT's Microlensing Key Project.
    '''

    # Calls the Get_Config() function to obtain the latest directory which the
    # TimeLog file belongs to.
    
    info = Get_Config()
    
    tpath = info['timelog_directory']
    dpath = info['downloadlog_directory']

    tlog = tpath + '/TimeLog.txt'
    dlog = dpath + '/DownloadLog' + '_' + time0 + '.txt'
    
    time = []
    
    with open(dlog,'a') as outfile:
        outfile.write("# Calculating total time used from all frames.\n")
        
    with open(tlog,'r') as infile:
        for line in infile:
            if not line.startswith('#'):
                if not line.startswith('\n'):
                    col = line.split()
                    time.append(col[2])

    time = map(float,time)
    
    # Get the total time in seconds and convert it into hours, takes 2 decimals.
    
    total_time = str(np.around((np.sum(time)/3600.0),decimals = 2))

    with open(dlog,'a') as outfile:
        outfile.write("# Total time calculation completed.\n")
        
    # Output the result to a HTML file.
    
    if os.path.exists(tpath + '/Time.html'):
        with open(tpath + '/Time.html','w') as outfile:
            outfile.write("<html><body>")
            outfile.write("<strong>Total Time Used/Allocated: %s/3110hrs</strong>"
                          % total_time)
            outfile.write("</body></html>")
    else:
        with open(tpath + '/Time.html','a') as outfile:
            outfile.write("<html><body>")
            outfile.write("<strong>Total Time Used/Allocated: %s/3110hrs</strong>"
                          % total_time)
            outfile.write("</body></html>")

    with open(dlog,'a') as outfile:
        outfile.write("# Time used updated in HTML file.\n")
        outfile.write("# Lock file deleted. \n")
        outfile.write("# GetData completed. \n")

    # Delete the lock file in the log directory.
    
    for files in os.listdir(dpath):
        if files.endswith(".lock"):
            os.remove(dpath + '/' + files)
        else:
            pass


##################################################################################
#
# FUNCTION: GET_DATA
#
##################################################################################

def Get_Data():
    '''
    Function to query over LCOGT's archive and download frames with requested
    information found in the configuration file, which is called at the beginning
    of this function. Meanwhile, it calculates the time used for obtaining each
    frame and returns the total time allocation that have been used to obatin all
    the frames downloaded.
    '''
    
    # Get key information from configuration file.
    
    info = Get_Config()
    
    archive = info['archive']
    api_token = info['api_token']
    api_frames = info['api_frames']
    username = info['username']
    password = info['password']
    proposal = info['proposal']
    date_start = info['date_start']
    date_end = info['date_end']
    rlevel = info['rlevel']
    path1 = info['frame_directory']
    path2 = info['downloadlog_directory']
    path3 = info['timelog_directory']
    path4 = info['finalframe_directory']
    data_type = ''

    # Check if there's a lock file in the directory, if there's not, create one and continue
    # the rest of the code; if there's is one, stop the rest of the code.

    if os.path.exists(path2 + '/GetData.lock'):
        sys.exit(0)
    else:
        with open(path2 + '/GetData.lock','w') as lockfile:
            lockfile.write(time)

    # Creat and open files for logging downloaded frame names, their obs id and,
    # their total observation time, and move it to desired directory; if already
    # existed, append current time to file.

    dlog = path2 + '/DownloadLog' + '_' + time0 + '.txt'
    tlog = path3 + '/TimeLog.txt'
    
    if os.path.exists(dlog):
        with open(dlog,'a') as outfile:
            outfile.write("\n" + "\n" + "# " + time + "\n" + "\n")
            outfile.write("# Lock file created." + "\n")
    else:
        with open(dlog,'w') as outfile:
            outfile.write("##### GetData Download Logfile #####" + "\n" + "\n")
            outfile.write("# " + time + "\n" + "\n")
            outfile.write("# Lock file created." + "\n")
    
    if os.path.exists(tlog):
        pass
    else:
        with open(tlog,'w') as outfile:
            outfile.write("##### GetData Time Allocation Logfile #####" + "\n" + "\n")
            outfile.write("# Group Name" + "     " + "File Name" + "     " +
                          "Total Observation Time" + "\n")

    # Fetching data type from the configuraton file input.
    
    if rlevel == 'raw':
        rlevel = '00'
        data_type = '.fz'
    elif rlevel == 'quicklook':
        rlevel = '10'
        data_type = '.fits'
    elif rlevel == 'reduced':
        rlevel = '90'
        data_type = '.fz'
    else:
        with open(dlog,'a') as outfile:
            outfile.write("# Unknown data type from the configuration file. \n")

    # Cleaning frame directory to remove unexpected files in it.

    for files in os.listdir(path1):
        if files.endswith(data_type):
            os.remove(path1 + '/' + files)
        else:
            pass
    
    # Make an authenticated request to the archive.
    with open(dlog,'a') as outfile:
        outfile.write("# Log in to LCOGT archive..." + "\n")
    
    response = requests.post(archive + api_token,data =
                             {'username': username,'password': password}).json()
    token = response.get('token')
    headers = {'Authorization': 'Token ' + token}

    # Download desired data from the archive, skip those which have already been
    # downloaded.

    with open(dlog,'a') as outfile:
        outfile.write("# Log in successful, downloading requested frames..." + "\n")
    
    response = requests.get(archive + api_frames + '?start=' + date_start + '&end='
                            + date_end + '&RLEVEL=' + rlevel + '&PROPID=' + proposal,
                            headers = headers).json()

    frames = response['results']
    for frame in frames:
        log = open(tlog, 'r')
        num = []
        try:
            for line in log:
                if not line.startswith('#'):
                    if not line.startswith('\n'):
                        col = line.split()
                        if col[1] == frame['filename']:
                            num.append(col[1])
                            break
                        else:
                            pass
        finally:
            log.close()

        # Download frames that haven't been downloaded yet.
        
        if len(num) == 0:
            with open(path1 + '/' + frame['filename'],'wb') as f:      
                f.write(requests.get(frame['url']).content)
            with open(dlog,'a') as outfile:
                outfile.write(str(frame['filename']) + " successfully downloaded." +
                              "\n")

        # Skip frames that have already been downloaded.
        
        else:
            with open(dlog,'a') as outfile:
                outfile.write("# Skipping " + str(frame['filename']) + ", already "
                              + "exists." + "\n")
        
    with open(dlog,'a') as outfile:
        outfile.write("# All frames are downloaded." + "\n")

    # Go through each fits file in the directory to get information from the header
    # and write info to the logs; if already done so for some frames, skip them.

    with open(dlog,'a') as outfile:
        outfile.write("# Calculating time used for each frame..." + "\n")
    
    for files in os.listdir(path1):
        if files.endswith(data_type):
            group_name = []
            file_name = []
            obstime = []
        
            log = open(tlog,'r')
            try:
                for line in log:
                    if not line.startswith('#'):
                        if not line.startswith('\n'):
                            col = line.split()
                            if  col[1] == files:
                                file_name.append(col[1])
                                break
                            else:
                                pass
            finally:
                log.close()
                
            # Calculate time for file that hasn't been calculated before.
            
            if len(file_name) == 0:
                hdulist = fits.open(path1 + '/' + files)
                group = hdulist[0].header['GROUPID']
                exptime = hdulist[0].header['EXPTIME']
                instru = hdulist[0].header['INSTRUME']

                with open(tlog,'r') as infile:
                    for line in infile:
                        if not line.startswith('#'):
                            if not line.startswith('\n'):
                                col = line.split()
                                if col[0] == group:
                                    group_name.append(col[0])
                                    break
                                else:
                                    pass
                                
                # Calculate time for frames that belongs to a group which already
                # exists in the log file.
                
                if len(group_name) == 1:
                    if instru [0:2] == 'fl':
                        obstime.append(float(exptime) + 2.0 + 37.0 + 1.0)
                    elif instru [0:2] == 'kb':
                        obstime.append(float(exptime) + 2.0 + 14.5 + 1.0)
                    elif instru [0:2] == 'fs':
                        obstime.append(float(exptime) + 2.0 + 10.5 + 12.0)
                    else:
                        pass
                        
                # Calculate time for frames that belongs to a group which is not in
                # the log file yet (first appearance for a group).
                
                elif len(group_name) == 0:
                    if instru [0:2] == 'fl':
                        obstime.append(float(exptime) + 90.0 + 2.0 + 37.0 + 1.0)
                    elif instru [0:2] == 'kb':
                        obstime.append(float(exptime) + 90.0 + 2.0 + 14.5 + 1.0)
                    elif instru [0:2] == 'fs':
                        obstime.append(float(exptime) + 240.0 + 2.0 + 10.5 + 12.0)
                    else:
                        pass
                else:
                    pass

                # Append time information to the log file for frames that make first
                # appearance for a specific observation group.
                
                if len(obstime) == 1 and len(group_name) == 0:

                    with open(dlog,'a') as outfile:
                        outfile.write("# Time calculated for new frame " + str(files) +
                                      "." + "\n")
                    
                    with open(tlog, 'a') as outfile:
                        outfile.write(str(group) + "     " + str(files) + "     "
                                      + str(obstime[0]) + "\n")

                # Append time information to the log file for frames that belong to
                # a specific observation group.
                
                elif len(obstime) == 1 and len(group_name) == 1:

                    with open(dlog,'a') as outfile:
                        outfile.write("# Time calculated for new frame " + str(files) +
                                      "." + "\n")
                    
                    temp = open(path3 + '/temp','wb')
                    with open (tlog,'r') as f:
                        a = 0
                        for line in f:
                            if not line.startswith('#'):
                                if not line.startswith('\n'):
                                    col = line.split()
                                    if col[0] == group_name[0]:
                                        if a == 0:
                                            line = (line.strip() + '\n' + str(group)
                                                    + "     " + str(files) + "     "
                                                    + str(obstime[0]) + "\n")
                                            a = a + 1
                                        else:
                                            pass
                                    else:
                                        pass
                            temp.write(line)
                    temp.close()
                    shutil.move(path2 + '/temp',tlog)

                # Append comments to the log file for frames that have unknown class
                # of instrument.
                
                else:
                    with open(dlog,'a') as outfile:
                        outfile.write("# Unknown class of instrument for frame " +
                                      str(files) + ".\n")
            
            # Append comments to the log file for frames which time has already been
            # calculated.
            
            else:
                with open(dlog,'a') as outfile:
                    outfile.write("# Time already calculated for " + str(files) +
                                  "." + "\n")
        else:
            pass

    with open(dlog,'a') as outfile:
        outfile.write("# Time calculation for each frame completed." + "\n")

    # Move all frames to output directory and ready for use by other programs.

    for files in os.listdir(path1):
        if files.endswith(data_type):
            shutil.move(path1 + '/' + files, path4)
        else:
            pass

    with open(dlog,'a') as outfile:
        outfile.write("# Frames moved to output directory, ready for use.\n")


##################################################################################
#
# FUNCTION: GET_CONFIG
#
##################################################################################

def Get_Config():
    '''
    Function to read the key parameters from the Config_GetData file to feed as
    inputs for Get_Data function. It returns a list containing all key parameters.
    '''

    ConfigPath = os.path.join(os.path.expanduser('~'), '.obscontrol',
                              'Config_GetData.txt')
    
    param = {}
    
    with open(ConfigPath,'r') as infile:
        for line in infile:
            if not line.startswith('#'):
                if not line.startswith('\n'):
                    col = line.split()
                    param[col[0]] = col[1]

    return param


##################################################################################
# COMMANDLINE RUN SECTION
'''
Run the above script from the Linus command line. It calls Get_Config() first, then
Get_Data() and finally calls Output_HTML().
'''

if __name__ == '__main__':
    Get_Data()
    Output_HTML()
